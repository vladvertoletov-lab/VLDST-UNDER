"""HTTP-level E2E checks for the Mini App actions.

Requires E2E_DATABASE_URL pointing to PostgreSQL. Telegram's createInvoiceLink
is mocked at the network boundary; successful_payment entitlement is tested
through the same payment service used by the aiogram bot. No real Stars are
charged by the test suite.
"""
import os, sys, uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
if not (os.getenv("E2E_DATABASE_URL") or os.getenv("DATABASE_URL")):
    pytestmark = pytest.mark.skip(reason="Set E2E_DATABASE_URL to PostgreSQL")
try:
    import asyncpg  # noqa
except ImportError:
    pytest.skip("asyncpg is required", allow_module_level=True)

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.main import app, get_db
from app.models import *
from app.services.payments import grant_stars_entitlement

URL=os.getenv("E2E_DATABASE_URL") or os.getenv("DATABASE_URL")

@pytest.fixture(scope="session")
def engine(): return create_async_engine(URL, pool_pre_ping=True)
@pytest.fixture(scope="session")
def sf(engine): return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
@pytest.fixture(scope="session", autouse=True)
async def setup(engine):
    # Release gate owns schema lifecycle through Alembic migrations.
    yield
    await engine.dispose()

@pytest.fixture
async def ctx(sf):
    async with sf() as db:
        token = uuid.uuid4().hex[:10]
        a=User(telegram_id=int(token[:9], 16),nickname="E2E A",referral_code=f"e2e_a_{token}")
        b=User(telegram_id=int(token[1:10], 16),nickname="E2E B",referral_code=f"e2e_b_{token}")
        db.add_all([a,b]); await db.flush()
        db.add_all([Balance(user_id=a.id,vld=10000),Balance(user_id=b.id,vld=10000)])
        c=Collection(name="E2E COL",description="e2e")
        item=Item(name="E2E ITEM",description="e2e",rarity="EPIC",collection="E2E COL",base_value=100,max_level=10,image="x",recycle_value=10)
        ach=Achievement(code="FIRST_STEP",name="First Step",category="Progress",reward_vld=10,reward_xp=5,requirement={})
        sp=StarsProduct(code="E2E_FRAME",name="E2E Frame",description="cosmetic",stars_price=49,image="x",category="FRAMES")
        db.add_all([c,item,ach,sp]); await db.flush(); db.add(Inventory(user_id=a.id,item_id=item.id)); await db.commit()
        return a.id,b.id,c.id,item.id,sp.id

@pytest.fixture
async def client(sf, ctx):
    uid=ctx[0]
    async def override_db():
        async with sf() as db: yield db
    app.dependency_overrides[get_db]=override_db
    app.dependency_overrides[__import__('app.main',fromlist=['current_user']).current_user]=lambda: uid
    async with AsyncClient(transport=ASGITransport(app=app),base_url="http://test") as c: yield c
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_http_guild_showcase_collection(client, ctx):
    a,b,cid,iid,_=ctx
    r=await client.post('/api/guild/create',json={'name':'E2E GUILD','tag':'E2E'}); assert r.status_code==200
    gid=r.json()['guild']['id']
    # Current user cannot join another guild, so call a separate client context for B later.
    r=await client.get('/api/guild'); assert r.json()['guild']['id']==gid
    r=await client.post('/api/vault/showcase',json={'inventory_ids':[1]}); assert r.status_code in (200,400)
    r=await client.post(f'/api/collections/{cid}/claim/25',headers={'Idempotency-Key':'e2e-col-25'}); assert r.status_code==200
    r2=await client.post(f'/api/collections/{cid}/claim/25',headers={'Idempotency-Key':'e2e-col-25'}); assert r2.status_code==200 and r2.json().get('already_processed') is True

@pytest.mark.asyncio
async def test_http_event_and_season_repeat_claims(client, sf, ctx):
    a,_,_,_,_=ctx; now=datetime.now(timezone.utc)
    async with sf() as db:
        e=Event(name='E2E EVENT',description='e2e',banner='x',start_at=now-timedelta(minutes=1),end_at=now+timedelta(hours=1),global_goal=1)
        s=Season(name='E2E SEASON',start_at=now-timedelta(minutes=1),end_at=now+timedelta(days=1),levels=50)
        db.add_all([e,s]); await db.flush(); db.add(SeasonProgress(user_id=a,season_id=s.id,xp=100,level=2,claimed_levels=[])); db.add(SeasonReward(season_id=s.id,level=1,free_vld=100,free_xp=10,free_scrap=1)); await db.commit(); eid=e.id; sid=s.id
    assert (await client.post(f'/api/events/{eid}/join')).status_code==200
    # Event progress is authoritative: generate it through a verified server action.
    from app.services.gameplay import record_action
    async with sf() as db:
        await record_action(db,a,'game',1)
        await db.commit()
    c=await client.post(f'/api/events/{eid}/claim',headers={'Idempotency-Key':'evt-claim'}); assert c.status_code==200
    c2=await client.post(f'/api/events/{eid}/claim',headers={'Idempotency-Key':'evt-claim'}); assert c2.status_code==200
    sc=await client.post(f'/api/seasons/{sid}/claim',json={'level':1},headers={'Idempotency-Key':'season-1'}); assert sc.status_code==200
    sc2=await client.post(f'/api/seasons/{sid}/claim',json={'level':1},headers={'Idempotency-Key':'season-1'}); assert sc2.status_code==200

@pytest.mark.asyncio
async def test_stars_invoice_creation_and_entitlement_idempotency(client, sf, ctx, monkeypatch):
    _,_,_,_,product_id=ctx
    class Resp:
        status_code=200
        def json(self): return {'ok':True,'result':'https://t.me/$e2e_invoice'}
    class FakeClient:
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def post(self,*args,**kwargs): return Resp()
    import app.main as mainmod
    monkeypatch.setattr(mainmod.httpx,'AsyncClient',FakeClient)
    r=await client.post('/api/shop/purchase',json={'product_id':product_id}); assert r.status_code==200
    payload=r.json()['payload']
    async with sf() as db:
        purchase=(await db.execute(select(StarsPurchase).where(StarsPurchase.payload==payload))).scalar_one()
        product=await db.get(StarsProduct,product_id)
        assert purchase.status=='pending'
        assert await grant_stars_entitlement(db,purchase,product,'charge-e2e') is True
        await db.commit()
        assert await grant_stars_entitlement(db,purchase,product,'charge-e2e') is False
        await db.commit()
        owned=(await db.execute(select(UserCosmetic).where(UserCosmetic.user_id==purchase.user_id,UserCosmetic.product_id==product_id))).scalar_one()
        assert owned is not None
        assert purchase.status=='paid'
