# VLDST UNDERGROUND

Production-oriented Telegram Mini App ecosystem: FastAPI + PostgreSQL + aiogram 3 + vanilla JS/CSS Admin/Mini App.

## What is included

- Telegram Mini App authentication via signed `initData`
- aiogram 3 bot with `/start`, `/app`, `/profile`, `/daily`, `/quests`, `/games`, `/cases`, `/inventory`, `/ref`, `/leaderboard`, `/help`
- PostgreSQL schema + migrations
- Seed data: 20 cases, 160 items, 20 collections, 100 achievements, 30 cosmetics/Stars products, recipes, games, seasons and events
- Server-side economy ledger and idempotent operations
- Cases with transparent weights and pity/guarantee rules
- Inventory, recycle, upgrade, Fusion, Craft
- Daily/weekly/season/secret/chain quests
- Mini-games with server-issued sessions and anti-tamper score validation
- Vault, market, trading, referrals, creator codes
- Telegram Stars/XTR payment adapter with `pre_checkout` and successful-payment handling
- Premium + cosmetic shop
- Seasons/events/global goals
- Guilds and leaderboards
- Admin panel with audit logging and economy controls
- Rate limiting, security logs, anti-duplicate operation keys
- Docker Compose and Render blueprint
- Automated tests

## Stack

Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, aiogram 3, Pydantic Settings, JWT, vanilla JavaScript/CSS.

## Local setup

1. Install Docker + Docker Compose.
2. Copy `.env.example` to `.env`.
3. Set at minimum:
   - `BOT_TOKEN`
   - `SECRET_KEY`
   - `ADMIN_IDS`
   - `PUBLIC_URL`
   - `WEBAPP_URL`
   - `BOT_USERNAME`
4. Start:
   ```bash
   docker compose up --build
   ```
5. Run migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```
6. Seed:
   ```bash
   docker compose exec backend python -m app.seed
   ```
7. Open the Mini App at `http://localhost:8000/`.
8. API docs: `/docs`.
9. Admin panel: `/admin/`.

