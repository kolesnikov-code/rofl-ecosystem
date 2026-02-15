import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from aiogram import Router, types
from aiogram.filters import Command
import os
import asyncpg
import logging

router = Router()
logger = logging.getLogger(__name__)

# ID администратора (твой Telegram ID)
ADMIN_ID = 838371525  # замени на свой, если нужно

@router.message(Command("migrate"))
async def cmd_migrate(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён.")
        return

    await message.answer("🔄 Начинаю миграцию...")

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        await message.answer("❌ DATABASE_URL не найден.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # 1. Обновляем старые KLM_ на ROFL-
        result = await conn.execute("""
            UPDATE users 
            SET eco_id = 'ROFL-' || LPAD(SUBSTRING(eco_id FROM 5)::text, 7, '0')
            WHERE eco_id LIKE 'KLM_%'
        """)
        updated = result.split()[1]  # количество обновлённых строк

        # 2. Сбрасываем реферальные коды
        await conn.execute("UPDATE users SET ref_code = NULL WHERE ref_code IS NOT NULL")

        await message.answer(f"✅ Миграция завершена. Обновлено записей: {updated}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        logger.error(f"Ошибка миграции: {e}")
    finally:
        await conn.close()