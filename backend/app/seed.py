import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from .db import engine, Base, SessionLocal
from .models import *
from .services.economy import get_balance

CASES=[
("STARTER",100),("STREET",500),("NEON",1500),("CYBER",3000),("DIGITAL",5000),
("SHADOW",8000),("GOLD",12000),("PHANTOM",18000),("VOID",25000),("RIFT",35000),
("QUANTUM",50000),("OMEGA",75000),("INFERNO",100000),("FROZEN",125000),("GALAXY",175000),
("ULTRA",250000),("BLACK",350000),("RADIANT",500000),("UNDERGROUND",750000),("VLDST OMEGA",1000000)]
COL=["NEON CITY","CYBER LAB","VOID","DIGITAL DREAM","SHADOW","GOLDEN AGE","PHANTOM","RIFT","QUANTUM","OMEGA","INFERNO","FROZEN","GALAXY","UNDERGROUND","ANCIENT","TECHNO","SYNTH","NIGHT","RADIANT","VLDST ORIGINAL"]
RARITIES=["COMMON"]*75+["RARE"]*60+["EPIC"]*45+["LEGENDARY"]*35+["MYTHIC"]*20+["SECRET"]*5
GAMES=["REACTION","MEMORY","AIM","DECRYPT","PUZZLE","DODGE","OBSERVER","TOWER","NUMBER RUSH","SIGNAL HUNT"]

