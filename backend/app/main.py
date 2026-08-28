import secrets, uuid, hashlib, json, re
import httpx
from pathlib import Path
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, text
from pydantic import BaseModel, Field
from .db import get_db
from .models import *
from .config import settings
from .security import verify_telegram_init_data, make_token, read_token
from .services.economy import get_balance, change_vld, change_scrap, idempotent
from .services.cases import open_case
from .services.level import level_from_total_xp, xp_for_level
from .services.gameplay import record_action, award_xp, lock_user
from .services.payments import grant_stars_entitlement

ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"
ADMIN_DIR = ROOT_DIR / "admin"

app=FastAPI(title="VLDST UNDERGROUND API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class AuthIn(BaseModel): init_data: str
class FinishIn(BaseModel): nonce: str; score: int = Field(ge=0, le=100000)
class PurchaseIn(BaseModel): product_id: int
class GuildCreateIn(BaseModel): name: str = Field(min_length=3,max_length=80); tag: str = Field(min_length=2,max_length=12)
class GuildJoinIn(BaseModel): guild_id: int
class ShowcaseIn(BaseModel): inventory_ids: list[int] = Field(max_length=6)
class TitleIn(BaseModel): title: str = Field(min_length=1,max_length=80)
class EventProgressIn(BaseModel): amount: int = Field(default=1,ge=1,le=1000)
class SeasonClaimIn(BaseModel): level: int = Field(ge=1,le=100)
class AdjustIn(BaseModel): amount: int; currency: str="VLD"; reason: str="admin"

async def current_user(authorization: str=Header(""), db: AsyncSession=Depends(get_db)):
    if not authorization.startswith("Bearer "): raise HTTPException(401,"Authentication required")
    try:
        token_data = read_token(authorization[7:])
        uid = token_data["uid"] if isinstance(token_data, dict) else token_data
        u = await db.get(User, uid)
        if not u or u.banned: raise HTTPException(403,"Account unavailable")
        if isinstance(token_data, dict) and token_data.get("sv", u.session_version) != u.session_version: raise HTTPException(401,"Session revoked")
        return uid
    except HTTPException: raise
    except Exception: raise HTTPException(401,"Invalid token")

async def ensure_user(db, uid):
    u=await db.get(User,uid)
    if not u: raise HTTPException(404,"User not found")
    return u

async def refresh_energy(db, u):
    now=datetime.now(timezone.utc)
    last=u.energy_updated_at or u.created_at or now
    regen_minutes=max(1, int((await db.scalar(select(EconomyConfig.value).where(EconomyConfig.key=="energy_regen_minutes")) or 5)))
    energy_max=max(1, int((await db.scalar(select(EconomyConfig.value).where(EconomyConfig.key=="energy_max")) or 100)))
    minutes=max(0,int((now-last).total_seconds()//(regen_minutes*60)))
    if minutes>0:
        u.energy=min(energy_max,u.energy+minutes)
        u.energy_updated_at=last+timedelta(minutes=minutes*regen_minutes)
    return u

async def process_referral_milestones(db, invitee_id, milestone):
    ref=(await db.execute(select(Referral).where(Referral.invitee_id==invitee_id))).scalar_one_or_none()
    if not ref: return False
    reward={"registered":(500,25),"level_3":(1000,50),"level_5":(2000,100),"first_quest":(1500,75),"active":(3000,150)}.get(milestone)
    if not reward: return False
    exists=await db.scalar(select(ReferralReward.id).where(ReferralReward.inviter_id==ref.inviter_id,ReferralReward.invitee_id==invitee_id,ReferralReward.milestone==milestone))
    if exists:return False
    db.add(ReferralReward(inviter_id=ref.inviter_id,invitee_id=invitee_id,milestone=milestone,reward_vld=reward[0],reward_xp=reward[1]))
    await change_vld(db,ref.inviter_id,reward[0],"REFERRAL_REWARD",f"{invitee_id}:{milestone}")
    await award_xp(db,ref.inviter_id,reward[1]); ref.active=True; return True

async def active_season(db):
    now=datetime.now(timezone.utc)
    return (await db.execute(select(Season).where(Season.start_at<=now,Season.end_at>=now).order_by(Season.id.desc()))).scalars().first()

async def get_season_progress(db, uid, season):
    q=(await db.execute(select(SeasonProgress).where(SeasonProgress.user_id==uid,SeasonProgress.season_id==season.id))).scalar_one_or_none()
    if not q:
        q=SeasonProgress(user_id=uid,season_id=season.id,xp=0,level=1,claimed_levels=[])
        db.add(q); await db.flush()
    return q

def season_level_for_xp(xp, levels=50):
    # 100 XP for level 1, increasing by 50 each level.
    level=1; spent=0
    while level<levels and xp >= spent + (100 + (level-1)*50):
        spent += 100 + (level-1)*50; level += 1
    return level

async def add_season_xp(db, uid, amount):
    if amount<=0: return None
    s=await active_season(db)
    if not s: return None
    pgr=await get_season_progress(db,uid,s);pgr.xp+=amount;pgr.level=season_level_for_xp(pgr.xp,s.levels);return pgr

async def unlock_achievement(db, uid, code):
    ach=(await db.execute(select(Achievement).where(Achievement.code==code))).scalar_one_or_none()
    if not ach: return False
    exists=(await db.execute(select(UserAchievement).where(UserAchievement.user_id==uid,UserAchievement.achievement_id==ach.id))).scalar_one_or_none()
    if exists: return False
    db.add(UserAchievement(user_id=uid,achievement_id=ach.id))
    if ach.reward_vld: await change_vld(db,uid,ach.reward_vld,"ACHIEVEMENT_REWARD",ach.code)
    if ach.reward_xp:
        u=await ensure_user(db,uid); u.xp+=ach.reward_xp; u.level=level_from_total_xp(u.xp)
    return True

async def evaluate_achievements(db, uid, event="activity"):
    await lock_user(db, uid)
    games=(await db.execute(select(func.count(GameSession.id)).where(GameSession.user_id==uid,GameSession.claimed==True))).scalar() or 0
    cases=(await db.execute(select(func.count(Transaction.id)).where(Transaction.user_id==uid,Transaction.kind=="CASE_PURCHASE"))).scalar() or 0
    items=(await db.execute(select(func.count(func.distinct(Inventory.item_id))).where(Inventory.user_id==uid))).scalar() or 0
    quests=(await db.execute(select(func.count(QuestProgress.id)).where(QuestProgress.user_id==uid,QuestProgress.claimed==True))).scalar() or 0
    trades=(await db.execute(select(func.count(MarketTransaction.id)).where(MarketTransaction.buyer_id==uid))).scalar() or 0
    stats={"games":games,"cases":cases,"items":items,"quests":quests,"trades":trades}
    achievements=(await db.execute(select(Achievement))).scalars().all(); unlocked=[]
    for ach in achievements:
        req=ach.requirement or {}; kind=req.get("kind"); target=int(req.get("target", req.get("index", 0)) or 0)
        ok = True if kind=="always" else stats.get(kind,0)>=target
        if ok and await unlock_achievement(db,uid,ach.code): unlocked.append(ach.code)
    return unlocked

@app.get("/api/health")
async def health(db:AsyncSession=Depends(get_db)):
    try:
        await db.execute(text("SELECT 1")); return {"ok":True,"service":"vldst-underground","database":"ok"}
    except Exception: raise HTTPException(503,"Database unavailable")

@app.post("/api/auth/telegram")
async def auth(body: AuthIn, db: AsyncSession=Depends(get_db)):
    try: tg=verify_telegram_init_data(body.init_data)
    except Exception as e: raise HTTPException(401,str(e))
    tid=int(tg["id"])
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": tid & 0x7fffffffffffffff})
    q=await db.execute(select(User).where(User.telegram_id==tid))
    user=q.scalar_one_or_none()
    is_new=False
    if not user:
        is_new=True; code="ref_"+secrets.token_hex(4).upper()
        user=User(telegram_id=tid,username=tg.get("username"),nickname=(tg.get("first_name") or "VLDST")[:32],referral_code=code,energy=10)
        db.add(user); await db.flush()
        db.add(Balance(user_id=user.id,vld=5000,scrap=0,core=0)); db.add(Vault(user_id=user.id,level=1,slots=50))
        refcode=tg.get("_start_param")
        if refcode:
            inviter=await db.scalar(select(User).where(User.referral_code==refcode))
            if inviter and inviter.id!=user.id: db.add(Referral(inviter_id=inviter.id,invitee_id=user.id,active=False))
    if is_new: await process_referral_milestones(db,user.id,"registered")
    await db.commit()
    return {"token":make_token(user.id, user.session_version),"user_id":user.id}

@app.get("/api/me")
async def me(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    u=await db.get(User,uid); b=await get_balance(db,uid)
    if not u: raise HTTPException(404,"User not found")
    await refresh_energy(db,u); await db.commit()
    return {"id":u.id,"telegram_id":u.telegram_id,"username":u.username,"nickname":u.nickname,"level":u.level,"xp":u.xp,"energy":u.energy,"streak":u.streak,"vld":b.vld,"scrap":b.scrap,"core":b.core,"referral_code":u.referral_code}

@app.get("/api/profile")
async def profile(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    u=await db.get(User,uid); b=await get_balance(db,uid)
    inv=(await db.execute(select(func.count(Inventory.id)).where(Inventory.user_id==uid))).scalar() or 0
    ach=(await db.execute(select(func.count(UserAchievement.id)).where(UserAchievement.user_id==uid))).scalar() or 0
    prem=(await db.execute(select(Premium).where(Premium.user_id==uid))).scalar_one_or_none()
    return {"user":u.nickname,"level":u.level,"xp":u.xp,"next_xp":xp_for_level(min(100,u.level+1)),"vld":b.vld,"inventory":inv,"achievements":ach,"title":u.selected_title,"premium":bool(prem and prem.expires_at>datetime.now(timezone.utc))}

@app.get("/api/cases")
async def cases(db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(Case).where(Case.active==True).order_by(Case.price))).scalars().all()
    return [{"id":x.id,"name":x.name,"price":x.price,"image":x.image,"weights":x.weights} for x in rows]

@app.post("/api/cases/{case_id}/open")
async def case_open(case_id:int, request:Request, uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    try:
        result=await open_case(db,uid,case_id,key); await add_season_xp(db,uid,20 if result.get("rarity") in {"EPIC","LEGENDARY","MYTHIC","SECRET"} else 10); await evaluate_achievements(db,uid,"case"); await record_action(db,uid,"case"); await db.commit(); return result
    except ValueError as e: await db.rollback(); raise HTTPException(400,str(e))

@app.get("/api/inventory")
async def inventory(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    q=await db.execute(select(Inventory,Item).join(Item,Inventory.item_id==Item.id).where(Inventory.user_id==uid).order_by(Inventory.id.desc()).limit(100))
    return [{"inventory_id":i.id,"item_id":it.id,"name":it.name,"rarity":it.rarity,"collection":it.collection,"level":i.level,"value":it.base_value,"image":it.image,"favorite":i.favorite} for i,it in q.all()]

@app.post("/api/inventory/{inventory_id}/recycle")
async def recycle(inventory_id:int, request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    await lock_user(db,uid)
    if await idempotent(db,uid,key): return {"ok":True,"already_processed":True}
    inv=(await db.execute(select(Inventory).where(Inventory.id==inventory_id).with_for_update())).scalar_one_or_none()
    if not inv or inv.user_id!=uid: raise HTTPException(404,"Предмет больше недоступен")
    it=await db.get(Item,inv.item_id)
    await change_scrap(db,uid,it.recycle_value*(1+inv.level//5),"RECYCLE")
    await db.delete(inv)
    db.add(Operation(user_id=uid,key=key,result={"scrap":it.recycle_value}))
    await db.commit()
    return {"ok":True,"scrap":it.recycle_value}

@app.post("/api/inventory/{inventory_id}/upgrade")
async def upgrade(inventory_id:int,request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    if await idempotent(db,uid,key): return {"ok":True}
    inv=await db.get(Inventory,inventory_id); 
    if not inv or inv.user_id!=uid: raise HTTPException(404,"Предмет больше недоступен")
    it=await db.get(Item,inv.item_id)
    if inv.level>=it.max_level: raise HTTPException(400,"Максимальный уровень")
    cost=int(it.base_value*(1.25**inv.level))
    await change_vld(db,uid,-cost,"UPGRADE",str(inventory_id)); inv.level+=1
    db.add(Operation(user_id=uid,key=key,result={"level":inv.level,"cost":cost})); await db.commit()
    return {"ok":True,"level":inv.level,"cost":cost}

@app.get("/api/collections")
async def collections(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(Collection).order_by(Collection.id))).scalars().all()
    inv=(await db.execute(select(Item.collection,func.count(func.distinct(Inventory.item_id))).join(Inventory,Inventory.item_id==Item.id).where(Inventory.user_id==uid).group_by(Item.collection))).all()
    counts=dict(inv); out=[]
    for c in rows:
        owned=int(counts.get(c.name,0)); total=(await db.execute(select(func.count(Item.id)).where(Item.collection==c.name))).scalar() or 0
        pct=int(owned*100/max(1,total)); out.append({"id":c.id,"name":c.name,"description":c.description,"owned":owned,"total":total,"progress":pct,"milestones":{"25":pct>=25,"50":pct>=50,"75":pct>=75,"100":pct>=100}})
    return out

@app.post("/api/collections/{collection_id}/claim/{milestone}")
async def claim_collection(collection_id:int,milestone:int,request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    await lock_user(db,uid)
    if milestone not in (25,50,75,100): raise HTTPException(400,"Недопустимый milestone")
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    if await idempotent(db,uid,key): return {"ok":True,"already_processed":True}
    c=await db.get(Collection,collection_id)
    if not c: raise HTTPException(404,"Collection not found")
    total=(await db.execute(select(func.count(Item.id)).where(Item.collection==c.name))).scalar() or 0
    owned=(await db.execute(select(func.count(func.distinct(Inventory.item_id))).join(Item,Inventory.item_id==Item.id).where(Inventory.user_id==uid,Item.collection==c.name))).scalar() or 0
    pct=owned*100/max(1,total)
    if pct<milestone: raise HTTPException(400,"Milestone ещё не достигнут")
    opkey=f"collection:{collection_id}:{milestone}"
    if await idempotent(db,uid,opkey): return {"ok":True,"already_claimed":True}
    rewards={25:(250,25,0),50:(750,75,0),75:(1500,150,10),100:(5000,300,25)}[milestone]
    await change_vld(db,uid,rewards[0],"COLLECTION_REWARD",opkey)
    u=await ensure_user(db,uid);u.xp+=rewards[1];u.level=level_from_total_xp(u.xp)
    if rewards[2]: await change_scrap(db,uid,rewards[2],"COLLECTION_REWARD")
    db.add(Operation(user_id=uid,key=opkey,result={"collection_id":collection_id,"milestone":milestone,"vld":rewards[0]})); await evaluate_achievements(db,uid,"collection"); await db.commit()
    return {"ok":True,"milestone":milestone,"vld":rewards[0],"xp":rewards[1],"scrap":rewards[2]}


@app.get("/api/vault")
async def vault(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    v=(await db.execute(select(Vault).where(Vault.user_id==uid).with_for_update())).scalar_one_or_none()
    if not v: v=Vault(user_id=uid,level=1,slots=50);db.add(v);await db.flush()
    count=await db.scalar(select(func.count(Inventory.id)).where(Inventory.user_id==uid))
    return {"level":v.level,"slots":v.slots,"used":count or 0,"free":max(0,v.slots-(count or 0))}

@app.post("/api/vault/upgrade")
async def vault_upgrade(request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4());await lock_user(db,uid)
    if await idempotent(db,uid,key): return {"ok":True,"already_processed":True}
    v=(await db.execute(select(Vault).where(Vault.user_id==uid).with_for_update())).scalar_one_or_none()
    if not v: v=Vault(user_id=uid,level=1,slots=50);db.add(v);await db.flush()
    if v.slots>=500: raise HTTPException(400,"Vault максимального уровня")
    cost=int(1000*(1.6**(v.level-1)));new_slots=min(500,v.slots+25)
    await change_vld(db,uid,-cost,"VAULT_UPGRADE",key);v.level+=1;v.slots=new_slots
    db.add(VaultUpgrade(vault_id=v.id,level=v.level,cost_vld=cost,slots=new_slots));db.add(Operation(user_id=uid,key=key,result={"level":v.level,"slots":v.slots}));await db.commit();return {"ok":True,"level":v.level,"slots":v.slots,"cost":cost}

@app.post("/api/vault/showcase")
async def showcase(body:ShowcaseIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    ids=list(dict.fromkeys(body.inventory_ids))
    if len(ids)>6: raise HTTPException(400,"Максимум 6 предметов")
    rows=(await db.execute(select(Inventory).where(Inventory.user_id==uid,Inventory.id.in_(ids)))).scalars().all() if ids else []
    if len(rows)!=len(ids): raise HTTPException(400,"Один или несколько предметов недоступны")
    await db.execute(update(Inventory).where(Inventory.user_id==uid).values(equipped=False))
    if ids: await db.execute(update(Inventory).where(Inventory.id.in_(ids),Inventory.user_id==uid).values(equipped=True))
    await db.commit();return {"ok":True,"inventory_ids":ids}

@app.get("/api/vault/showcase")
async def get_showcase(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    q=await db.execute(select(Inventory,Item).join(Item,Inventory.item_id==Item.id).where(Inventory.user_id==uid,Inventory.equipped==True).limit(6))
    return [{"inventory_id":i.id,"item_id":it.id,"name":it.name,"rarity":it.rarity,"image":it.image,"level":i.level} for i,it in q.all()]

@app.post("/api/profile/title")
async def set_title(body:TitleIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    u=await ensure_user(db,uid); valid=(await db.execute(select(Achievement.title_reward).where(Achievement.title_reward==body.title).limit(1))).scalar_one_or_none()
    if not valid and body.title!="NEWCOMER": raise HTTPException(403,"Title не разблокирован")
    earned=(await db.execute(select(UserAchievement).join(Achievement,UserAchievement.achievement_id==Achievement.id).where(UserAchievement.user_id==uid,Achievement.title_reward==body.title))).scalar_one_or_none() if body.title!="NEWCOMER" else True
    if not earned: raise HTTPException(403,"Title не разблокирован")
    u.selected_title=body.title;await db.commit();return {"ok":True,"title":u.selected_title}

@app.get("/api/quests")
async def quests(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(Quest).where(Quest.active==True).order_by(Quest.id))).scalars().all()
    return [{"id":q.id,"title":q.title,"description":q.description,"target":q.target,"reward_vld":q.reward_vld,"reward_xp":q.reward_xp,"period":q.period} for q in rows]

@app.post("/api/quests/{quest_id}/claim")
async def claim_quest(quest_id:int,request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    if await idempotent(db,uid,key): return {"ok":True}
    await lock_user(db,uid)
    q=await db.get(Quest,quest_id)
    if not q or not q.active: raise HTTPException(404,"Задание больше недоступно")
    p=(await db.execute(select(QuestProgress).where(QuestProgress.user_id==uid,QuestProgress.quest_id==quest_id).with_for_update())).scalar_one_or_none()
    if not p:
        raise HTTPException(400,"Задание ещё не начато")
    if p.claimed: raise HTTPException(400,"Награда уже получена")
    if p.progress<q.target: raise HTTPException(400,"Задание ещё не выполнено")
    await change_vld(db,uid,q.reward_vld,"QUEST_REWARD",str(q.id))
    await award_xp(db,uid,q.reward_xp)
    p.claimed=True; await record_action(db,uid,"quest_claim"); await add_season_xp(db,uid,max(10,q.reward_xp//2)); db.add(Operation(user_id=uid,key=key,result={"reward_vld":q.reward_vld,"reward_xp":q.reward_xp}))
    await db.commit(); return {"ok":True,"reward_vld":q.reward_vld,"reward_xp":q.reward_xp}

@app.get("/api/games")
async def games(db:AsyncSession=Depends(get_db)):
    return [{"id":g.id,"code":g.code,"name":g.name,"energy_cost":g.energy_cost} for g in (await db.execute(select(Game).where(Game.active==True))).scalars().all()]

@app.post("/api/games/{game_id}/start")
async def game_start(game_id:int,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    g=await db.get(Game,game_id)
    u=await lock_user(db,uid)
    if not g or not g.active: raise HTTPException(404,"Игра недоступна")
    await refresh_energy(db,u)
    if u.energy<g.energy_cost: raise HTTPException(400,"Недостаточно Energy")
    u.energy-=g.energy_cost
    nonce=secrets.token_urlsafe(24); seed=secrets.token_hex(32)
    db.add(GameSession(user_id=uid,game_id=game_id,nonce=nonce,server_seed=seed))
    await db.commit(); return {"nonce":nonce,"server_seed_hint":seed[:8],"energy":u.energy}

@app.post("/api/games/{game_id}/finish")
async def game_finish(game_id:int,body:FinishIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    s=(await db.execute(select(GameSession).where(GameSession.user_id==uid,GameSession.game_id==game_id,GameSession.nonce==body.nonce).with_for_update())).scalar_one_or_none()
    if not s or s.claimed: raise HTTPException(400,"Игровая сессия недействительна")
    if datetime.now(timezone.utc)-s.started_at>timedelta(minutes=5): raise HTTPException(400,"Сессия истекла")
    elapsed=max(0.25,(datetime.now(timezone.utc)-s.started_at).total_seconds())
    max_score=min(100000, max(100, int(elapsed*1200)))
    if body.score>max_score: raise HTTPException(400,"Score не соответствует длительности сессии")
    # Score is untrusted telemetry. Gameplay rewards never depend directly on client score.
    reward=25
    xp=10
    await change_vld(db,uid,reward,"GAME_REWARD",body.nonce)
    await award_xp(db,uid,xp)
    s.claimed=True;s.finished_at=datetime.now(timezone.utc); db.add(GameResult(session_id=s.id,user_id=uid,score=body.score,reward_vld=reward,reward_xp=xp)); await add_season_xp(db,uid,max(5,xp)); await record_action(db,uid,"game")
    await evaluate_achievements(db,uid,"game"); await db.commit(); return {"score":body.score,"vld":reward,"xp":xp}

@app.get("/api/leaderboard")
async def leaderboard(db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(User).order_by(User.xp.desc()).limit(50))).scalars().all()
    return [{"rank":i+1,"nickname":u.nickname,"level":u.level,"xp":u.xp} for i,u in enumerate(rows)]

@app.get("/api/events")
async def events(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    now=datetime.now(timezone.utc); rows=(await db.execute(select(Event).where(Event.active==True).order_by(Event.start_at))).scalars().all();out=[]
    for e in rows:
        pr=(await db.execute(select(EventProgress).where(EventProgress.user_id==uid,EventProgress.event_id==e.id))).scalar_one_or_none()
        global_progress=e.global_progress
        out.append({"id":e.id,"name":e.name,"description":e.description,"banner":e.banner,"start":e.start_at,"end":e.end_at,"goal":e.global_goal,"progress":pr.progress if pr else 0,"joined":bool(pr),"reward_claimed":pr.reward_claimed if pr else False,"global_progress":global_progress,"status":"LIVE" if e.start_at<=now<=e.end_at else ("UPCOMING" if now<e.start_at else "ENDED")})
    return out

@app.post("/api/events/{event_id}/join")
async def event_join(event_id:int,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    await lock_user(db,uid)
    e=await db.get(Event,event_id);now=datetime.now(timezone.utc)
    if not e or not e.active or not(e.start_at<=now<=e.end_at): raise HTTPException(400,"Event сейчас недоступен")
    pr=(await db.execute(select(EventProgress).where(EventProgress.user_id==uid,EventProgress.event_id==event_id).with_for_update())).scalar_one_or_none()
    if not pr: db.add(EventProgress(user_id=uid,event_id=event_id,progress=0));await db.commit()
    return {"ok":True,"event_id":event_id}

@app.post("/api/events/{event_id}/progress")
async def event_progress(event_id:int, request:Request, uid:int=Depends(current_user), db:AsyncSession=Depends(get_db)):
    raise HTTPException(403,"Progress is generated by verified gameplay actions")

@app.post("/api/events/{event_id}/claim")
async def event_claim(event_id:int,request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    if await idempotent(db,uid,key): return {"ok":True,"already_processed":True}
    e=await db.get(Event,event_id);pr=(await db.execute(select(EventProgress).where(EventProgress.user_id==uid,EventProgress.event_id==event_id))).scalar_one_or_none()
    if not e or not pr or pr.reward_claimed: raise HTTPException(400,"Награда недоступна")
    global_progress=e.global_progress
    if e.global_goal and global_progress<e.global_goal: raise HTTPException(400,"Глобальная цель события ещё не достигнута")
    await change_vld(db,uid,e.reward_vld,"EVENT_REWARD",str(event_id));await award_xp(db,uid,e.reward_xp);pr.reward_claimed=True
    db.add(Operation(user_id=uid,key=key,result={"event_id":event_id,"vld":e.reward_vld,"xp":e.reward_xp}));await db.commit();return {"ok":True,"vld":e.reward_vld,"xp":e.reward_xp}

@app.get("/api/guild")
async def guild(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    m=(await db.execute(select(GuildMember).where(GuildMember.user_id==uid))).scalar_one_or_none()
    if not m:return {"guild":None}
    g=await db.get(Guild,m.guild_id); count=(await db.execute(select(func.count(GuildMember.id)).where(GuildMember.guild_id==g.id))).scalar() or 0
    return {"guild":{"id":g.id,"name":g.name,"tag":g.tag,"level":g.level,"xp":g.xp,"role":m.role,"members":count,"max_members":g.max_members}}

@app.get("/api/guilds")
async def guilds(db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(Guild).order_by(Guild.xp.desc()).limit(50))).scalars().all();out=[]
    for g in rows:
        n=(await db.execute(select(func.count(GuildMember.id)).where(GuildMember.guild_id==g.id))).scalar() or 0
        out.append({"id":g.id,"name":g.name,"tag":g.tag,"level":g.level,"xp":g.xp,"members":n,"max_members":g.max_members})
    return out

@app.post("/api/guild/create")
async def guild_create(body:GuildCreateIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    await lock_user(db,uid)
    if (await db.execute(select(GuildMember).where(GuildMember.user_id==uid))).scalar_one_or_none(): raise HTTPException(400,"Вы уже состоите в Guild")
    name=re.sub(r"[^\w\- ]","",body.name).strip(); tag=re.sub(r"[^A-Za-z0-9]","",body.tag).upper()
    if len(name)<3 or len(tag)<2: raise HTTPException(400,"Некорректное имя Guild")
    if (await db.execute(select(Guild).where(or_(Guild.name==name,Guild.tag==tag)))).scalar_one_or_none(): raise HTTPException(409,"Guild name/tag уже занят")
    g=Guild(name=name,tag=tag,created_by=uid);db.add(g);await db.flush();db.add(GuildMember(guild_id=g.id,user_id=uid,role="owner"));db.add_all([GuildQuest(guild_id=g.id,title="Guild Games",target=50,reward_vld=2500,reward_xp=250),GuildQuest(guild_id=g.id,title="Guild Cases",target=25,reward_vld=3000,reward_xp=300),GuildQuest(guild_id=g.id,title="Guild Craft",target=10,reward_vld=4000,reward_xp=400)]);await db.commit()
    return {"ok":True,"guild":{"id":g.id,"name":g.name,"tag":g.tag,"role":"owner"}}

@app.post("/api/guild/join")
async def guild_join(body:GuildJoinIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    await db.execute(select(User).where(User.id==uid).with_for_update())
    if (await db.execute(select(GuildMember).where(GuildMember.user_id==uid))).scalar_one_or_none(): raise HTTPException(400,"Вы уже состоите в Guild")
    g=(await db.execute(select(Guild).where(Guild.id==body.guild_id).with_for_update())).scalar_one_or_none()
    if not g: raise HTTPException(404,"Guild not found")
    count=(await db.execute(select(func.count(GuildMember.id)).where(GuildMember.guild_id==g.id))).scalar() or 0
    if count>=g.max_members: raise HTTPException(400,"Guild переполнен")
    db.add(GuildMember(guild_id=g.id,user_id=uid,role="member"));await db.commit();return {"ok":True,"guild_id":g.id}

@app.post("/api/guild/leave")
async def guild_leave(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    m=(await db.execute(select(GuildMember).where(GuildMember.user_id==uid))).scalar_one_or_none()
    if not m: raise HTTPException(400,"Вы не состоите в Guild")
    if m.role=="owner": raise HTTPException(400,"Owner должен передать Guild или удалить её через Admin")
    await db.delete(m);await db.commit();return {"ok":True}

@app.get("/api/market")
async def market(db:AsyncSession=Depends(get_db)):
    q=await db.execute(select(MarketListing,Inventory,Item,User).join(Inventory,MarketListing.inventory_id==Inventory.id).join(Item,Inventory.item_id==Item.id).join(User,MarketListing.seller_id==User.id).where(MarketListing.active==True).order_by(MarketListing.id.desc()).limit(100))
    return [{"id":l.id,"inventory_id":i.id,"item_id":it.id,"name":it.name,"rarity":it.rarity,"image":it.image,"level":i.level,"price":l.price,"seller_id":u.id,"seller":u.nickname} for l,i,it,u in q.all()]

class MarketListIn(BaseModel):
    inventory_id:int
    price:int=Field(ge=1,le=10_000_000_000)

@app.post("/api/market/list")
async def market_list(body:MarketListIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    await lock_user(db,uid)
    inv=(await db.execute(select(Inventory).where(Inventory.id==body.inventory_id).with_for_update())).scalar_one_or_none()
    if not inv or inv.user_id!=uid: raise HTTPException(404,"Предмет больше недоступен")
    if await db.scalar(select(MarketListing.id).where(MarketListing.inventory_id==inv.id,MarketListing.active==True)): raise HTTPException(409,"Предмет уже выставлен")
    db.add(MarketListing(seller_id=uid,inventory_id=inv.id,price=body.price,active=True));await db.commit();return {"ok":True}

@app.post("/api/market/{listing_id}/buy")
async def market_buy(listing_id:int,request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    existing=await idempotent(db,uid,key)
    if existing:return {"ok":True,"already_processed":True,**(existing.result or {})}
    # Lock both users in stable order before the listing/balances to avoid deadlocks.
    seller_id=await db.scalar(select(MarketListing.seller_id).where(MarketListing.id==listing_id))
    if seller_id is None: raise HTTPException(409,"Предмет больше недоступен")
    for user_id in sorted({uid,seller_id}): await lock_user(db,user_id)
    # Lock the listing; only one buyer can win a listing.
    listing=(await db.execute(select(MarketListing).where(MarketListing.id==listing_id).with_for_update())).scalar_one_or_none()
    if not listing or not listing.active: raise HTTPException(409,"Предмет больше недоступен")
    if listing.seller_id==uid: raise HTTPException(400,"Нельзя купить собственный предмет")
    inv=(await db.execute(select(Inventory).where(Inventory.id==listing.inventory_id).with_for_update())).scalar_one_or_none()
    if not inv or inv.user_id!=listing.seller_id: raise HTTPException(409,"Лот повреждён")
    price=listing.price
    fee_percent=await db.scalar(select(EconomyConfig.value).where(EconomyConfig.key=="market_fee_percent")) or 5
    fee=price*int(fee_percent)//100; seller_amount=price-fee
    try:
        await change_vld(db,uid,-price,"MARKET_BUY",str(listing_id))
        await change_vld(db,listing.seller_id,seller_amount,"MARKET_SELL",str(listing_id))
    except ValueError as e:
        await db.rollback();raise HTTPException(400,str(e))
    inv.user_id=uid;listing.active=False
    db.add(MarketTransaction(listing_id=listing.id,buyer_id=uid,seller_id=listing.seller_id,price=price,seller_amount=seller_amount,fee=fee))
    result={"listing_id":listing_id,"inventory_id":inv.id,"price":price,"fee":fee,"seller_amount":seller_amount}
    db.add(Operation(user_id=uid,key=key,result=result));await db.commit();return {"ok":True,**result}

class TradeCreateIn(BaseModel): receiver_id:int; sender_inventory_ids:list[int]=Field(default_factory=list,max_length=10); receiver_inventory_ids:list[int]=Field(default_factory=list,max_length=10)
@app.post("/api/trades")
async def trade_create(body:TradeCreateIn,request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    if body.receiver_id==uid: raise HTTPException(400,"Нельзя торговать с собой")
    for user_id in sorted({uid,body.receiver_id}): await lock_user(db,user_id)
    if await idempotent(db,uid,key): return {"ok":True,"already_processed":True}
    receiver=await db.get(User,body.receiver_id)
    if not receiver: raise HTTPException(404,"Получатель не найден")
    ids=list(dict.fromkeys(body.sender_inventory_ids+body.receiver_inventory_ids))
    if len(ids)>20: raise HTTPException(400,"Слишком много предметов")
    invs=(await db.execute(select(Inventory).where(Inventory.id.in_(ids)).with_for_update())).scalars().all() if ids else []
    by={x.id:x for x in invs}
    if any(i not in by for i in ids): raise HTTPException(400,"Предмет недоступен")
    if any(by[i].user_id!=uid for i in body.sender_inventory_ids): raise HTTPException(403,"Чужой предмет")
    if any(by[i].user_id!=body.receiver_id for i in body.receiver_inventory_ids): raise HTTPException(403,"Чужой предмет")
    if not body.sender_inventory_ids and not body.receiver_inventory_ids: raise HTTPException(400,"Trade пуст")
    t=Trade(sender_id=uid,receiver_id=body.receiver_id);db.add(t);await db.flush()
    for i in body.sender_inventory_ids: db.add(TradeItem(trade_id=t.id,inventory_id=i,owner_side="sender"))
    for i in body.receiver_inventory_ids: db.add(TradeItem(trade_id=t.id,inventory_id=i,owner_side="receiver"))
    db.add(Operation(user_id=uid,key=key,result={"trade_id":t.id}));await db.commit();return {"ok":True,"trade_id":t.id,"status":t.status}

@app.post("/api/trades/{trade_id}/confirm")
async def trade_confirm(trade_id:int,request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4()); t=(await db.execute(select(Trade).where(Trade.id==trade_id).with_for_update())).scalar_one_or_none()
    if not t or uid not in (t.sender_id,t.receiver_id): raise HTTPException(404,"Trade not found")
    if t.status!="pending": return {"ok":True,"status":t.status}
    if uid==t.sender_id: t.sender_confirmed=True
    else: t.receiver_confirmed=True
    if t.sender_confirmed and t.receiver_confirmed:
        rows=(await db.execute(select(TradeItem).where(TradeItem.trade_id==t.id).with_for_update())).scalars().all()
        invs=(await db.execute(select(Inventory).where(Inventory.id.in_([x.inventory_id for x in rows])).with_for_update())).scalars().all()
        im={x.id:x for x in invs}
        for row in rows:
            if row.inventory_id not in im: raise HTTPException(409,"Trade inventory unavailable")
            inv=im[row.inventory_id]; expected=t.sender_id if row.owner_side=="sender" else t.receiver_id
            if inv.user_id!=expected: raise HTTPException(409,"Trade inventory ownership changed")
        for row in rows:
            inv=im[row.inventory_id]; inv.user_id=t.receiver_id if row.owner_side=="sender" else t.sender_id
        t.status="completed"
    db.add(Operation(user_id=uid,key=key,result={"trade_id":t.id,"status":t.status}));await db.commit();return {"ok":True,"status":t.status}

@app.get("/api/referrals")
async def referrals(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    u=await db.get(User,uid); count=(await db.execute(select(func.count(Referral.id)).where(Referral.inviter_id==uid))).scalar() or 0
    return {"code":u.referral_code,"count":count,"link":f"https://t.me/{settings.bot_username}?startapp={u.referral_code}"}

@app.get("/api/shop")
async def shop(db:AsyncSession=Depends(get_db)):
    return [{"id":p.id,"code":p.code,"name":p.name,"description":p.description,"stars":p.stars_price,"image":p.image,"category":p.category} for p in (await db.execute(select(StarsProduct).where(StarsProduct.active==True))).scalars().all()]

@app.post("/api/shop/purchase")
async def purchase(body:PurchaseIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    await lock_user(db,uid)
    p=await db.get(StarsProduct,body.product_id)
    if not p or not p.active: raise HTTPException(404,"Товар недоступен")
    if not settings.bot_token: raise HTTPException(503,"Telegram payment is not configured")
    owned=(await db.execute(select(UserCosmetic).where(UserCosmetic.user_id==uid,UserCosmetic.product_id==p.id))).scalar_one_or_none()
    if owned: raise HTTPException(409,"Товар уже приобретён")
    pending=(await db.execute(select(StarsPurchase).where(StarsPurchase.user_id==uid,StarsPurchase.product_id==p.id,StarsPurchase.status=="pending").order_by(StarsPurchase.id.desc()))).scalars().first()
    if pending and pending.invoice_url: return {"status":"pending","payload":pending.payload,"stars":p.stars_price,"invoice_url":pending.invoice_url}
    payload=f"vldst:stars:{uid}:{p.id}:{uuid.uuid4().hex}"
    purchase=StarsPurchase(user_id=uid,product_id=p.id,payload=payload,status="pending");db.add(purchase);await db.flush()
    url=f"https://api.telegram.org/bot{settings.bot_token}/createInvoiceLink"
    body_json={"title":p.name,"description":p.description[:255],"payload":payload,"currency":"XTR","prices":[{"label":p.name,"amount":p.stars_price}]}
    async with httpx.AsyncClient(timeout=15) as client:
        r=await client.post(url,json=body_json)
    if r.status_code!=200 or not r.json().get("ok"):
        await db.rollback();raise HTTPException(502,"Telegram invoice creation failed")
    invoice_url=r.json()["result"];purchase.invoice_url=invoice_url;await db.commit();return {"status":"pending","payload":payload,"stars":p.stars_price,"invoice_url":invoice_url}

@app.get("/api/shop/owned")
async def owned_shop(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    q=await db.execute(select(UserCosmetic,StarsProduct).join(StarsProduct,UserCosmetic.product_id==StarsProduct.id).where(UserCosmetic.user_id==uid));return [{"product_id":p.id,"name":p.name,"category":p.category,"equipped":uc.equipped} for uc,p in q.all()]


@app.post("/api/shop/equip/{product_id}")
async def equip_cosmetic(product_id:int,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    await lock_user(db,uid)
    p=await db.get(StarsProduct,product_id);uc=(await db.execute(select(UserCosmetic).where(UserCosmetic.user_id==uid,UserCosmetic.product_id==product_id).with_for_update())).scalar_one_or_none()
    if not p or not uc: raise HTTPException(404,"Косметика не найдена")
    rows=(await db.execute(select(UserCosmetic,StarsProduct).join(StarsProduct,UserCosmetic.product_id==StarsProduct.id).where(UserCosmetic.user_id==uid,StarsProduct.category==p.category))).all()
    for x,_ in rows: x.equipped=False
    uc.equipped=True;await db.commit();return {"ok":True,"product_id":product_id,"category":p.category}

@app.get("/api/transactions")
async def transactions(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(Transaction).where(Transaction.user_id==uid).order_by(Transaction.id.desc()).limit(100))).scalars().all()
    return [{"kind":t.kind,"amount":t.amount,"currency":t.currency,"balance_after":t.balance_after,"reference":t.reference,"created_at":t.created_at} for t in rows]


@app.get("/api/achievements")
async def achievements(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    await evaluate_achievements(db,uid); rows=(await db.execute(select(Achievement))).scalars().all();earned=set((await db.execute(select(UserAchievement.achievement_id).where(UserAchievement.user_id==uid))).scalars().all());u=await ensure_user(db,uid);await db.commit()
    return [{"id":a.id,"code":a.code,"name":a.name,"category":a.category,"reward_vld":a.reward_vld,"reward_xp":a.reward_xp,"title":a.title_reward,"unlocked":a.id in earned} for a in rows]

@app.get("/api/notifications")
async def notifications(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(Notification).where(Notification.user_id==uid).order_by(Notification.id.desc()).limit(50))).scalars().all()
    return [{"id":n.id,"title":n.title,"body":n.body,"read":n.read} for n in rows]

@app.get("/api/seasons")
async def seasons(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(Season).order_by(Season.id.desc()))).scalars().all();out=[]
    for s in rows:
        pgr=await get_season_progress(db,uid,s); rewards=(await db.execute(select(SeasonReward).where(SeasonReward.season_id==s.id).order_by(SeasonReward.level))).scalars().all()
        out.append({"id":s.id,"name":s.name,"start":s.start_at,"end":s.end_at,"levels":s.levels,"xp":pgr.xp,"level":pgr.level,"claimed_levels":pgr.claimed_levels,"rewards":[{"level":r.level,"vld":r.free_vld,"xp":r.free_xp,"scrap":r.free_scrap,"premium_product_id":r.premium_product_id} for r in rewards]})
    await db.commit();return out

@app.post("/api/seasons/{season_id}/claim")
async def season_claim(season_id:int,body:SeasonClaimIn,request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    await lock_user(db,uid)
    if await idempotent(db,uid,key): return {"ok":True,"already_processed":True}
    s=await db.get(Season,season_id);now=datetime.now(timezone.utc)
    if not s or not(s.start_at<=now<=s.end_at): raise HTTPException(400,"Season не активен")
    if body.level>s.levels: raise HTTPException(400,"Invalid level")
    pgr=await get_season_progress(db,uid,s)
    await db.refresh(pgr, attribute_names=["xp","level","claimed_levels"])
    await db.execute(select(SeasonProgress).where(SeasonProgress.id==pgr.id).with_for_update())
    if pgr.level<body.level: raise HTTPException(400,"Season level ещё не достигнут")
    claimed=list(pgr.claimed_levels or [])
    if body.level in claimed: raise HTTPException(400,"Награда уже получена")
    reward=(await db.execute(select(SeasonReward).where(SeasonReward.season_id==s.id,SeasonReward.level==body.level))).scalar_one_or_none()
    if not reward: raise HTTPException(404,"Season reward not configured")
    if reward.free_vld: await change_vld(db,uid,reward.free_vld,"SEASON_REWARD",f"{s.id}:{body.level}")
    u=await ensure_user(db,uid);u.xp+=reward.free_xp;u.level=level_from_total_xp(u.xp)
    if reward.free_scrap: await change_scrap(db,uid,reward.free_scrap,"SEASON_REWARD")
    if reward.premium_product_id and pgr.premium_pass:
        exists=await db.scalar(select(UserCosmetic.id).where(UserCosmetic.user_id==uid,UserCosmetic.product_id==reward.premium_product_id))
        if not exists: db.add(UserCosmetic(user_id=uid,product_id=reward.premium_product_id))
    claimed.append(body.level);pgr.claimed_levels=claimed;db.add(Operation(user_id=uid,key=key,result={"season_id":s.id,"level":body.level}));await db.commit()
    return {"ok":True,"level":body.level,"vld":reward.free_vld,"xp":reward.free_xp,"scrap":reward.free_scrap}

@app.post("/api/seasons/{season_id}/xp")
async def season_xp_disabled(season_id:int, uid:int=Depends(current_user)):
    raise HTTPException(403,"Season XP is generated by verified gameplay actions")

@app.post("/api/daily/claim")
async def daily_claim(request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    await lock_user(db,uid)
    if await idempotent(db,uid,key): return {"ok":True,"already_processed":True}
    u=await db.get(User,uid)
    now=datetime.now(timezone.utc)
    if u.last_daily and now.date() == u.last_daily.date(): raise HTTPException(400,"Daily уже получен")
    if u.last_daily and (now.date()-u.last_daily.date()).days==1: u.streak=min(7,u.streak+1)
    else: u.streak=1
    rewards={1:500,2:750,3:1000,4:1500,5:2000,6:3000,7:5000}
    amount=rewards[u.streak]
    await change_vld(db,uid,amount,"DAILY_REWARD",key)
    if u.streak==7: await change_scrap(db,uid,10,"DAILY_REWARD")
    u.last_daily=now
    await award_xp(db,uid,25+u.streak*5); await record_action(db,uid,"daily")
    db.add(Operation(user_id=uid,key=key,result={"vld":amount,"streak":u.streak})); await db.commit()
    return {"ok":True,"vld":amount,"streak":u.streak}

@app.post("/api/quests/{quest_id}/progress")
async def quest_progress(quest_id:int,body:EventProgressIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    q=await db.get(Quest,quest_id)
    if not q or not q.active: raise HTTPException(404,"Задание больше недоступно")
    raise HTTPException(403,"Quest progress is generated by verified actions")

class CraftIn(BaseModel): recipe_id:int; inventory_ids:list[int]=Field(default_factory=list,max_length=20)
@app.get("/api/craft/recipes")
async def craft_recipes(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(CraftRecipe).where(CraftRecipe.active==True).order_by(CraftRecipe.id))).scalars().all()
    return [{"id":r.id,"name":r.name,"output_item_id":r.output_item_id,"requirements":r.requirements,"vld_cost":r.vld_cost,"scrap_cost":r.scrap_cost,"core_cost":r.core_cost,"min_level":r.min_level} for r in rows]

@app.post("/api/craft")
async def craft(body:CraftIn,request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4())
    await lock_user(db,uid)
    if await idempotent(db,uid,key): return {"ok":True,"already_processed":True}
    r=await db.get(CraftRecipe,body.recipe_id)
    u=await db.get(User,uid)
    if not r or not r.active or u.level<r.min_level: raise HTTPException(400,"Recipe unavailable")
    req=body.inventory_ids or []
    if r.requirements.get("items") and len(req)!=len(r.requirements["items"]): raise HTTPException(400,"Неверный набор предметов")
    if req:
        invs=(await db.execute(select(Inventory).where(Inventory.user_id==uid,Inventory.id.in_(req)).with_for_update())).scalars().all()
        if len(invs)!=len(req) or len(set(req))!=len(req): raise HTTPException(400,"Предметы недоступны")
        await db.execute(__import__('sqlalchemy').delete(Inventory).where(Inventory.id.in_(req),Inventory.user_id==uid))
    await change_vld(db,uid,-r.vld_cost,"CRAFT",key)
    await change_scrap(db,uid,-r.scrap_cost,"CRAFT")
    b=await get_balance(db,uid,for_update=True)
    if b.core<r.core_cost: raise HTTPException(400,"Недостаточно CORE")
    b.core-=r.core_cost
    inv=Inventory(user_id=uid,item_id=r.output_item_id);db.add(inv);await db.flush()
    db.add(CraftHistory(user_id=uid,recipe_id=r.id,output_inventory_id=inv.id))
    db.add(Operation(user_id=uid,key=key,result={"inventory_id":inv.id}));await record_action(db,uid,"craft");await db.commit()
    return {"ok":True,"inventory_id":inv.id}

class FusionIn(BaseModel): inventory_ids:list[int]=Field(min_length=3,max_length=3)
@app.post("/api/fusion")
async def fusion(body:FusionIn,request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4()); await lock_user(db,uid)
    if await idempotent(db,uid,key): return {"ok":True,"already_processed":True}
    if len(set(body.inventory_ids))!=3: raise HTTPException(400,"Нужны 3 разных предмета")
    invs=(await db.execute(select(Inventory,Item).join(Item,Inventory.item_id==Item.id).where(Inventory.user_id==uid,Inventory.id.in_(body.inventory_ids)).with_for_update())).all()
    if len(invs)!=3: raise HTTPException(400,"Предметы недоступны")
    ranks={"COMMON":"RARE","RARE":"EPIC","EPIC":"LEGENDARY"}; rarities=[it.rarity for _,it in invs]
    if len(set(rarities))!=1 or rarities[0] not in ranks: raise HTTPException(400,"Нельзя объединить эти предметы")
    output_rarity=ranks[rarities[0]]; candidates=(await db.execute(select(Item).where(Item.rarity==output_rarity))).scalars().all()
    if not candidates: raise HTTPException(400,"Нет доступного результата")
    await db.execute(__import__('sqlalchemy').delete(Inventory).where(Inventory.id.in_(body.inventory_ids),Inventory.user_id==uid))
    out=Inventory(user_id=uid,item_id=secrets.choice(candidates).id);db.add(out);await db.flush()
    db.add(FusionHistory(user_id=uid,input_inventory_ids=body.inventory_ids,output_inventory_id=out.id));db.add(Operation(user_id=uid,key=key,result={"inventory_id":out.id,"rarity":output_rarity}));await record_action(db,uid,"fusion");await db.commit()
    return {"ok":True,"inventory_id":out.id,"rarity":output_rarity}

@app.get("/api/guild/quests")
async def guild_quests(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    m=(await db.execute(select(GuildMember).where(GuildMember.user_id==uid))).scalar_one_or_none()
    if not m:return []
    rows=(await db.execute(select(GuildQuest).where(GuildQuest.guild_id==m.guild_id,GuildQuest.active==True))).scalars().all()
    return [{"id":q.id,"title":q.title,"target":q.target,"progress":q.progress,"reward_vld":q.reward_vld,"reward_xp":q.reward_xp} for q in rows]

@app.post("/api/guild/quests/{quest_id}/claim")
async def guild_quest_claim(quest_id:int,request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4()); await lock_user(db,uid)
    if await idempotent(db,uid,key): return {"ok":True,"already_processed":True}
    m=(await db.execute(select(GuildMember).where(GuildMember.user_id==uid))).scalar_one_or_none()
    q=(await db.execute(select(GuildQuest).where(GuildQuest.id==quest_id).with_for_update())).scalar_one_or_none()
    if not m or not q or q.guild_id!=m.guild_id or not q.active: raise HTTPException(404,"Guild quest unavailable")
    if q.progress<q.target: raise HTTPException(400,"Задание ещё не выполнено")
    claimed=await db.scalar(select(GuildQuestClaim.id).where(GuildQuestClaim.guild_quest_id==q.id,GuildQuestClaim.user_id==uid))
    if claimed: raise HTTPException(400,"Награда уже получена")
    await change_vld(db,uid,q.reward_vld,"GUILD_QUEST_REWARD",str(q.id));await award_xp(db,uid,q.reward_xp);db.add(GuildQuestClaim(guild_quest_id=q.id,user_id=uid));db.add(Operation(user_id=uid,key=key,result={"guild_quest_id":q.id}));await db.commit();return {"ok":True,"vld":q.reward_vld,"xp":q.reward_xp}

class PromoIn(BaseModel): code:str=Field(min_length=2,max_length=80)
@app.post("/api/promo/redeem")
async def redeem_promo(body:PromoIn,request:Request,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    key=request.headers.get("Idempotency-Key") or str(uuid.uuid4()); await lock_user(db,uid)
    if await idempotent(db,uid,key): return {"ok":True,"already_processed":True}
    p=(await db.execute(select(PromoCode).where(PromoCode.code==body.code.upper(),PromoCode.active==True).with_for_update())).scalar_one_or_none()
    if not p or (p.expires_at and p.expires_at<datetime.now(timezone.utc)) or p.uses>=p.max_uses: raise HTTPException(400,"Промокод недействителен")
    if await db.scalar(select(PromoRedemption.id).where(PromoRedemption.promo_id==p.id,PromoRedemption.user_id==uid)): raise HTTPException(400,"Промокод уже использован")
    p.uses+=1;db.add(PromoRedemption(promo_id=p.id,user_id=uid));await change_vld(db,uid,p.reward_vld,"PROMO_REWARD",p.code);await award_xp(db,uid,p.reward_xp);db.add(Operation(user_id=uid,key=key,result={"code":p.code}));await db.commit();return {"ok":True,"vld":p.reward_vld,"xp":p.reward_xp}

def admin_check(uid): 
    if uid not in settings.admin_id_set: raise HTTPException(403,"Admin access required")

class AdminItemGrantIn(BaseModel): item_id:int
class AdminPremiumIn(BaseModel): days:int=Field(ge=1,le=3650)
class AdminNotificationIn(BaseModel): title:str=Field(min_length=1,max_length=120); body:str=Field(min_length=1,max_length=4000)
class AdminCaseIn(BaseModel): name:str; description:str; price:int=Field(ge=1); image:str; weights:dict
class AdminQuestIn(BaseModel): title:str; description:str; category:str; quest_type:str; target:int=Field(ge=1); reward_vld:int=Field(ge=0); reward_xp:int=Field(ge=0); period:str="daily"

@app.post("/api/admin/users/{user_id}/ban")
async def admin_ban(user_id:int,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid); u=await db.get(User,user_id)
    if not u: raise HTTPException(404,"User not found")
    u.banned=True;u.session_version+=1;db.add(AuditLog(admin_user_id=uid,action="ban",target=str(user_id),payload={}));await db.commit();return {"ok":True}

@app.post("/api/admin/users/{user_id}/unban")
async def admin_unban(user_id:int,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid); u=await db.get(User,user_id)
    if not u: raise HTTPException(404,"User not found")
    u.banned=False;u.session_version+=1;db.add(AuditLog(admin_user_id=uid,action="unban",target=str(user_id),payload={}));await db.commit();return {"ok":True}

@app.delete("/api/admin/users/{user_id}/item/{inventory_id}")
async def admin_remove_item(user_id:int,inventory_id:int,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid); inv=await db.get(Inventory,inventory_id)
    if not inv or inv.user_id!=user_id: raise HTTPException(404,"Inventory item not found")
    await db.delete(inv);db.add(AuditLog(admin_user_id=uid,action="remove_item",target=str(user_id),payload={"inventory_id":inventory_id}));await db.commit();return {"ok":True}

@app.post("/api/admin/users/{user_id}/item")
async def admin_give_item(user_id:int,body:AdminItemGrantIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid); u=await db.get(User,user_id); it=await db.get(Item,body.item_id)
    if not u or not it: raise HTTPException(404,"User or item not found")
    inv=Inventory(user_id=user_id,item_id=body.item_id);db.add(inv);await db.flush();db.add(AuditLog(admin_user_id=uid,action="give_item",target=str(user_id),payload=body.model_dump()));await db.commit();return {"ok":True,"inventory_id":inv.id}

@app.post("/api/admin/users/{user_id}/premium")
async def admin_give_premium(user_id:int,body:AdminPremiumIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid); u=await db.get(User,user_id)
    if not u: raise HTTPException(404,"User not found")
    now=datetime.now(timezone.utc); p=(await db.execute(select(Premium).where(Premium.user_id==user_id).with_for_update())).scalar_one_or_none()
    if p: p.expires_at=max(p.expires_at,now)+timedelta(days=body.days)
    else: db.add(Premium(user_id=user_id,expires_at=now+timedelta(days=body.days)))
    db.add(AuditLog(admin_user_id=uid,action="give_premium",target=str(user_id),payload=body.model_dump()));await db.commit();return {"ok":True}

@app.post("/api/admin/users/{user_id}/notify")
async def admin_notify(user_id:int,body:AdminNotificationIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid); u=await db.get(User,user_id)
    if not u: raise HTTPException(404,"User not found")
    db.add(Notification(user_id=user_id,title=body.title,body=body.body));db.add(AuditLog(admin_user_id=uid,action="notification",target=str(user_id),payload=body.model_dump()));await db.commit();return {"ok":True}

@app.post("/api/admin/cases")
async def admin_create_case(body:AdminCaseIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid); c=Case(**body.model_dump());db.add(c);db.add(AuditLog(admin_user_id=uid,action="create_case",target=body.name,payload=body.model_dump()));await db.commit();return {"ok":True,"id":c.id}

@app.post("/api/admin/quests")
async def admin_create_quest(body:AdminQuestIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid); q=Quest(**body.model_dump());db.add(q);db.add(AuditLog(admin_user_id=uid,action="create_quest",target=body.title,payload=body.model_dump()));await db.commit();return {"ok":True,"id":q.id}

@app.get("/api/admin/economy")
async def admin_economy(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid); rows=(await db.execute(select(EconomyConfig).order_by(EconomyConfig.key))).scalars().all();return [{"key":x.key,"value":x.value} for x in rows]

class EconomySetIn(BaseModel): value:int
@app.put("/api/admin/economy/{key}")
async def admin_set_economy(key:str,body:EconomySetIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid); row=await db.get(EconomyConfig,key)
    if not row: row=EconomyConfig(key=key,value=body.value);db.add(row)
    else: row.value=body.value
    db.add(AuditLog(admin_user_id=uid,action="economy_config",target=key,payload=body.model_dump()));await db.commit();return {"ok":True,"key":key,"value":body.value}

class BroadcastIn(BaseModel): title:str=Field(min_length=1,max_length=120); body:str=Field(min_length=1,max_length=4000)
@app.post("/api/admin/broadcast")
async def admin_broadcast(body:BroadcastIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid)
    ids=(await db.execute(select(User.id).where(User.banned==False))).scalars().all()
    db.add_all([Notification(user_id=x,title=body.title,body=body.body) for x in ids])
    db.add(AuditLog(admin_user_id=uid,action="broadcast",target="all",payload={"count":len(ids),**body.model_dump()}));await db.commit();return {"ok":True,"queued":len(ids)}

@app.get("/api/admin/dashboard")
async def dashboard(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid)
    users=(await db.execute(select(func.count(User.id)))).scalar() or 0
    tx=(await db.execute(select(func.coalesce(func.sum(Transaction.amount),0)).where(Transaction.currency=="VLD"))).scalar() or 0
    purchases=(await db.execute(select(func.count(StarsPurchase.id)).where(StarsPurchase.status=="paid"))).scalar() or 0
    return {"users":users,"vld_net_ledger":tx,"paid_purchases":purchases}

@app.get("/api/admin/users")
async def admin_users(uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid)
    rows=(await db.execute(select(User).order_by(User.id.desc()).limit(100))).scalars().all()
    return [{"id":u.id,"telegram_id":u.telegram_id,"username":u.username,"nickname":u.nickname,"level":u.level,"banned":u.banned} for u in rows]

@app.post("/api/admin/users/{user_id}/adjust")
async def admin_adjust(user_id:int,body:AdjustIn,uid:int=Depends(current_user),db:AsyncSession=Depends(get_db)):
    admin_check(uid); target=await db.get(User,user_id)
    if not target: raise HTTPException(404,"User not found")
    if body.currency!="VLD": raise HTTPException(400,"Only VLD adjustment is enabled here")
    val=await change_vld(db,user_id,body.amount,"ADMIN_ADJUSTMENT",body.reason)
    db.add(AuditLog(admin_user_id=uid,action="balance_adjust",target=str(user_id),payload=body.model_dump()))
    await db.commit(); return {"ok":True,"vld":val}

@app.get("/admin/")
async def admin_page(): return FileResponse(ADMIN_DIR / "index.html")

@app.get("/style.css")
async def app_css(): return FileResponse(FRONTEND_DIR / "style.css", media_type="text/css")

@app.get("/app.js")
async def app_js(): return FileResponse(FRONTEND_DIR / "app.js", media_type="application/javascript")

@app.get("/")
async def app_page(): return FileResponse(FRONTEND_DIR / "index.html")

# Static mounts are intentionally registered after API routes so /api/* is never swallowed by the root mount.
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
app.mount("/admin-static", StaticFiles(directory=ADMIN_DIR), name="admin-static")
