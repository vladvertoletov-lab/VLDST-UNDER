"""PostgreSQL concurrency/load QA.

Run:
  E2E_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vldst_e2e \
  pytest -q tests/test_concurrency_postgres.py

The suite uses real concurrent DB transactions. It intentionally skips when
PostgreSQL/asyncpg is unavailable rather than substituting SQLite.
"""
import os, sys, asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
URL=os.getenv("E2E_DATABASE_URL") or os.getenv("DATABASE_URL")
if not URL or "postgresql" not in URL:
    pytest.skip("Set E2E_DATABASE_URL to PostgreSQL", allow_module_level=True)
try:
    import asyncpg  # noqa
except ImportError:
    pytest.skip("asyncpg is required", allow_module_level=True)

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db import Base
from app.models import User, Balance, Case, Item, Inventory, Guild, GuildMember, MarketListing, MarketTransaction, StarsProduct, StarsPurchase
from app.services.cases import open_case
from app.services.economy import get_balance
from app.services.payments import grant_stars_entitlement

@pytest.fixture(scope="session")
def engine(): return create_async_engine(URL, pool_size=30, max_overflow=30, pool_pre_ping=True)
@pytest.fixture(scope="session")
def sf(engine): return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def mkuser(sf, tid, vld=0):
    async with sf() as db:
        u=User(telegram_id=tid,username=f"qa{tid}",nickname=f"QA{tid}",referral_code=f"ref{tid}")
        db.add(u); await db.flush(); db.add(Balance(user_id=u.id,vld=vld,season_xp=0)); await db.commit(); return u.id

@pytest.mark.asyncio
async def test_parallel_case_opens_serialize_balance(sf):
    uid=await mkuser(sf,910001,1000)
    async with sf() as db:
        it=Item(name="LOAD COMMON",description="x",rarity="COMMON",collection="LOAD",base_value=10,max_level=10,image="x",recycle_value=1)
        c=Case(name="LOAD CASE",description="x",price=100,weights={"COMMON":1},active=True)
        db.add_all([it,c]); await db.commit(); cid=c.id
    async def one(i):
        async with sf() as db:
            try:
                r=await open_case(db,uid,cid,f"load-case-{i}"); await db.commit(); return ("ok",r)
            except Exception as e: await db.rollback(); return ("err",type(e).__name__,str(e))
    results=await asyncio.gather(*[one(i) for i in range(20)])
    ok=sum(x[0]=="ok" for x in results); assert ok==10
    async with sf() as db:
        b=await get_balance(db,uid); assert b.vld==0
        inv=(await db.execute(select(func.count(Inventory.id)).where(Inventory.user_id==uid))).scalar(); assert inv==10

@pytest.mark.asyncio
async def test_parallel_market_buy_single_winner(sf):
    seller=await mkuser(sf,910002,0); buyer1=await mkuser(sf,910003,1000); buyer2=await mkuser(sf,910004,1000)
    async with sf() as db:
        it=Item(name="MARKET ITEM",description="x",rarity="RARE",collection="LOAD",base_value=100,max_level=10,image="x",recycle_value=10); db.add(it); await db.flush()
        inv=Inventory(user_id=seller,item_id=it.id); db.add(inv); await db.flush(); l=MarketListing(seller_id=seller,inventory_id=inv.id,price=500,active=True);db.add(l);await db.commit(); lid=l.id
    from app.main import market_buy
    from starlette.requests import Request
    async def one(uid,key):
        async with sf() as db:
            # invoke endpoint logic with a minimal Request carrying idempotency header
            scope={"type":"http","method":"POST","path":f"/api/market/{lid}/buy","headers":[(b"idempotency-key",key.encode())]}
            req=Request(scope)
            try:return await market_buy(lid,req,uid,db)
            except Exception as e: await db.rollback(); return type(e).__name__
    r=await asyncio.gather(one(buyer1,"m1"),one(buyer2,"m2")); assert sum(isinstance(x,dict) and x.get("ok") for x in r)==1
    async with sf() as db:
        l=await db.get(MarketListing,lid); assert l.active is False
        mt=(await db.execute(select(func.count(MarketTransaction.id)).where(MarketTransaction.listing_id==lid))).scalar(); assert mt==1
        inv=(await db.get(Inventory,l.id if False else (await db.get(MarketListing,lid)).inventory_id)); assert inv.user_id in (buyer1,buyer2)

@pytest.mark.asyncio
async def test_parallel_guild_joins_respect_capacity(sf):
    owner=await mkuser(sf,910005,0); users=[await mkuser(sf,910010+i,0) for i in range(10)]
    async with sf() as db:
        g=Guild(name="LOAD GUILD",tag="LDG",created_by=owner,max_members=3);db.add(g);await db.flush();db.add(GuildMember(guild_id=g.id,user_id=owner,role="owner"));await db.commit();gid=g.id
    from app.main import guild_join, GuildJoinIn
    async def one(uid):
        async with sf() as db:
            try:r=await guild_join(GuildJoinIn(guild_id=gid),uid,db);return True
            except Exception: await db.rollback();return False
    results=await asyncio.gather(*[one(u) for u in users]); assert sum(results)==2
    async with sf() as db:
        n=(await db.execute(select(func.count(GuildMember.id)).where(GuildMember.guild_id==gid))).scalar();assert n==3

@pytest.mark.asyncio
async def test_duplicate_payment_callbacks_grant_once(sf):
    uid=await mkuser(sf,910100,0)
    async with sf() as db:
        p=StarsProduct(code="LOAD_COS",name="Load Cosmetic",description="x",stars_price=49,image="x",category="FRAMES",active=True);db.add(p);await db.flush()
        sp=StarsPurchase(user_id=uid,product_id=p.id,payload="load-payload",status="pending");db.add(sp);await db.commit();pid=sp.id
    async def one():
        async with sf() as db:
            row=(await db.execute(select(StarsPurchase).where(StarsPurchase.id==pid).with_for_update())).scalar_one(); product=await db.get(StarsProduct,row.product_id)
            try: changed=await grant_stars_entitlement(db,row,product,"load-charge");await db.commit();return changed
            except Exception: await db.rollback();return False
    r=await asyncio.gather(*[one() for _ in range(25)]); assert sum(r)==1
    async with sf() as db:
        row=await db.get(StarsPurchase,pid); assert row.status=="paid" and row.telegram_charge_id=="load-charge"
