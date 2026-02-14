from aiogram import Router, types
from aiogram.filters import Command
from shared.database import get_eco_id

router = Router()

@router.message(Command("myid"))
async def cmd_myid(message: types.Message):
    user_id = message.from_user.id
    eco_id = await get_eco_id(user_id)
    await message.answer(
        f"🆔 **Твой ROFL ID:** `{eco_id}`\n\n"
        "📌 Используй его для переводов и входа на сайт.\n"
        "Также ты можешь переводить по:\n"
        "• @username\n"
        "• Telegram ID (число)",
        parse_mode="Markdown"
    )