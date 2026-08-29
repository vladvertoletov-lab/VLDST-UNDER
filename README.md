# VLDST UNDERGROUND — Final deployable MVP
## 1. Local
`cp .env.example .env`
Set `BOT_TOKEN` and `DATABASE_URL`.
`pip install -r requirements.txt`
`uvicorn app.main:app --reload`
Bot: `python bot/bot.py`

## 2. Render
Create the Render Blueprint from `render.yaml`.
Set `BOT_TOKEN`, `WEBAPP_URL`, `PUBLIC_URL`, `ADMIN_IDS`.
The Postgres connection is provided by Render.

## 3. Telegram
In BotFather configure the Mini App URL to `/app`.
Set the bot token in Render.

## Included
20 cases, 160 item assets, 6 rarities, server-side case roll, inventory, sell,
recycle, upgrade, 20 quests, 10 games, daily streak, profile, referrals,
collections, leaderboard, guild foundation, gifts, Star Shop catalog,
Premium catalog, events, admin statistics, Telegram initData verification,
PostgreSQL, Render and Docker.

## Stars
This build deliberately exposes the Stars product catalog but does not fake successful
payments. Connect Telegram's official invoice/payment flow in a bot webhook before
accepting Stars. Never credit Stars/VLD merely because a client says payment succeeded.

## VLD
VLD is an in-game off-chain balance in this version. A future token is a separate
technical/legal product and should not be treated as a withdrawable asset by default.
