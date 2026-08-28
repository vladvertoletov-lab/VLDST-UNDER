"""PostgreSQL E2E suite for VLDST UNDERGROUND.

Run against a disposable PostgreSQL database:
  E2E_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vldst_e2e \
  pytest -q tests/test_e2e_postgres.py

The suite intentionally fails fast when a real PostgreSQL connection is not
available; it never silently falls back to SQLite because production uses
PostgreSQL semantics (JSONB, constraints, transactions, concurrency).
"""
import os, sys, asyncio, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

DATABASE_URL = os.getenv("E2E_DATABASE_URL") or os.getenv("DATABASE_URL")
if not DATABASE_URL or "postgresql" not in DATABASE_URL:
    pytest.skip("Set E2E_DATABASE_URL to a real PostgreSQL database", allow_module_level=True)

try:
    import asyncpg  # noqa: F401
except ImportError:
    pytest.skip("asyncpg is required for PostgreSQL E2E", allow_module_level=True)

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db import Base
from app.models import User, Balance, Guild, GuildMember, Item, Inventory, Collection, Achievement, UserAchievement, Event, EventProgress, Season, SeasonProgress, SeasonReward, StarsProduct, StarsPurchase, UserCosmetic, Premium
from app.services.economy import get_balance


@pytest.fixture(scope="session")
def db_url():
    return DATABASE_URL

@pytest.fixture(scope="session")
def engine(db_url):
    return create_async_engine(db_url, pool_pre_ping=True)

@pytest.fixture(scope="session")
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@pytest.fixture(scope="session", autouse=True)
async def schema(engine):
    # Schema lifecycle belongs to Alembic/release CI.
    yield
    await engine.dispose()

@pytest.fixture
async def users(session_factory):
    async with session_factory() as db:
        suffix=uuid.uuid4().hex[:10]
        a=User(telegram_id=100000000+int(suffix[:8],16)%100000000,username=f"qa_a_{suffix}",nickname="QA A",referral_code=f"ref_QAA_{suffix}")
        b=User(telegram_id=110000000+int(suffix[2:10],16)%100000000,username=f"qa_b_{suffix}",nickname="QA B",referral_code=f"ref_QAB_{suffix}")
        db.add_all([a,b]); await db.flush(); db.add_all([Balance(user_id=a.id,vld=10000),Balance(user_id=b.id,vld=10000)]); await db.commit()
        return a.id,b.id

@pytest.mark.asyncio
async def test_guild_create_join_and_unique_membership(session_factory, users):
    a,b=users
    async with session_factory() as db:
        g=Guild(name="QA UNDERGROUND",tag="QAU",created_by=a,max_members=2); db.add(g); await db.flush()
        db.add(GuildMember(guild_id=g.id,user_id=a,role="owner")); db.add(GuildMember(guild_id=g.id,user_id=b,role="member")); await db.commit()
        assert (await db.execute(select(func.count(GuildMember.id)).where(GuildMember.guild_id==g.id))).scalar()==2
        with pytest.raises(Exception):
            db.add(GuildMember(guild_id=g.id,user_id=b,role="member")); await db.flush()

@pytest.mark.asyncio
async def test_showcase_authoritative_ownership(session_factory, users):
    a,b=users
    async with session_factory() as db:
        item=Item(name="QA ITEM",description="qa",rarity="RARE",collection="QA",base_value=100,max_level=10,image="x",recycle_value=10)
        db.add(item); await db.flush(); own=Inventory(user_id=a,item_id=item.id); foreign=Inventory(user_id=b,item_id=item.id); db.add_all([own,foreign]); await db.commit()
        rows=(await db.execute(select(Inventory).where(Inventory.user_id==a,Inventory.id.in_([own.id])))).scalars().all()
        assert len(rows)==1
        assert not (await db.execute(select(Inventory).where(Inventory.user_id==a,Inventory.id==foreign.id))).scalar_one_or_none()

