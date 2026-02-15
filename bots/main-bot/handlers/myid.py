import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from aiogram import Router, types
from aiogram.filters import Command
from shared.database import get_eco_id

router = Router()

@router.message(Command("myid"))
async def cmd_myid(message: types.Message):
    user_id = message.from_user.id
    eco_id = await get_eco_id(user_id)
    await message.answer(
        f"🆔 **Твой ROFL ID:** `{eco_id}`\n"
        "📌 Используй для переводов.",
        parse_mode="Markdown"
    )