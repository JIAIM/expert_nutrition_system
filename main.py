import asyncio
import os
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from tg_bot.handlers.onboarding import router as onboarding_router

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

dp.include_router(onboarding_router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())