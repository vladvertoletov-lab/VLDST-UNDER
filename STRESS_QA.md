# VLDST PostgreSQL Stress QA

Added a real PostgreSQL stress benchmark for 100/250/500/1000 concurrent operations.

## Metrics

- p50/p95/p99/max latency
- throughput (ops/sec)
- unexpected errors
- expected business conflicts
- lock-wait samples from `pg_stat_activity`
- peak lock waiters
- deadlock delta from `pg_stat_database`

## Workloads

1. Case opens against a single balance row — hot-row contention.
2. Distributed market purchases — independent listings.
3. Hot market listing — concurrent winner race.
4. Guild joins — one capacity-limited guild.
5. Duplicate Telegram Stars callbacks — one payment row.

## Local run

```bash
E2E_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/vldst_e2e \
python scripts/stress_load.py --concurrency 100 250 500 1000
```

The process exits with code 1 if unexpected errors or deadlocks are observed.
Expected conflicts are not failures.

## CI

`.github/workflows/load-stress.yml` runs a matrix of 100/250/500/1000 on PostgreSQL 16 and uploads JSON/Markdown artifacts.
