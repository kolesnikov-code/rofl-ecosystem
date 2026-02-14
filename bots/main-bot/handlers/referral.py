from aiogram import Router, types
from aiogram.filters import Command
from shared.database import get_ref_code

router = Router()

@router.message(Command("ref"))
async def cmd_ref(message: types.Message):
    user_id = message.from_user.id
    code = await get_ref_code(user_id)
    bot_username = (await message.bot.get_me()).username

    invite_link = f"https://t.me/{bot_username}?start=ref_{code}"

    text = (
        f"🔗 **Твоя реферальная ссылка:**\n"
        f"`{invite_link}`\n\n"
        f"👥 За каждого друга, который зарегистрируется — **1000 рофлов**.\n"
        f"👥👥 За друга твоего друга — **500 рофлов**.\n\n"
        f"💰 Рофлы начисляются сразу после регистрации друга.\n"
        f"📊 Статистику рефералов покажу позже."
    )
    await message.answer(text, parse_mode="Markdown")