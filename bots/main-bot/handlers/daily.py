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
        logger.error(f"Ошибка в daily для {user_id}: {e}")
        await message.answer("❌ Что-то пошло не так. Попробуй позже.")
        return

    if result is None:
        await message.answer("⏳ Ты уже получал(а) ежедневный бонус сегодня. Возвращайся через 24 часа!")
        return

    bonus, streak = result
    balance = await get_balance(user_id)
    gender = await get_user_gender(user_id) or "other"

    if gender == "male":
        msg = (
            f"🎁 Ежедневный бонус получен!\n"
            f"💰 +{bonus} рофлов\n"
            f"🔥 Серия: {streak} дней\n"
            f"💳 Твой баланс: {balance} рофлов"
        )
    elif gender == "female":
        msg = (
            f"🎁 Ежедневный бонус получен!\n"
            f"💰 +{bonus} рофлов\n"
            f"🔥 Серия: {streak} дней\n"
            f"💳 Твой баланс: {balance} рофлов"
        )
    else:
        msg = (
            f"🎁 Ежедневный бонус получен!\n"
            f"💰 +{bonus} рофлов\n"
            f"🔥 Серия: {streak} дней\n"
            f"💳 Твой баланс: {balance} рофлов"
        )

    await message.answer(msg)