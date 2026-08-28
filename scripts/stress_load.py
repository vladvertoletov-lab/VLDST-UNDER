#!/usr/bin/env python3
"""VLDST PostgreSQL stress/concurrency benchmark.

Requires a real PostgreSQL database. It intentionally refuses SQLite.
Measures p50/p95/p99/max latency, throughput, errors, lock waits and deadlocks.

Examples:
  E2E_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vldst_e2e \
    python scripts/stress_load.py --concurrency 100 250 500 1000

  ... --workload all --json-out artifacts/load.json --report-out artifacts/load.md
"""
from __future__ import annotations
import argparse, asyncio, json, os, statistics, sys, time, uuid
import asyncpg
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

URL = os.getenv("E2E_DATABASE_URL") or os.getenv("DATABASE_URL")

sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.requests import Request
from fastapi import HTTPException
from app.models import (
    User, Balance, Case, Item, Inventory, Guild, GuildMember,
    MarketListing, MarketTransaction, StarsProduct, StarsPurchase,
)
from app.services.cases import open_case
from app.services.payments import grant_stars_entitlement
from app.main import GuildJoinIn, guild_join, market_buy

@dataclass
class Sample:
    workload: str
    concurrency: int
    operation: str
    ok: int
    expected_conflict: int
    errors: int
    elapsed_s: float
    throughput_ops_s: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    lock_wait_samples: int
    lock_wait_max: int
    deadlocks_delta: int

class LockMonitor:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.stop = asyncio.Event()
        self.samples: list[int] = []
        self.task: asyncio.Task | None = None
    async def start(self):
        self.task = asyncio.create_task(self._run())
    async def _run(self):
        conn = await asyncpg.connect(self.dsn.replace("+asyncpg", ""))
        try:
            while not self.stop.is_set():
                n = await conn.fetchval("""
                    SELECT count(*) FROM pg_stat_activity
                    WHERE wait_event_type = 'Lock' AND pid <> pg_backend_pid()
                """)
                self.samples.append(int(n or 0))
                await asyncio.sleep(0.05)
        finally:
            await conn.close()
    async def stop_and_read(self):
        self.stop.set()
        if self.task:
            await self.task
        return len(self.samples), max(self.samples or [0])

async def db_deadlocks(dsn: str) -> int:
    conn = await asyncpg.connect(dsn.replace("+asyncpg", ""))
    try:
        return int(await conn.fetchval("SELECT COALESCE(sum(deadlocks),0) FROM pg_stat_database"))
    finally:
        await conn.close()

async def scalar(sf, stmt):
    async with sf() as db:
        return (await db.execute(stmt)).scalar()

async def create_user(sf, seed: int, vld: int = 0) -> int:
    async with sf() as db:
        u = User(telegram_id=seed, username=f"load{seed}", nickname=f"LOAD{seed}", referral_code=f"load_{seed}_{uuid.uuid4().hex[:8]}")
        db.add(u); await db.flush()
        db.add(Balance(user_id=u.id, vld=vld, season_xp=0)); await db.commit()
        return u.id

async def setup_case(sf, n: int):
    suffix = uuid.uuid4().hex[:8]
    uid = await create_user(sf, 700000000 + int(suffix,16) % 100000000, 100*n)
    async with sf() as db:
        item = Item(name=f"LOAD-{suffix}", description="stress", rarity="COMMON", collection="LOAD", base_value=10, max_level=10, image="x", recycle_value=1)
        case = Case(name=f"LOAD-CASE-{suffix}", description="stress", price=100, image="x", weights={"COMMON":1}, active=True)
        db.add_all([item,case]); await db.commit(); return uid, case.id

async def setup_guild(sf, n: int):
    owner = await create_user(sf, 710000000 + int(uuid.uuid4().hex[:8],16) % 100000000)
    users = [await create_user(sf, 720000000 + int(uuid.uuid4().hex[:8],16) % 100000000) for _ in range(n)]
    async with sf() as db:
        g=Guild(name=f"LOAD-G-{uuid.uuid4().hex[:8]}",tag=f"L{uuid.uuid4().hex[:6]}"[:12],created_by=owner,max_members=20)
        db.add(g); await db.flush(); db.add(GuildMember(guild_id=g.id,user_id=owner,role="owner")); await db.commit(); return g.id, users

