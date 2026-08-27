import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PreCheckoutQuery,
    WebAppInfo,
)
from sqlalchemy import select

from app.db import SessionLocal
from app.models import StarsProduct, StarsPurchase, User
from app.services.payments import grant_stars_entitlement


TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP = os.getenv("WEBAPP_URL", "http://localhost:8000/").rstrip("/")

dp = Dispatcher()


def menu(start_param: str | None = None) -> InlineKeyboardMarkup:
    url = WEBAPP
    if start_param:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}startapp={start_param}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="OPEN VLDST", web_app=WebAppInfo(url=url))]
        ]
    )


@dp.message(CommandStart())
async def start(message: Message):
    # /start REF_CODE is the normal Telegram bot deep-link format.
    args = message.text.split(maxsplit=1) if message.text else []
    start_param = args[1].strip() if len(args) > 1 else None
    text = "⚡ VLDST UNDERGROUND\nДобро пожаловать в Cyber Underground."
    if start_param:
        text += "\n\nReferral/start параметр получен."
    await message.answer(text, reply_markup=menu(start_param))


@dp.message(Command("app"))
async def app(message: Message):
    await message.answer("Открыть VLDST:", reply_markup=menu())


@dp.message(Command("profile"))
async def profile(message: Message):
    await message.answer("Профиль доступен внутри Mini App.", reply_markup=menu())


@dp.message(Command("daily"))
async def daily(message: Message):
    await message.answer("Daily Reward доступен в разделе Home.", reply_markup=menu())


@dp.message(Command("quests"))
async def quests(message: Message):
    await message.answer("Quests Hub:", reply_markup=menu())


@dp.message(Command("games"))
async def games(message: Message):
    await message.answer("Games Hub:", reply_markup=menu())


@dp.message(Command("cases"))
async def cases(message: Message):
    await message.answer("Cases:", reply_markup=menu())


@dp.message(Command("inventory"))
async def inventory(message: Message):
    await message.answer("Vault / Inventory:", reply_markup=menu())


@dp.message(Command("ref"))
async def ref(message: Message):
    await message.answer("Referral link создаётся в Mini App.", reply_markup=menu())


@dp.message(Command("leaderboard"))
async def leaderboard(message: Message):
    await message.answer("Leaderboard:", reply_markup=menu())


@dp.message(Command("help"))
async def help_(message: Message):
    await message.answer(
        "VLDST UNDERGROUND — /app /profile /daily /quests /games "
        "/cases /inventory /ref /leaderboard"
    )


@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    async with SessionLocal() as db:
        purchase = (
            await db.execute(
                select(StarsPurchase).where(
                    StarsPurchase.payload == query.invoice_payload
                )
            )
        ).scalar_one_or_none()
        owner = await db.get(User, purchase.user_id) if purchase else None

        if (
            not purchase
            or not owner
            or owner.telegram_id != query.from_user.id
            or purchase.status != "pending"
        ):
            await query.answer(
                ok=False,
                error_message="Invoice недействителен или уже обработан",
            )
            return

        product = await db.get(StarsProduct, purchase.product_id)
        if (
            not product
            or not product.active
            or query.currency != "XTR"
            or query.total_amount != product.stars_price
        ):
            await query.answer(
                ok=False,
                error_message="Цена или товар больше недоступны",
            )
            return

    await query.answer(ok=True)


@dp.message(lambda message: message.successful_payment is not None)
async def successful_payment(message: Message):
    payment = message.successful_payment
    async with SessionLocal() as db:
        purchase = (
            await db.execute(
                select(StarsPurchase)
                .where(StarsPurchase.payload == payment.invoice_payload)
                .with_for_update()
            )
        ).scalar_one_or_none()
        owner = await db.get(User, purchase.user_id) if purchase else None

        if (
            not purchase
            or not owner
            or owner.telegram_id != message.from_user.id
        ):
            return
        if purchase.status == "paid":
            return

        product = await db.get(StarsProduct, purchase.product_id)
        if (
            not product
            or payment.currency != "XTR"
            or payment.total_amount != product.stars_price
        ):
            purchase.status = "rejected"
            await db.commit()
            return

        await grant_stars_entitlement(
            db,
            purchase,
            product,
            payment.telegram_payment_charge_id,
        )
        await db.commit()

    await message.answer("★ Оплата подтверждена. Товар добавлен в VLDST.")


async def run_bot():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is required")
    bot = Bot(TOKEN)
    try:
        # Polling must own the bot process; clearing an old webhook prevents
        # Telegram from routing updates away from this instance.
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


async def main():
    await run_bot()


if __name__ == "__main__":
    asyncio.run(main())
