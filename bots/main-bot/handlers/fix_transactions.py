import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from aiogram import Router, types
from aiogram.filters import Command
import asyncpg
import logging

router = Router()
logger = logging.getLogger(__name__)
ADMIN_ID = 838371525  # замени на свой

@router.message(Command("fix_transactions"))
async def cmd_fix(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("🔄 Исправляю transactions...")
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        await message.answer("❌ Нет DATABASE_URL.")
        return
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("ALTER TABLE transactions ALTER COLUMN related_id TYPE BIGINT;")
        await message.answer("✅ Тип изменён на BIGINT.")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    finally:
        await conn.close()