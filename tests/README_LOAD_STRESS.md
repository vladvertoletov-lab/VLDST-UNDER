# VLDST PostgreSQL Stress QA

`stress_load.py` is a real PostgreSQL benchmark, not a SQLite substitute.

It runs 100/250/500/1000 concurrent operations and records:

- p50/p95/p99/max latency
- throughput (operations/sec)
- unexpected errors
- expected conflicts
- PostgreSQL lock-wait samples and peak lock waiters
- `pg_stat_database.deadlocks` delta

Workloads:

- case opens against one player's balance row (hot-row lock contention)
- distributed market purchases
- hot market listing purchase race
- Guild joins against one capacity-limited Guild
- duplicate Stars callbacks against one payment row

Run locally:

```bash
E2E_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/vldst_e2e \
  python scripts/stress_load.py --concurrency 100 250 500 1000
```

The command exits non-zero on unexpected errors or deadlocks. Expected business conflicts (full Guild / already sold listing) are not failures.
