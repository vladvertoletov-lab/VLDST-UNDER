#!/usr/bin/env python3
"""Production entrypoint for Render and Docker.

One process owns both the FastAPI web server and the Telegram long-polling bot.
That is intentional for a single Render Free web service: there is no separate
worker to keep alive, while the HTTP service still binds to Render's PORT.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
os.chdir(ROOT)

# Make both ``app`` and ``bot`` importable in every launch mode.
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))


def run_checked(*args: str, cwd: Path = ROOT) -> None:
    print("$", " ".join(args), flush=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{BACKEND}:{ROOT}" + (
        f":{env['PYTHONPATH']}" if env.get("PYTHONPATH") else ""
    )
    subprocess.run(args, cwd=cwd, env=env, check=True)


async def serve() -> None:
    import uvicorn
    from app.config import settings
    from app.main import app
    from bot.bot import run_bot

    port = int(os.getenv("PORT", "10000"))
    uvicorn_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        log_level=settings.log_level.lower(),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
    server = uvicorn.Server(uvicorn_config)

    api_task = asyncio.create_task(server.serve(), name="api")
    bot_task = asyncio.create_task(run_bot(), name="telegram-bot")
    done, pending = await asyncio.wait(
        {api_task, bot_task}, return_when=asyncio.FIRST_COMPLETED
    )

    error: BaseException | None = None
    for task in done:
        try:
            task.result()
        except BaseException as exc:  # propagate the real failing component
            error = exc
            print(f"FATAL: {task.get_name()} stopped: {exc!r}", flush=True)

    if not bot_task.done():
        bot_task.cancel()
    if not api_task.done():
        await server.shutdown()
        api_task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

    if error:
        raise error


async def main() -> None:
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is required")
    if not os.getenv("BOT_TOKEN"):
        raise RuntimeError("BOT_TOKEN is required")

    # Render Free does not provide a pre-deploy hook. Run migrations and the
    # idempotent seed immediately before starting the long-lived service.
    run_checked(sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head", cwd=BACKEND)
    run_checked(sys.executable, "-m", "app.seed")
    await serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
