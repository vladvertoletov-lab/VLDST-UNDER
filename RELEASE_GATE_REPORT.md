# VLDST Final GitHub Actions Release Gate

Implemented a single mandatory workflow: `.github/workflows/release-gate.yml`.

## Gate order

1. PostgreSQL 16 service + readiness check
2. Static/import checks
3. Unit tests
4. Alembic `upgrade head`
5. Seed
6. Seed smoke check
7. PostgreSQL API E2E
8. PostgreSQL E2E
9. Concurrency/race QA with explicit no-skip assertion
10. 1000-concurrent stress across all critical workloads
11. Performance thresholds
12. QA artifact upload

The workflow uses one stable required check: `Production Release Gate / Production Release Gate`.

## 1000-user stress workloads

- case_open
- guild_join
- market_purchase_distributed
- market_purchase_hot_listing
- duplicate_payment_callback

## Performance thresholds

- p95 <= 5000 ms
- p99 <= 10000 ms
- throughput >= 2 ops/sec
- max lock waiters <= 250
- unexpected errors = 0
- PostgreSQL deadlocks = 0
- required concurrency = 1000
- all required workload names must be present

## Important test-suite hardening

The PostgreSQL E2E suites no longer call `Base.metadata.drop_all/create_all`. The release pipeline owns schema lifecycle through Alembic. Test user identifiers are unique per fixture invocation so the same database can run the complete suite after seed without unique-key collisions.

## Repository setting required once

GitHub branch protection/rulesets must require:

`Production Release Gate / Production Release Gate`

This repository-side setting cannot be enforced by YAML alone.

Render remains configured with `autoDeployTrigger: checksPass`.

## Local verification

- Python compileall: PASS
- Workflow YAML parsing: PASS
- Threshold CLI: PASS
- Release workflow structure: PASS

A real PostgreSQL/GitHub-hosted run is not available in this execution environment, so the live 1000-concurrency benchmark remains a CI acceptance test rather than a claimed local pass.
