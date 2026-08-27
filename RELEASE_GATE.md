# VLDST Production Release Gate

The single mandatory release workflow is `.github/workflows/release-gate.yml`.

Order is intentionally sequential:

1. PostgreSQL 16 starts and health-checks.
2. Python/static/import checks.
3. Unit tests.
4. Alembic `upgrade head`.
5. Seed data.
6. Seed smoke check.
7. API E2E.
8. PostgreSQL E2E.
9. PostgreSQL concurrency/race tests.
10. 1000-user stress benchmark across case opens, Guild joins, distributed/hot Market purchases and duplicate Stars callbacks.
11. Performance threshold gate.
12. QA evidence is uploaded as a workflow artifact.

## Required GitHub status check

In GitHub branch protection/rulesets for `main`, require the exact check:

`Production Release Gate / Production Release Gate`

This repository-side branch rule cannot be enabled by a source file alone; it is a one-time GitHub repository setting.

## Thresholds

- p95 <= 5000 ms
- p99 <= 10000 ms
- throughput >= 2 ops/sec
- max lock waiters <= 250
- unexpected errors = 0
- PostgreSQL deadlocks = 0
- concurrency level 1000 must be present
- all five required stress workloads must be present

Render uses `autoDeployTrigger: checksPass`, so Render waits for repository checks to pass. Keep the GitHub branch rule above enabled so `main` itself cannot be advanced without the release gate.