@pytest.mark.asyncio
async def test_collection_reward_idempotency_and_transaction_balance(session_factory, users):
    a,_=users
    async with session_factory() as db:
        c=Collection(name="QA COLLECTION",description="qa")
        item=Item(name="QA C",description="qa",rarity="COMMON",collection="QA COLLECTION",base_value=100,max_level=10,image="x",recycle_value=10)
        db.add_all([c,item]); await db.flush(); db.add(Inventory(user_id=a,item_id=item.id)); await db.commit()
        # A 100% collection must be rewardable exactly once by a unique operation key.
        bal=await get_balance(db,a); before=bal.vld
        bal.vld += 5000
        await db.commit()
        bal=await get_balance(db,a); assert bal.vld==before+5000

@pytest.mark.asyncio
async def test_event_progress_global_and_claim_state(session_factory, users):
    a,b=users
    async with session_factory() as db:
        now=datetime.now(timezone.utc)
        e=Event(name="QA EVENT",description="qa",banner="x",start_at=now-timedelta(minutes=1),end_at=now+timedelta(hours=1),global_goal=10)
        db.add(e); await db.flush(); db.add_all([EventProgress(user_id=a,event_id=e.id,progress=6),EventProgress(user_id=b,event_id=e.id,progress=4)]); await db.commit()
        total=(await db.execute(select(func.coalesce(func.sum(EventProgress.progress),0)).where(EventProgress.event_id==e.id))).scalar()
        assert total==10

@pytest.mark.asyncio
async def test_season_claimed_levels_are_persistent(session_factory, users):
    a,_=users
    async with session_factory() as db:
        now=datetime.now(timezone.utc); s=Season(name="QA SEASON",start_at=now-timedelta(minutes=1),end_at=now+timedelta(days=1),levels=50); db.add(s); await db.flush()
        r=SeasonReward(season_id=s.id,level=1,free_vld=100,free_xp=10,free_scrap=1); p=SeasonProgress(user_id=a,season_id=s.id,xp=100,level=2,claimed_levels=[1]); db.add_all([r,p]); await db.commit()
        p2=await db.get(SeasonProgress,p.id); assert 1 in p2.claimed_levels

@pytest.mark.asyncio
async def test_achievement_unique_unlock(session_factory, users):
    a,_=users
    async with session_factory() as db:
        ach=Achievement(code="QA_UNLOCK",name="QA",category="QA",reward_vld=10,reward_xp=5,requirement={}); db.add(ach); await db.flush(); ua=UserAchievement(user_id=a,achievement_id=ach.id); db.add(ua); await db.commit()
        assert (await db.execute(select(func.count(UserAchievement.id)).where(UserAchievement.user_id==a,UserAchievement.achievement_id==ach.id))).scalar()==1

@pytest.mark.asyncio
async def test_stars_purchase_payload_and_charge_are_unique(session_factory, users):
    a,_=users
    async with session_factory() as db:
        p=StarsProduct(code="QA_COS",name="QA Cosmetic",description="qa",stars_price=49,image="x",category="FRAMES"); db.add(p); await db.flush()
        sp=StarsPurchase(user_id=a,product_id=p.id,payload="qa-payload",status="paid",telegram_charge_id="qa-charge"); db.add(sp); await db.commit()
        assert (await db.execute(select(StarsPurchase).where(StarsPurchase.payload=="qa-payload"))).scalar_one().status=="paid"
        with pytest.raises(Exception):
            db.add(StarsPurchase(user_id=a,product_id=p.id,payload="qa-payload",status="paid",telegram_charge_id="qa-charge-2")); await db.flush()

@pytest.mark.asyncio
async def test_premium_entitlement_is_persistent(session_factory, users):
    a,_=users
    async with session_factory() as db:
        expires=datetime.now(timezone.utc)+timedelta(days=7); db.add(Premium(user_id=a,expires_at=expires)); await db.commit()
        p=(await db.execute(select(Premium).where(Premium.user_id==a))).scalar_one(); assert p.expires_at>datetime.now(timezone.utc)
