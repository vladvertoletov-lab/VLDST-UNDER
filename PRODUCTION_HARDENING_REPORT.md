# VLDST UNDERGROUND — Production Hardening Sprint

## Status

**Release Candidate — hardening complete at code/configuration level.**

A live PostgreSQL/Telegram/Render deployment is still required for the final acceptance gate because this execution environment does not provide a PostgreSQL server or GitHub-hosted runner.

## P0 exploit closures

- Quest claim no longer creates completed progress implicitly.
- Client-controlled Event Progress is disabled; event progress is generated only by verified server actions.
- Client-controlled Season XP endpoint is disabled; Season XP is awarded by server gameplay services.
- Game settlement locks the session and treats client score as untrusted telemetry. Rewards are fixed server-side rather than calculated from arbitrary client score.
- Energy spending locks the user row and includes server-side regeneration.
- Achievement unlocks use authoritative DB counters and unique DB constraints.
- Case opens use a stable user -> balance lock order and server-side pity state.
- Market purchases lock buyer/seller users in stable order, then the listing/inventory.
- Stars purchase creation locks the user; successful payment entitlement is protected by payment-row locking and unique charge/payload constraints.
- Banned users are rejected immediately and token session versions can be revoked.

## Authoritative gameplay engine

`backend/app/services/gameplay.py` centralizes action fan-out:

`game`, `case`, `craft`, `fusion`, `recycle`, `quest_claim`, `daily`, `trade`, `collection`, `event`.

These actions update Quest, Event and Guild Quest progress without accepting arbitrary reward/progress values from the Mini App.

## Completed systems

- Daily reward + streak
- Quest progress/claim hardening
- Craft Lab + 30 recipes
- Fusion
- Vault + upgrades + capacity
- Guild quests + claims
- Market + fee configuration
- Trading confirmation flow
- Promo code redemption
- Referral registration + milestone reward foundation
- Season Premium Pass entitlement
- Season premium reward track
- Admin user controls
- Admin economy controls
- Admin case/quest creation
- Admin broadcast notifications
- Game result persistence
- Case pity persistence
- Event global progress persistence

## Database / Alembic

`0001_initial.py` is now an explicit `op.create_table` baseline rather than `Base.metadata.create_all()`.

`0002_full_systems.py` is retained as a compatibility revision and is a no-op for the squashed baseline.

Offline Alembic SQL generation was verified successfully.

The current metadata contains **48 PostgreSQL tables**, including the core economy, game, case, collection, vault, guild, market, trade, Stars, season, referral, crafting and audit tables.

## CI/CD

Production Gate dependencies are now:

1. Unit / Static QA
2. PostgreSQL E2E / Concurrency Gate
3. PostgreSQL 1000-user Performance Gate
4. Production Deploy Gate

The performance gate checks:

- p95
- p99
- throughput
- peak lock waiters
- unexpected errors
- PostgreSQL deadlocks

Render remains configured for `autoDeployTrigger: checksPass`.

## Verification performed in this environment

- Python AST: PASS
- Python compilation: PASS
- JavaScript syntax: PASS
- Alembic offline SQL generation: PASS
- API route presence check: PASS
- model metadata import: PASS
- required endpoint check: PASS
- ZIP artifact hygiene: pending final packaging

## Environment limitation

A real PostgreSQL concurrency/stress execution cannot be claimed from this environment because PostgreSQL/asyncpg runtime access is unavailable here. GitHub Actions is configured to execute the real database gate.