async def main():
    async with SessionLocal() as db:
        if not (await db.execute(select(Case))).scalars().first():
            weights={"COMMON":.55,"RARE":.28,"EPIC":.12,"LEGENDARY":.04,"MYTHIC":.009,"SECRET":.001}
            for i,(name,price) in enumerate(CASES,1):
                db.add(Case(name=name,description=f"{name} underground capsule",price=price,image=f"/assets/cases/{name.lower().replace(' ','_')}.svg",weights=weights))
        if not (await db.execute(select(Item))).scalars().first():
            for i,r in enumerate(RARITIES,1):
                col=COL[(i-1)%len(COL)]
                db.add(Item(name=f"{col} Artifact {i:03d}",description=f"Unique {r.lower()} artifact from {col}.",rarity=r,collection=col,base_value=100*i,max_level=10,image=f"/assets/items/item_{i:03d}.svg",animation="glow" if r in {"MYTHIC","SECRET"} else "none",effect="collection",recycle_value=max(10,25*i)))
        if not (await db.execute(select(Collection))).scalars().first():
            for c in COL: db.add(Collection(name=c,description=f"{c} collection"))
        # Explicit item mappings for cases and collections.
        if not (await db.execute(select(CaseItem))).scalars().first():
            cases=(await db.execute(select(Case).order_by(Case.id))).scalars().all(); items=(await db.execute(select(Item).order_by(Item.id))).scalars().all()
            for c in cases:
                for it in items:
                    if it.rarity in c.weights: db.add(CaseItem(case_id=c.id,item_id=it.id,weight=max(0.0001,float(c.weights.get(it.rarity,0)))))
        if not (await db.execute(select(CollectionItem))).scalars().first():
            cols=(await db.execute(select(Collection).order_by(Collection.id))).scalars().all(); items=(await db.execute(select(Item).order_by(Item.id))).scalars().all()
            by={c.name:c.id for c in cols}
            for it in items:
                if it.collection in by: db.add(CollectionItem(collection_id=by[it.collection],item_id=it.id))
        if not (await db.execute(select(Vault))).scalars().first():
            users=(await db.execute(select(User))).scalars().all()
            for u in users: db.add(Vault(user_id=u.id,level=1,slots=50))

        if not (await db.execute(select(Achievement))).scalars().first():
            core=[
                ("FIRST_STEP","FIRST STEP","Progress",0,25,{"kind":"always","target":0},"NEWCOMER"),
                ("FIRST_CASE","FIRST CASE","Cases",100,25,{"kind":"cases","target":1},"HUNTER"),
                ("FIRST_EPIC","FIRST EPIC","Cases",250,50,{"kind":"cases","target":5},None),
                ("FIRST_LEGENDARY","FIRST LEGENDARY","Cases",500,100,{"kind":"cases","target":25},"LEGEND"),
                ("FIRST_MYTHIC","FIRST MYTHIC","Cases",1000,250,{"kind":"cases","target":100},"MYTHIC SEEKER"),
                ("COLLECTOR","COLLECTOR","Collections",1000,100,{"kind":"items","target":20},"COLLECTOR"),
                ("100_GAMES","100 GAMES","Games",1000,250,{"kind":"games","target":100},None),
                ("500_GAMES","500 GAMES","Games",2500,500,{"kind":"games","target":500},None),
                ("1000_GAMES","1000 GAMES","Games",5000,1000,{"kind":"games","target":1000},"UNDERGROUND MASTER"),
                ("QUEST_MASTER","QUEST MASTER","Progress",1500,300,{"kind":"quests","target":50},"EXPLORER"),
            ]
            for row in core: db.add(Achievement(code=row[0],name=row[1],category=row[2],reward_vld=row[3],reward_xp=row[4],requirement=row[5],title_reward=row[6]))
            for i in range(10,101):
                kind=["games","cases","items","quests","trades"][i%5]; target=max(1,i*5)
                db.add(Achievement(code=f"ACH_{i:03d}",name=f"UNDERGROUND MILESTONE #{i}",category=["Progress","Games","Cases","Collections","Craft","Social","Guild","Events","Secrets","Season"][i%10],reward_vld=100*i,reward_xp=25*i,requirement={"kind":kind,"target":target},title_reward=("UNDERGROUND MASTER" if i==100 else None)))
        if not (await db.execute(select(Quest))).scalars().first():
            actions=["game","case","craft","fusion","recycle","quest_claim","daily","trade","collection","event"]
            for i in range(1,13):
                db.add(Quest(title=f"Daily Mission {i}",description=f"Complete {actions[(i-1)%len(actions)]} activity {i} times.",category="daily",quest_type=actions[(i-1)%len(actions)],target=max(1,i),reward_vld=100*i,reward_xp=20*i,period="daily"))
            for i in range(1,21):
                db.add(Quest(title=f"Weekly Mission {i}",description=f"Weekly {actions[i%len(actions)]} objective.",category="weekly",quest_type=actions[i%len(actions)],target=i*2,reward_vld=500*i,reward_xp=50*i,period="weekly"))
        if not (await db.execute(select(Game))).scalars().first():
            for g in GAMES: db.add(Game(code=g.lower().replace(" ","_"),name=g,energy_cost=1))
        if not (await db.execute(select(StarsProduct))).scalars().first():
            cats=["THEMES","FRAMES","BACKGROUNDS","EFFECTS","ANIMATIONS","BADGES"]
            prices=[49,79,99,149,199,299]
            for i in range(1,31):
                db.add(StarsProduct(code=f"COSMETIC_{i:02d}",name=f"Underground Cosmetic {i:02d}",description="Premium cosmetic item; no gameplay advantage.",stars_price=prices[(i-1)%6],image=f"/assets/cosmetics/cosmetic_{i:02d}.svg",category=cats[(i-1)%6]))
            if not (await db.execute(select(StarsProduct).where(StarsProduct.code=="PREMIUM_7"))).scalar_one_or_none(): db.add(StarsProduct(code="PREMIUM_7",name="VLDST Premium · 7 Days",description="Premium profile and cosmetic features for 7 days.",stars_price=50,image="/assets/cosmetics/cosmetic_01.svg",category="PREMIUM"))
            if not (await db.execute(select(StarsProduct).where(StarsProduct.code=="PREMIUM_30"))).scalar_one_or_none(): db.add(StarsProduct(code="PREMIUM_30",name="VLDST Premium · 30 Days",description="Premium profile and cosmetic features for 30 days.",stars_price=150,image="/assets/cosmetics/cosmetic_02.svg",category="PREMIUM"))
            if not (await db.execute(select(StarsProduct).where(StarsProduct.code=="SEASON_PASS_01"))).scalar_one_or_none(): db.add(StarsProduct(code="SEASON_PASS_01",name="Season 01 Premium Pass",description="Unlocks the cosmetic premium season reward track.",stars_price=299,image="/assets/cosmetics/cosmetic_03.svg",category="SEASON_PASS"))
        # Repair special products even when the database was seeded by an older build.
        specials={
            "PREMIUM_7": ("VLDST Premium · 7 Days",50,"PREMIUM","/assets/cosmetics/cosmetic_01.svg"),
            "PREMIUM_30": ("VLDST Premium · 30 Days",150,"PREMIUM","/assets/cosmetics/cosmetic_02.svg"),
            "SEASON_PASS_01": ("Season 01 Premium Pass",299,"SEASON_PASS","/assets/cosmetics/cosmetic_03.svg"),
        }
        for code,(name,price,category,image) in specials.items():
            if not await db.scalar(select(StarsProduct.id).where(StarsProduct.code==code)):
                db.add(StarsProduct(code=code,name=name,description="Digital cosmetic/premium product; no gameplay advantage.",stars_price=price,image=image,category=category));
        await db.flush()
        premium_cosmetics=(await db.execute(select(StarsProduct).where(StarsProduct.category.in_(["THEMES","FRAMES","BACKGROUNDS","EFFECTS","ANIMATIONS","BADGES"])).order_by(StarsProduct.id).limit(10))).scalars().all()

        season=(await db.execute(select(Season).order_by(Season.id.desc()))).scalars().first()
        if not season:
            now=datetime.now(timezone.utc)
            season=Season(name="SEASON 01: NEON UNDERGROUND",start_at=now,end_at=now+timedelta(days=30),levels=50); db.add(season); await db.flush()
        for level in range(1,season.levels+1):
            if not (await db.execute(select(SeasonReward).where(SeasonReward.season_id==season.id,SeasonReward.level==level))).scalar_one_or_none():
                db.add(SeasonReward(season_id=season.id,level=level,free_vld=100+level*25,free_xp=10+level*5,free_scrap=2 if level%10==0 else 0,premium_product_id=(premium_cosmetics[(level//5-1)%len(premium_cosmetics)].id if level%5==0 and premium_cosmetics else None)))
        if not (await db.execute(select(Event))).scalars().first():
            now=datetime.now(timezone.utc)
            actions=["game","game","recycle","recycle","collection","game","game","case","craft"]
            for idx,name in enumerate(["VOID NIGHT","NEON WEEK","DOUBLE XP","SCRAP RUSH","COLLECTION WEEK","GAME FEST","GUILD RACE","SECRET SIGNAL","UNDERGROUND EVENT"]):
                db.add(Event(name=name,description=f"{name} limited event",banner=f"/assets/ui/{name.lower().replace(' ','_')}.svg",start_at=now,end_at=now+timedelta(days=7),global_goal=100000,action_type=actions[idx],reward_vld=1000+idx*250,reward_xp=100+idx*20))
        if not (await db.execute(select(CraftRecipe))).scalars().first():
            items=(await db.execute(select(Item).order_by(Item.id))).scalars().all()
            for i in range(30):
                db.add(CraftRecipe(name=f"Recipe {i+1:02d}",output_item_id=items[min(len(items)-1,120+i)].id,requirements={"items":2},vld_cost=250*(i+1),scrap_cost=50*(i+1),core_cost=0 if i<20 else 1,min_level=1+i//5))
        if not (await db.execute(select(PromoCode))).scalars().first():
            db.add(PromoCode(code="VLDST2026",reward_vld=2500,reward_xp=100,max_uses=1000))
        if not (await db.execute(select(EconomyConfig))).scalars().first():
            cfg={"daily_reward":500,"energy_max":100,"energy_regen_minutes":5,"market_fee_percent":5,"xp_multiplier":1,"game_reward":100}
            for k,v in cfg.items(): db.add(EconomyConfig(key=k,value=v))
        await db.commit()
    await engine.dispose()

if __name__=="__main__": asyncio.run(main())
