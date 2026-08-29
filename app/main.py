from fastapi import FastAPI,Depends,HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select,func,desc
from sqlalchemy.ext.asyncio import AsyncSession
from .db import init_db,get_db,User,Case,Item,Inventory,Transaction,Quest,QuestClaim,Referral,Achievement,AchievementUser,Guild,GuildMember,Gift
from .auth import telegram_user
from .economy import CASES,RARITIES,roll
from .games import GAMES,play
from .config import settings
from datetime import datetime,timezone,timedelta
import secrets,string

app=FastAPI(title="VLDST UNDERGROUND",version="1.0.0")
app.mount("/app",StaticFiles(directory="frontend",html=True),name="frontend")

@app.on_event("startup")
async def startup():
    await init_db()
    async with __import__("app.db",fromlist=["Session"]).Session() as db:
        if not (await db.execute(select(func.count(Case.id)))).scalar():
            for i,(n,p) in enumerate(CASES,1): db.add(Case(id=i,name=n,price=p,image=f"/assets/cases/case_{i}.svg"))
        if not (await db.execute(select(func.count(Item.id)))).scalar():
            rar=list(RARITIES)
            for i in range(1,161):
                r = (
                    "COMMON" if i <= 50 else
                    "RARE" if i <= 90 else
                    "EPIC" if i <= 120 else
                    "LEGENDARY" if i <= 145 else
                    "MYTHIC" if i <= 157 else
                    "SECRET"
                )

                db.add(Item(
                    id=i,
                    name=f"VLDST {r} #{i}",
                    description="",
                    rarity=r,
                    collection="UNDERGROUND",
                    value=i * 250,
                    base_value=i * 250,
                    image=f"/assets/items/item_{i}.svg"
                ))

            qs = [
                ("First Signal","Открой 1 кейс","cases",1,500,20),
                ("Network Explorer","Открой 3 кейса","cases",3,1200,35),
                ("Case Hunter","Открой 5 кейсов","cases",5,2500,60),
                ("Game Starter","Сыграй 3 игры","games",3,800,30),
                ("Game Addict","Сыграй 10 игр","games",10,2500,80),
                ("Recycler","Продай 3 предмета","sell",3,1000,35),
                ("Upgrade","Улучши предмет","upgrade",1,1500,50),
                ("Collector","Собери 10 предметов","items",10,2000,60),
                ("Rare Signal","Получи RARE+","rare",1,1200,40),
                ("Epic Signal","Получи EPIC+","epic",1,3000,90),
                ("Recruit","Пригласи игрока","referral",1,1500,70),
                ("Streak 3","Заходи 3 дня","streak",3,1800,80),
                ("Rich","Заработай 5000 VLD","earn",5000,1000,50),
                ("Whale","Заработай 25000 VLD","earn",25000,5000,120),
                ("Neon","Открой NEON+","neon",1,3500,100),
                ("Secret Hunter","Найди SECRET","secret",1,25000,300),
                ("Quest Master","Выполни 5 квестов","quest",5,4000,120),
                ("Week","Зайди 7 дней","streak",7,7000,200),
                ("Level 5","Достигни 5 уровня","level",5,5000,180),
                ("Level 10","Достигни 10 уровня","level",10,15000,350)
            ]

            for i,q in enumerate(qs,1):
                db.add(Quest(
                    id=i,
                    title=q[0],
                    description=q[1],
                    kind=q[2],
                    target=q[3],
                    reward=q[4],
                    xp=q[5]
                ))
async def current(db,tu):
    u=(await db.execute(select(User).where(User.telegram_id==tu["id"]))).scalar_one_or_none()
    if not u:
        code="VLD-"+''.join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(8))
        u=User(telegram_id=tu["id"],username=tu.get("username"),first_name=tu.get("first_name"),referral_code=code)
        db.add(u); await db.commit(); await db.refresh(u)
    if u.banned: raise HTTPException(403,"Аккаунт заблокирован")
    return u