async def setup_market(sf, n: int):
    seller = await create_user(sf, int(uuid.uuid4().hex[:15],16), 0)
    buyers=[]
    async with sf() as db:
        item=Item(name=f"MARKET-{uuid.uuid4().hex[:8]}",description="stress",rarity="RARE",collection="LOAD",base_value=100,max_level=10,image="x",recycle_value=10)
        db.add(item); await db.flush()
        listings=[]
        for i in range(n):
            inv=Inventory(user_id=seller,item_id=item.id); db.add(inv); await db.flush()
            listings.append(MarketListing(seller_id=seller,inventory_id=inv.id,price=100,active=True))
            buyers.append(await create_user(sf, int(uuid.uuid4().hex[:15],16), 100))
        db.add_all(listings); await db.commit()
        return seller, buyers, [x.id for x in listings]

async def setup_hot_market(sf, n):
    seller=await create_user(sf,int(uuid.uuid4().hex[:15],16))
    buyers=[await create_user(sf,int(uuid.uuid4().hex[:15],16),100) for _ in range(n)]
    async with sf() as db:
        item=Item(name=f"HOT-{uuid.uuid4().hex[:8]}",description="stress",rarity="RARE",collection="LOAD",base_value=100,max_level=10,image="x",recycle_value=10);db.add(item);await db.flush()
        inv=Inventory(user_id=seller,item_id=item.id);db.add(inv);await db.flush();l=MarketListing(seller_id=seller,inventory_id=inv.id,price=100,active=True);db.add(l);await db.commit();return buyers,l.id

async def setup_payment(sf):
    uid=await create_user(sf,int(uuid.uuid4().hex[:15],16))
    async with sf() as db:
        p=StarsProduct(code=f"LOAD-{uuid.uuid4().hex[:8]}",name="Load Cosmetic",description="stress",stars_price=49,image="x",category="FRAMES",active=True);db.add(p);await db.flush()
        sp=StarsPurchase(user_id=uid,product_id=p.id,payload=f"load:{uuid.uuid4().hex}",status="pending");db.add(sp);await db.commit();return sp.id,p.id

def percentile(values, q):
    if not values:return 0.0
    xs=sorted(values); k=(len(xs)-1)*q; f=int(k); c=min(f+1,len(xs)-1)
    return xs[f]+(xs[c]-xs[f])*(k-f)

async def run_case(sf,n):
    uid,cid=await setup_case(sf,n)
    async def op(i):
        t=time.perf_counter()
        async with sf() as db:
            try: await open_case(db,uid,cid,f"stress-case-{i}-{uuid.uuid4().hex}"); await db.commit(); return time.perf_counter()-t,"ok"
            except Exception as e: await db.rollback(); return time.perf_counter()-t,"err"
    return await run_ops("case_open",n,op,sf)

async def run_guild(sf,n):
    gid,users=await setup_guild(sf,n)
    async def op(i):
        t=time.perf_counter()
        async with sf() as db:
            try: await guild_join(GuildJoinIn(guild_id=gid),users[i],db); return time.perf_counter()-t,"ok"
            except HTTPException as e: await db.rollback(); return time.perf_counter()-t,"conflict" if e.status_code in (400,409) else "err"
            except Exception: await db.rollback(); return time.perf_counter()-t,"err"
    return await run_ops("guild_join",n,op,sf)

async def run_market(sf,n):
    seller,buyers,lids=await setup_market(sf,n)
    async def op(i):
        t=time.perf_counter();
        async with sf() as db:
            req=Request({"type":"http","method":"POST","path":f"/api/market/{lids[i]}/buy","headers":[(b"idempotency-key",f"stress-mkt-{i}".encode())]})
            try: await market_buy(lids[i],req,buyers[i],db); return time.perf_counter()-t,"ok"
            except HTTPException as e: await db.rollback(); return time.perf_counter()-t,"conflict" if e.status_code in (400,409) else "err"
            except Exception: await db.rollback(); return time.perf_counter()-t,"err"
    return await run_ops("market_purchase_distributed",n,op,sf)

async def run_hot_market(sf,n):
    buyers,lid=await setup_hot_market(sf,n)
    buyers=buyers[:n]
    async def op(i):
        t=time.perf_counter()
        async with sf() as db:
            req=Request({"type":"http","method":"POST","path":f"/api/market/{lid}/buy","headers":[(b"idempotency-key",f"stress-hot-{i}".encode())]})
            try: await market_buy(lid,req,buyers[i],db); return time.perf_counter()-t,"ok"
            except HTTPException as e: await db.rollback(); return time.perf_counter()-t,"conflict" if e.status_code in (400,409) else "err"
            except Exception: await db.rollback(); return time.perf_counter()-t,"err"
    return await run_ops("market_purchase_hot_listing",n,op,sf)

