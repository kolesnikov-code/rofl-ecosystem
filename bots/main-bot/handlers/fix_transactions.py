from aiogram import Router, types
from aiogram.filters import Command
import os
import asyncpg
import logging

router = Router()
logger = logging.getLogger(__name__)

# Твой Telegram ID (замени, если нужно)
ADMIN_ID = 5270210217

@router.message(Command("fix_transactions"))
async def cmd_fix_transactions(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Доступ запрещён.")
        return

    await message.answer("🔄 Начинаю исправление таблицы transactions...")

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        await message.answer("❌ DATABASE_URL не найден.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Проверяем текущий тип колонки related_id
        row = await conn.fetchrow("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name='transactions' AND column_name='related_id'
        """)
        if not row:
            await message.answer("❌ Колонка related_id не найдена.")
            return

        current_type = row[0]
        if current_type == 'bigint':
            await message.answer("✅ Колонка related_id уже имеет тип BIGINT. Ничего не нужно делать.")
            return

        # Меняем тип на BIGINT
        await conn.execute("ALTER TABLE transactions ALTER COLUMN related_id TYPE BIGINT;")
        await message.answer("✅ Тип колонки related_id успешно изменён на BIGINT.")
        logger.info("Колонка related_id изменена на BIGINT")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        logger.error(f"Ошибка при изменении колонки: {e}")
    finally:
        await conn.close()