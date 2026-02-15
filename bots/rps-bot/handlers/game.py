import random
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from shared.database import get_balance, update_balance, add_transaction, get_user_gender

router = Router()
logger = logging.getLogger(__name__)

choices = {"rock": "🪨 Камень", "paper": "📜 Бумага", "scissors": "✂️ Ножницы"}

def determine_winner(player, bot):
    if player == bot:
        return "draw"
    if (player == "rock" and bot == "scissors") or \
       (player == "scissors" and bot == "paper") or \
       (player == "paper" and bot == "rock"):
        return "player"
    return "bot"

@router.message(Command("play"))
async def cmd_play(message: types.Message):
    user_id = message.from_user.id
    if not await get_user_gender(user_id):
        await message.answer("❌ Сначала зарегистрируйся в главном боте.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=v, callback_data=f"rps_{k}") for k, v in choices.items()]
    ])
    await message.answer("Выбери ход:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data and c.data.startswith("rps_"))
async def process_choice(callback: CallbackQuery):
    user_id = callback.from_user.id
    player = callback.data.split("_")[1]
    bot = random.choice(["rock", "paper", "scissors"])
    result = determine_winner(player, bot)
    reward = 5 if result == "player" else 0
    if reward:
        await update_balance(user_id, reward)
        await add_transaction(user_id, reward, "game", "Победа в КНБ")
    new_balance = await get_balance(user_id)
    await callback.message.edit_text(
        f"Твой выбор: {choices[player]}\nМой выбор: {choices[bot]}\n\n"
        f"{'Ты победил!' if result=='player' else 'Ты проиграл.' if result=='bot' else 'Ничья.'} "
        f"{'+' + str(reward) + ' рофлов' if reward else '0 рофлов'}\n"
        f"💰 Баланс: {new_balance}"
    )
    await callback.answer()