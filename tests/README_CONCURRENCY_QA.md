# VLDST UNDERGROUND — PostgreSQL Concurrency QA

## Scenarios

| Scenario | Concurrent operations | Expected invariant |
|---|---:|---|
| Case opens | 20 | 10 successful at 100 VLD each from 1000 VLD; no negative balance |
| Market buy | 2 | Exactly 1 buyer wins a listing; exactly 1 market transaction |
| Guild join | 10 | With capacity 3 and owner already present, exactly 2 joins succeed |
| Stars callback | 25 | Exactly 1 entitlement/payment transition is applied |

## Required runtime

A real PostgreSQL instance and `asyncpg` are required. SQLite is deliberately not supported for this suite because row locks and transaction isolation are part of what is being tested.

```bash
E2E_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/vldst_e2e \
pytest -q tests/test_concurrency_postgres.py
```

The test fixture creates a disposable schema and the tests use independent `AsyncSession` objects so operations actually overlap at the database level.

## Concurrency hardening included

- VLD balance mutations use `SELECT ... FOR UPDATE`.
- Case opens serialize on the player's balance row before idempotency/reward processing.
- Market purchases lock the listing and inventory row, making a listing single-winner.
- Guild joins lock the user row and guild row, protecting both one-guild membership and capacity.
- Telegram successful-payment handling locks the purchase row before entitlement is granted.
- Database uniqueness constraints remain the final duplicate guard.

## Environment limitation during this QA run

The execution environment used to prepare this package does not contain `asyncpg` and does not provide a PostgreSQL server. Therefore the real PostgreSQL concurrency suite was invoked and correctly **SKIPPED** rather than silently substituting SQLite.

Static validation and Python compilation were run successfully.