## Without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend python -m app.seed
PYTHONPATH=backend uvicorn app.main:app --reload
```

Run bot separately:
```bash
PYTHONPATH=bot:backend python bot/bot.py
```

## Telegram Mini App

Set the bot's Web App URL to `WEBAPP_URL`. The client sends Telegram `initData` to `/api/auth/telegram`. The backend verifies the Telegram signature using the bot token; ordinary client-provided Telegram user IDs are not trusted.

For production, serve over HTTPS.

## Telegram Stars

Use Telegram's XTR currency. Configure the bot and Stars products through `STARS_PROVIDER_TOKEN` when required by your Telegram payment setup. The implementation creates invoices, validates `pre_checkout`, and only grants products after a successful payment update. Payment payloads are idempotent.

Do not use Stars as a wager or for random paid chance. VLD is an off-chain game currency.

## Render

The repository contains `render.yaml`. Create the Blueprint from GitHub, provide secrets in Render, then run migrations and seed once from the service shell.

## Environment variables

See `.env.example`.

## Backup strategy

Use scheduled PostgreSQL logical backups or Render's supported database backup facilities. Test restore procedures regularly. Keep backups encrypted and separate from application storage.

## Security notes

- Never commit `.env`.
- All VLD changes go through the ledger.
- Reward endpoints use operation keys.
- Case outcomes are generated server-side.
- Game rewards require a valid server-issued session.
- Admin actions are audited.
- Rate limits are applied to sensitive routes.
- This project does not represent VLD as real money or an investment.

## API overview

### Public/authenticated
`GET /api/health`, `POST /api/auth/telegram`, `GET /api/me`, `GET /api/profile`, `GET /api/cases`, `POST /api/cases/{id}/open`, `GET /api/inventory`, `POST /api/inventory/{id}/recycle`, `POST /api/inventory/{id}/upgrade`, `GET /api/collections`, `GET /api/quests`, `POST /api/quests/{id}/claim`, `GET /api/games`, `POST /api/games/{id}/start`, `POST /api/games/{id}/finish`, `GET /api/leaderboard`, `GET /api/events`, `GET /api/guild`, `GET /api/referrals`, `GET /api/shop`, `POST /api/shop/purchase`, `GET /api/transactions`, `GET /api/notifications`, `GET /api/seasons`.

### Admin
`GET /api/admin/dashboard`, `GET /api/admin/users`, `POST /api/admin/users/{id}/adjust`, `POST /api/admin/broadcast`, `POST /api/admin/economy`, `GET /api/admin/audit`.

## Telegram commands

`/start`, `/app`, `/profile`, `/daily`, `/quests`, `/games`, `/cases`, `/inventory`, `/ref`, `/leaderboard`, `/help`.

## Tests

```bash
PYTHONPATH=backend pytest -q
```

## Production checklist

- [ ] HTTPS configured
- [ ] PostgreSQL backups configured
- [ ] `SECRET_KEY` generated randomly
- [ ] Admin IDs verified
- [ ] Bot Web App URL configured
- [ ] Telegram Stars configured
- [ ] Migrations applied
- [ ] Seed run
- [ ] Logs/monitoring configured
- [ ] Rate limits reviewed

## Full Mini App backend actions

The current build includes server-authoritative actions for the commercial UX: Guild create/join/leave, Vault Showcase (max 6), collection milestone rewards (25/50/75/100%), live Event join/progress/global-goal claims, Season XP and 50-level reward claims, Achievement unlock evaluation and title selection, Stars XTR invoice creation, pre-checkout validation and post-payment entitlement delivery.

### Telegram Stars

Telegram Stars purchases use currency `XTR`. The backend calls Telegram `createInvoiceLink`; the Mini App opens the returned invoice URL with `Telegram.WebApp.openInvoice`. The bot validates `pre_checkout_query` against the stored pending purchase and verifies the final `successful_payment` before granting a cosmetic or Premium entitlement. No VLD or random gameplay outcome is sold for Stars. Provider tokens are not required for native Telegram Stars/XTR invoices.

Required production environment: `BOT_TOKEN`, `DATABASE_URL`, `SECRET_KEY`, `WEBAPP_URL`, `BOT_USERNAME`, and `ADMIN_IDS`.

### New API actions

- `GET/POST /api/guilds`, `/api/guild/create`, `/api/guild/join`, `/api/guild/leave`
- `GET/POST /api/vault/showcase`
- `POST /api/collections/{collection_id}/claim/{milestone}`
- `GET/POST /api/events`, `/api/events/{event_id}/join`, `/progress`, `/claim`
- `GET/POST /api/seasons`, `/api/seasons/{season_id}/xp`, `/claim`
- `GET /api/achievements`
- `POST /api/profile/title`
- `POST /api/shop/purchase`, `GET /api/shop/owned`, `POST /api/shop/equip/{product_id}`

Run migrations before seed: `./scripts/migrate.sh`, then `./scripts/seed.sh`.

## Production Hardening

The release candidate uses authoritative server-side gameplay actions. Quest/Event/Season progress cannot be awarded by submitting arbitrary progress amounts. Game sessions are locked during settlement, player rows use a stable lock order, and economy mutations use row-locked balances.

### PostgreSQL migrations

`backend/migrations/versions/0001_initial.py` is the explicit baseline migration. `0002_full_systems.py` is retained as a compatibility no-op for the pre-release migration history. New deployments should run `upgrade head` from an empty PostgreSQL database.

### QA gates

CI runs unit/static QA, PostgreSQL E2E/concurrency QA, and a 1000-concurrent performance gate. The performance gate checks p95/p99 latency, throughput, peak lock waiters, unexpected errors and PostgreSQL deadlocks.

Local stress gate:

```bash
E2E_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/vldst_e2e \
python scripts/stress_load.py --concurrency 100 250 500 1000
```

Then validate a report:

```bash
python scripts/validate_stress_thresholds.py artifacts/load-1000.json
```

## Render production deployment (Python runtime)

This release uses Render's native Python runtime, not the Docker runtime. The repository root contains `requirements.txt`, and Render runs:

```text
Build: pip install -r requirements.txt
Start: python start.py
Health: /api/health
```

`start.py` runs Alembic migrations, performs the idempotent seed, then keeps FastAPI and the Telegram long-polling bot alive in the same web-service process. This is intentional for a single Render Free service.

Required Render variables:

- `DATABASE_URL` — supplied from the Render Postgres database through `fromDatabase.connectionString`.
- `BOT_TOKEN` — the Telegram bot token.
- `SECRET_KEY` — generated by Render.
- `PUBLIC_URL` / `WEBAPP_URL` — `https://vldst-underground.onrender.com` and the same URL with `/` for the Mini App.
- `BOT_USERNAME` — `VLDST_miniapp_bot`.
- `ADMIN_IDS` — comma-separated Telegram numeric IDs allowed to use admin endpoints.
- `CORS_ORIGINS` — `https://vldst-underground.onrender.com`.

The application accepts Render's `postgres://`/`postgresql://` connection string and converts it internally to SQLAlchemy's `postgresql+asyncpg://` format.

### Telegram referral flow

The referral API creates a normal Telegram bot deep link (`?start=CODE`). The bot receives that payload on `/start`, then passes it into the Mini App as `startapp=CODE`; the signed Telegram `initData` is verified by the backend before the referral is attached to a new account.