async def run_payment(sf,n):
    pid,product_id=await setup_payment(sf)
    async def op(i):
        t=time.perf_counter()
        async with sf() as db:
            try:
                purchase=(await db.execute(select(StarsPurchase).where(StarsPurchase.id==pid).with_for_update())).scalar_one()
                product=await db.get(StarsProduct,product_id)
                changed=await grant_stars_entitlement(db,purchase,product,"stress-charge")
                await db.commit(); return time.perf_counter()-t,"ok" if changed else "noop"
            except Exception: await db.rollback(); return time.perf_counter()-t,"err"
    return await run_ops("duplicate_payment_callback",n,op,sf)

async def run_ops(name,n,op,sf):
    before=await db_deadlocks(URL)
    mon=LockMonitor(URL); await mon.start(); started=time.perf_counter()
    results=await asyncio.gather(*[op(i) for i in range(n)])
    elapsed=time.perf_counter()-started
    samples,max_lock=await mon.stop_and_read(); after=await db_deadlocks(URL)
    lat=[x[0]*1000 for x in results]
    ok=sum(x[1] in ("ok","noop") for x in results); conflict=sum(x[1]=="conflict" for x in results); err=sum(x[1]=="err" for x in results)
    return Sample(name,n,name,ok,conflict,err,elapsed,n/elapsed,percentile(lat,.5),percentile(lat,.95),percentile(lat,.99),max(lat or [0]),samples,max_lock,after-before)

async def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--concurrency",nargs="+",type=int,default=[100,250,500,1000]); ap.add_argument("--workload",choices=["all","case","market","guild","payment"],default="all"); ap.add_argument("--pool-size",type=int,default=80); ap.add_argument("--report-out",default="artifacts/load_stress_report.md"); ap.add_argument("--json-out",default="artifacts/load_stress.json"); args=ap.parse_args()
    engine=create_async_engine(URL,pool_size=args.pool_size,max_overflow=max(args.pool_size,20),pool_pre_ping=True)
    sf=async_sessionmaker(engine,expire_on_commit=False,class_=AsyncSession)
    samples=[]
    for n in args.concurrency:
        workloads=[]
        if args.workload in ("all","case"): workloads.append(run_case)
        if args.workload in ("all","market"): workloads.append(run_market)
        if args.workload in ("all","guild"): workloads.append(run_guild)
        if args.workload in ("all","payment"): workloads.append(run_payment)
        for fn in workloads:
            samples.append(await fn(sf,n))
        if args.workload in ("all","market"):
            samples.append(await run_hot_market(sf,n))
    await engine.dispose()
    payload={"generated_at":datetime.now(timezone.utc).isoformat(),"samples":[asdict(x) for x in samples]}
    Path(args.json_out).parent.mkdir(parents=True,exist_ok=True);Path(args.json_out).write_text(json.dumps(payload,indent=2),encoding="utf-8")
    lines=["# VLDST PostgreSQL Stress QA","",f"Generated: {payload['generated_at']}","", "| Workload | N | OK | Conflicts | Errors | p50 ms | p95 ms | p99 ms | Max ms | Throughput/s | Lock samples | Max locks | Deadlocks |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for x in samples:
        lines.append(f"| {x.operation} | {x.concurrency} | {x.ok} | {x.expected_conflict} | {x.errors} | {x.p50_ms:.2f} | {x.p95_ms:.2f} | {x.p99_ms:.2f} | {x.max_ms:.2f} | {x.throughput_ops_s:.2f} | {x.lock_wait_samples} | {x.lock_wait_max} | {x.deadlocks_delta} |")
    lines += ["", "## Gate", "", "The stress gate fails when unexpected errors or PostgreSQL deadlocks occur. Expected Guild capacity and hot-market losers are counted as conflicts."]
    Path(args.report_out).parent.mkdir(parents=True,exist_ok=True);Path(args.report_out).write_text("\n".join(lines)+"\n",encoding="utf-8")
    unexpected=[x for x in samples if x.errors or x.deadlocks_delta]
    print(json.dumps({"samples":len(samples),"unexpected_failures":len(unexpected),"report":args.report_out,"json":args.json_out},indent=2))
    raise SystemExit(1 if unexpected else 0)

if __name__=="__main__": asyncio.run(main())