def user_json(u): return {"telegram_id":u.telegram_id,"username":u.username,"first_name":u.first_name,"coins":u.coins,"stars":u.stars,"xp":u.xp,"level":u.level,"energy":u.energy,"streak":u.streak,"premium_until":u.premium_until}
def add_xp(u,x):
    u.xp+=x; u.level=max(1,1+u.xp//1000)
async def tx(db,u,kind,amount,meta=None):
    u.coins+=amount
    db.add(Transaction(telegram_id=u.telegram_id,kind=kind,amount=amount,balance=u.coins,meta=meta or {}))

@app.get("/")
async def root(): return {"ok":True,"project":"VLDST UNDERGROUND","version":"1.0.0"}
@app.get("/health")
async def health(): return {"ok":True}

@app.get("/api/me")
async def me(tu=Depends(telegram_user),db=Depends(get_db)):
    return {"ok":True,"user":user_json(await current(db,tu))}

@app.get("/api/catalog")
async def catalog():
    return {"cases":[{"id":i+1,"name":n,"price":p,"odds":RARITIES,"image":f"/assets/cases/case_{i+1}.svg"} for i,(n,p) in enumerate(CASES)],
            "games":{k:{"energy":v[0],"max_score":v[1],"multiplier":v[2]} for k,v in GAMES.items()},
            "stars_products":[{"id":"premium7","title":"Premium 7 days","stars":100},{"id":"premium30","title":"Premium 30 days","stars":300},{"id":"profile_neon","title":"Neon Profile","stars":25},{"id":"energy","title":"Energy Pack","stars":15}]}

@app.post("/api/cases/{case_id}/open")
async def open_case(case_id:int,tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); c=await db.get(Case,case_id)
    if not c or not c.active: raise HTTPException(404,"Кейс не найден")
    if u.coins<c.price: raise HTTPException(400,"Недостаточно VLD")
    u.coins-=c.price
    rarity=roll()
    items=(await db.execute(select(Item).where(Item.rarity==rarity))).scalars().all()
    if not items: raise HTTPException(500,"Нет предметов редкости")
    item=items[secrets.randbelow(len(items))]
    inv=Inventory(telegram_id=u.telegram_id,item_id=item.id)
    db.add(inv); add_xp(u,10)
    db.add(Transaction(telegram_id=u.telegram_id,kind="case_open",amount=-c.price,balance=u.coins,meta={"case":c.id,"item":item.id,"rarity":rarity}))
    await db.commit(); await db.refresh(inv)
    return {"ok": True, "item": {"id": item.id, "name": item.name, "rarity": item.rarity, "value": item.value, "image": item.image}, "user": user_json(u), "odds": RARITIES}

@app.get("/api/cases/{case_id}/items")
async def case_items(case_id:int,db=Depends(get_db)):
    items=(await db.execute(select(Item).order_by(Item.id))).scalars().all()
    return {"items": [{"id": x.id, "name": x.name, "rarity": x.rarity, "value": x.value, "image": x.image} for x in items]}

@app.get("/api/inventory")
async def inventory(tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu)
    rows=(await db.execute(select(Inventory,Item).join(Item,Item.id==Inventory.item_id).where(Inventory.telegram_id==u.telegram_id,Inventory.sold==False).order_by(Inventory.id.desc()))).all()
    return {"items":[{"inventory_id":i.id,"id":it.id,"name":it.name,"rarity":it.rarity,"value":it.value,"level":i.level,"locked":i.locked,"image":it.image} for i,it in rows]}

@app.post("/api/inventory/{inventory_id}/sell")
async def sell(inventory_id:int,tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); row=(await db.execute(select(Inventory,Item).join(Item,Item.id==Inventory.item_id).where(Inventory.id==inventory_id,Inventory.telegram_id==u.telegram_id,Inventory.sold==False))).first()
    if not row: raise HTTPException(404,"Предмет не найден")
    inv,it=row
    if inv.locked: raise HTTPException(400,"Предмет заблокирован")
    value=int(it.value*(1+0.15*(inv.level-1))); inv.sold=True; await tx(db,u,"sell",value,{"item":it.id}); add_xp(u,5)
    await db.commit(); return {"ok":True,"value":value,"user":user_json(u)}

@app.post("/api/inventory/{inventory_id}/upgrade")
async def upgrade(inventory_id:int,tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); row=(await db.execute(select(Inventory,Item).join(Item,Item.id==Inventory.item_id).where(Inventory.id==inventory_id,Inventory.telegram_id==u.telegram_id,Inventory.sold==False))).first()
    if not row: raise HTTPException(404,"Предмет не найден")
    inv,it=row; cost=max(100,int(it.value*0.25*inv.level))
    if u.coins<cost: raise HTTPException(400,"Недостаточно VLD")
    u.coins-=cost; inv.level+=1; add_xp(u,15); await db.commit()
    return {"ok":True,"level":inv.level,"cost":cost,"user":user_json(u)}

@app.post("/api/inventory/{inventory_id}/recycle")
async def recycle(inventory_id:int,tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); row=(await db.execute(select(Inventory,Item).join(Item,Item.id==Inventory.item_id).where(Inventory.id==inventory_id,Inventory.telegram_id==u.telegram_id,Inventory.sold==False))).first()
    if not row: raise HTTPException(404,"Предмет не найден")
    inv,it=row
    if inv.locked: raise HTTPException(400,"Предмет заблокирован")
    reward=int(it.value*{"COMMON":.18,"RARE":.22,"EPIC":.28,"LEGENDARY":.35,"MYTHIC":.45,"SECRET":.6}[it.rarity])
    inv.sold=True; await tx(db,u,"recycle",reward,{"item":it.id}); await db.commit()
    return {"ok":True,"reward":reward,"user":user_json(u)}

@app.get("/api/quests")
async def quests(tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); qs=(await db.execute(select(Quest).order_by(Quest.id))).scalars().all()
    claimed=set((await db.execute(select(QuestClaim.quest_id).where(QuestClaim.telegram_id==u.telegram_id)) ).scalars().all())
    return {"quests":[{"id":q.id,"title":q.title,"description":q.description,"target":q.target,"reward":q.reward,"xp":q.xp,"claimed":q.id in claimed} for q in qs]}

@app.post("/api/quests/{quest_id}/claim")
async def quest_claim(quest_id:int,tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); q=await db.get(Quest,quest_id)
    if not q: raise HTTPException(404,"Квест не найден")
    if (await db.execute(select(QuestClaim).where(QuestClaim.telegram_id==u.telegram_id,QuestClaim.quest_id==q.id))).scalar_one_or_none(): raise HTTPException(400,"Уже получено")
    # MVP: claim only when the server has enough evidence for simple quest types.
    counts={"cases":await db.scalar(select(func.count(Transaction.id)).where(Transaction.telegram_id==u.telegram_id,Transaction.kind=="case_open")),
            "games":await db.scalar(select(func.count(Transaction.id)).where(Transaction.telegram_id==u.telegram_id,Transaction.kind=="game")),
            "sell":await db.scalar(select(func.count(Transaction.id)).where(Transaction.telegram_id==u.telegram_id,Transaction.kind.in_(["sell","recycle"]))),
            "items":await db.scalar(select(func.count(Inventory.id)).where(Inventory.telegram_id==u.telegram_id))}
    progress=counts.get(q.kind,0)
    if q.kind=="earn": progress=max(0,u.xp*0+u.coins)
    if q.kind=="level": progress=u.level
    if q.kind=="streak": progress=u.streak
    if q.kind=="referral": progress=await db.scalar(select(func.count(Referral.id)).where(Referral.inviter==u.telegram_id))
    if progress<q.target: raise HTTPException(400,f"Прогресс {progress}/{q.target}")
    db.add(QuestClaim(telegram_id=u.telegram_id,quest_id=q.id)); await tx(db,u,"quest",q.reward,{"quest":q.id}); add_xp(u,q.xp); await db.commit()
    return {"ok":True,"reward":q.reward,"user":user_json(u)}

@app.post("/api/games/{game}/play")
async def game(game:str,tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); game=game.upper()
    if game not in GAMES: raise HTTPException(404,"Игра не найдена")
    energy,rewardmax,mult=GAMES[game]
    if u.energy<energy: raise HTTPException(400,"Недостаточно энергии")
    score,reward,xp,e=play(game); u.energy-=e; await tx(db,u,"game",reward,{"game":game,"score":score}); add_xp(u,xp); await db.commit()
    return {"ok":True,"game":game,"score":score,"reward":reward,"xp":xp,"energy":e,"user":user_json(u)}

@app.post("/api/daily")
async def daily(tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); today=datetime.now(timezone.utc).date()
    last=(await db.execute(select(Transaction).where(Transaction.telegram_id==u.telegram_id,Transaction.kind=="daily").order_by(Transaction.id.desc()))).scalars().first()
    if last and last.created_at and last.created_at.date()==today: raise HTTPException(400,"Сегодня уже получено")
    u.streak+=1; reward=1000+min(u.streak,30)*100; await tx(db,u,"daily",reward,{"streak":u.streak}); add_xp(u,25); u.energy=min(100,u.energy+20); await db.commit()
    return {"ok":True,"reward":reward,"streak":u.streak,"user":user_json(u)}

@app.get("/api/profile")
async def profile(tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); inv=await db.scalar(select(func.count(Inventory.id)).where(Inventory.telegram_id==u.telegram_id,Inventory.sold==False))
    cases=await db.scalar(select(func.count(Transaction.id)).where(Transaction.telegram_id==u.telegram_id,Transaction.kind=="case_open"))
    games=await db.scalar(select(func.count(Transaction.id)).where(Transaction.telegram_id==u.telegram_id,Transaction.kind=="game"))
    return {"user":user_json(u),"stats":{"items":inv,"cases":cases,"games":games,"streak":u.streak},"referral_code":u.referral_code}

@app.get("/api/leaderboard")
async def leaderboard(db=Depends(get_db)):
    users=(await db.execute(select(User).where(User.banned==False).order_by(desc(User.xp),desc(User.coins)).limit(50))).scalars().all()
    return {"leaders":[{"rank":i+1,"username":u.username or u.first_name or "Player","level":u.level,"xp":u.xp,"coins":u.coins} for i,u in enumerate(users)]}

@app.get("/api/collections")
async def collections(tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); total=await db.scalar(select(func.count(Inventory.id)).where(Inventory.telegram_id==u.telegram_id,Inventory.sold==False))
    return {"collections":[{"name":"UNDERGROUND","owned":total,"total":160,"progress":round(min(100,total/160*100),1),"reward":10000}]}

@app.get("/api/referrals")
async def referrals(tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); n=await db.scalar(select(func.count(Referral.id)).where(Referral.inviter==u.telegram_id))
    return {"code":u.referral_code,"invited":n,"reward_per_friend":500,"link":f"https://t.me/your_bot?start=ref_{u.referral_code}"}

@app.get("/api/events")
async def events():
    return {"events":[{"id":"season1","title":"UNDERGROUND SEASON 1","description":"Collect XP and climb the leaderboard","active":True,"progress":0,"goal":1000000}]}

@app.post("/api/guilds/create")
async def guild_create(tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); name="VLD-"+(u.username or str(u.telegram_id))[:18]
    if (await db.execute(select(Guild).where(Guild.name==name))).scalar_one_or_none(): raise HTTPException(400,"Гильдия уже существует")
    g=Guild(name=name,owner=u.telegram_id); db.add(g); await db.flush(); db.add(GuildMember(guild_id=g.id,telegram_id=u.telegram_id,role="owner")); await db.commit()
    return {"ok":True,"guild_id":g.id,"name":g.name}

@app.get("/api/guilds")
async def guilds(db=Depends(get_db)):
    gs=(await db.execute(select(Guild).order_by(desc(Guild.xp)).limit(50))).scalars().all()
    return {"guilds":[{"id":g.id,"name":g.name,"level":g.level,"xp":g.xp,"vault":g.vault} for g in gs]}

@app.post("/api/gifts/{receiver_id}/{inventory_id}")
async def gift(receiver_id:int,inventory_id:int,tu=Depends(telegram_user),db=Depends(get_db)):
    u=await current(db,tu); inv=await db.get(Inventory,inventory_id)
    if not inv or inv.telegram_id!=u.telegram_id or inv.sold or inv.locked: raise HTTPException(400,"Предмет недоступен")
    receiver=await db.scalar(select(User).where(User.telegram_id==receiver_id))
    if not receiver: raise HTTPException(404,"Получатель не найден")
    inv.sold=True; db.add(Gift(sender=u.telegram_id,receiver=receiver_id,inventory_id=inventory_id)); await db.commit()
    return {"ok":True}

@app.get("/api/stars/products")
async def stars_products():
    return {"products":[{"id":"premium7","stars":100},{"id":"premium30","stars":300},{"id":"profile_neon","stars":25},{"id":"energy","stars":15}]}

@app.get("/api/admin/stats")
async def admin_stats(db=Depends(get_db)):
    users=await db.scalar(select(func.count(User.id))); inv=await db.scalar(select(func.count(Inventory.id)).where(Inventory.sold==False))
    coins=await db.scalar(select(func.coalesce(func.sum(User.coins),0))); cases=await db.scalar(select(func.count(Transaction.id)).where(Transaction.kind=="case_open"))
    return {"users":users,"inventory":inv,"coins":coins,"cases_opened":cases}
