import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from aiogram import Router, types
from aiogram.filters import Command
from shared.database import claim_daily, get_balance, get_user_gender
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("daily"))
async def cmd_daily(message: types.Message):
    user_id = message.from_user.id
    try:
        result = await claim_daily(user_id)
    except Exception as e:
        logger.error(f"Ошибка daily для {user_id}: {e}")
        await message.answer("❌ Ошибка. Попробуй позже.")
        return

    if result is None:
        await message.answer("⏳ Ты уже получал бонус сегодня. Возвращайся через 24ч!")
        return

    bonus, streak = result
    balance = await get_balance(user_id)
    gender = await get_user_gender(user_id) or "other"
    msg = f"🎁 Ежедневный бонус!\n💰 +{bonus} рофлов\n🔥 Серия: {streak} дней\n💳 Баланс: {balance}"
    await message.answer(msg)