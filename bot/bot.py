import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    PreCheckoutQuery,
)

from sqlalchemy import select

from app.db import SessionLocal
from app.models import StarsPurchase, StarsProduct, User
from app.services.payments import grant_stars_entitlement


TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP = os.getenv("WEBAPP_URL", "http://localhost:8000/").rstrip("/")

dp = Dispatcher()


def menu(start_param: str | None = None):
    url = WEBAPP

    if start_param:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}startapp={start_param}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="OPEN VLDST",
                    web_app=WebAppInfo(url=url),
                )
            ]
        ]
    )


@dp.message(CommandStart())
async def start(m: Message):
    # Telegram sends /start or /start PAYLOAD.
    args = m.text.split(maxsplit=1) if m.text else []
    start_param = args[1].strip() if len(args) > 1 else None

    text = (
        "⚡ VLDST UNDERGROUND\n"
        "Добро пожаловать в Cyber Underground."
    )

    if start_param:
        text += "\n\nReferral/start параметр получен."

    await m.answer(
        text,
        reply_markup=menu(start_param),
    )


@dp.message(Command("app"))
async def app(m: Message):
    await m.answer(
        "Открыть VLDST:",
        reply_markup=menu(),
    )


@dp.message(Command("profile"))
async def profile(m: Message):
    await m.answer(
        "Профиль доступен внутри Mini App.",
        reply_markup=menu(),
    )


@dp.message(Command("daily"))
async def daily(m: Message):
    await m.answer(
        "Daily Reward доступен в разделе Home.",
        reply_markup=menu(),
    )


@dp.message(Command("quests"))
async def quests(m: Message):
    await m.answer(
        "Quests Hub:",
        reply_markup=menu(),
    )


@dp.message(Command("games"))
async def games(m: Message):
    await m.answer(
        "Games Hub:",
        reply_markup=menu(),
    )


@dp.message(Command("cases"))
async def cases(m: Message):
    await m.answer(
        "Cases:",
        reply_markup=menu(),
    )


@dp.message(Command("inventory"))
async def inventory(m: Message):
    await m.answer(
        "Vault / Inventory:",
        reply_markup=menu(),
    )


@dp.message(Command("ref"))
async def ref(m: Message):
    await m.answer(
        "Referral link создаётся в Mini App.",
        reply_markup=menu(),
    )


@dp.message(Command("leaderboard"))
async def leaderboard(m: Message):
    await m.answer(
        "Leaderboard:",
        reply_markup=menu(),
    )


@dp.message(Command("help"))
async def help_(m: Message):
    await m.answer(
        "VLDST UNDERGROUND — "
        "/app /profile /daily /quests /games "
        "/cases /inventory /ref /leaderboard"
    )


@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    async with SessionLocal() as db:
        purchase = (
            await db.execute(
                select(StarsPurchase).where(
                    StarsPurchase.payload == q.invoice_payload
                )
            )
        ).scalar_one_or_none()

        owner = await db.get(User, purchase.user_id) if purchase else None

        if (
            not purchase
            or not owner
            or owner.telegram_id != q.from_user.id
            or purchase.status != "pending"
        ):
            await q.answer(
                ok=False,
                error_message="Invoice недействителен или уже обработан",
            )
            return

        product = await db.get(StarsProduct, purchase.product_id)

        if (
            not product
            or not product.active
            or q.currency != "XTR"
            or q.total_amount != product.stars_price
        ):
            await q.answer(
                ok=False,
                error_message="Цена или товар больше недоступны",
            )
            return

        await q.answer(ok=True)


@dp.message(lambda m: m.successful_payment is not None)
async def successful_payment(m: Message):
    sp = m.successful_payment

    async with SessionLocal() as db:
        purchase = (
            await db.execute(
                select(StarsPurchase)
                .where(StarsPurchase.payload == sp.invoice_payload)
                .with_for_update()
            )
        ).scalar_one_or_none()

        owner = await db.get(User, purchase.user_id) if purchase else None

        if (
            not purchase
            or not owner
            or owner.telegram_id != m.from_user.id
        ):
            return

        if purchase.status == "paid":
            return

        product = await db.get(StarsProduct, purchase.product_id)

        if (
            not product
            or sp.currency != "XTR"
            or sp.total_amount != product.stars_price
        ):
            purchase.status = "rejected"
            await db.commit()
            return

        await grant_stars_entitlement(
            db,
            purchase,
            product,
            sp.telegram_payment_charge_id,
        )

        await db.commit()

    await m.answer(
        "★ Оплата подтверждена. Товар добавлен в VLDST."
    )


async def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is required")

    bot = Bot(TOKEN)

    await bot.delete_webhook(drop_pending_updates=False)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
