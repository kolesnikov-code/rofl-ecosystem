import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from shared.database import init_db

from handlers import (
    start, balance, catalog, channel_subs,
    daily, send, referral, payment, myid, fix_transactions
)

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(balance.router)
    dp.include_router(catalog.router)
    dp.include_router(channel_subs.router)
    dp.include_router(daily.router)
    dp.include_router(send.router)
    dp.include_router(referral.router)
    dp.include_router(payment.router)
    dp.include_router(myid.router)
    dp.include_router(fix_transactions.router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Бот остановлен пользователем")