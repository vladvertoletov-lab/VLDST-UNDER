import asyncio,os
from aiogram import Bot,Dispatcher
from aiogram.filters import CommandStart,Command
from aiogram.types import Message,InlineKeyboardMarkup,InlineKeyboardButton,WebAppInfo
from dotenv import load_dotenv
load_dotenv(); TOKEN=os.getenv("BOT_TOKEN"); URL=os.getenv("WEBAPP_URL","http://localhost:8000/app")
dp=Dispatcher()
@dp.message(CommandStart())
async def start(m:Message):
    kb=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 ОТКРЫТЬ VLDST",web_app=WebAppInfo(url=URL))]])
    await m.answer("🟣 <b>VLDST UNDERGROUND</b>\nКейсы • игры • задания • коллекции • гильдии",reply_markup=kb,parse_mode="HTML")
@dp.message(Command("app"))
async def app(m:Message): await start(m)
async def main():
    if not TOKEN: raise RuntimeError("BOT_TOKEN is missing")
    await dp.start_polling(Bot(TOKEN))
if __name__=="__main__": asyncio.run(main())
