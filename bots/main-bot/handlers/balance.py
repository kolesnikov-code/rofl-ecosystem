import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

import asyncpg
import logging
import html
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from shared.database import get_balance, get_user_gender, transfer_coins

router = Router()
logger = logging.getLogger(__name__)

class TransferState(StatesGroup):
    waiting_identifier = State()
    waiting_amount = State()

@router.message(Command("balance"))
async def cmd_balance(message: types.Message):
    user_id = message.from_user.id
    balance = await get_balance(user_id)
    gender = await get_user_gender(user_id) or "other"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Перевести", callback_data="transfer_start")]
    ])
    text = f"💰 Твой баланс: *{balance} рофлов*\n\nНе пыль на полке — кинь братану.\n💬 /send @username сумма"
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    logger.info(f"Баланс для {user_id}: {balance}")

@router.callback_query(lambda c: c.data == "transfer_start")
async def transfer_start_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "💸 Введи получателя (@username, Telegram ID или ROFL ID):\n_(отправь /cancel для отмены)_",
        parse_mode="Markdown"
    )
    await state.set_state(TransferState.waiting_identifier)
    await callback.answer()

@router.message(Command("cancel"), StateFilter(TransferState))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Перевод отменён.")

@router.message(StateFilter(TransferState.waiting_identifier), ~F.text.startswith('/'))
async def transfer_identifier(message: types.Message, state: FSMContext):
    identifier = message.text.strip()
    sender_id = message.from_user.id
    logger.info(f"📥 Ввод идентификатора: {identifier} от {sender_id}")

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        await message.answer("❌ Ошибка БД."); await state.clear(); return

    receiver_id = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            if identifier.startswith('@'):
                clean = identifier[1:].strip()
                row = await conn.fetchrow("SELECT telegram_id FROM users WHERE username ILIKE $1", clean)
                if row: receiver_id = row[0]
            elif identifier.startswith('ROFL-') or identifier.startswith('KLM_'):
                row = await conn.fetchrow("SELECT telegram_id FROM users WHERE eco_id = $1", identifier)
                if row: receiver_id = row[0]
            elif identifier.isdigit():
                row = await conn.fetchrow("SELECT telegram_id FROM users WHERE telegram_id = $1", int(identifier))
                if row: receiver_id = row[0]
            else:
                await message.answer("❌ Неверный формат."); return
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Ошибка БД: {e}")
        await message.answer("❌ Ошибка поиска."); await state.clear(); return

    if not receiver_id:
        await message.answer(f"❌ Пользователь {identifier} не найден."); await state.clear(); return
    if receiver_id == sender_id:
        await message.answer("❌ Нельзя переводить себе."); await state.clear(); return

    await state.update_data(receiver_id=receiver_id, receiver_identifier=identifier)
    await message.answer(f"📤 Получатель: {identifier}\n\nВведи сумму (минимум 100):")
    await state.set_state(TransferState.waiting_amount)

@router.message(StateFilter(TransferState.waiting_amount), ~F.text.startswith('/'))
async def transfer_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 100:
            await message.answer("❌ Минимум 100."); return
    except ValueError:
        await message.answer("❌ Сумма должна быть числом."); return

    data = await state.get_data()
    receiver_id, receiver_identifier = data['receiver_id'], data['receiver_identifier']
    success, msg, details = await transfer_coins(message.from_user.id, receiver_id, amount)

    if success:
        sender_balance = await get_balance(message.from_user.id)
        await message.answer(
            f"✅ {msg}\n💸 Отправлено: {amount} рофлов\n🧾 Комиссия (25%): {details['commission']}\n"
            f"📥 {receiver_identifier} получил: {details['receive']}\n💳 Твой баланс: {sender_balance}"
        )
        try:
            await message.bot.send_message(receiver_id,
                f"📥 Вам перевели {details['receive']} рофлов от @{message.from_user.username or 'пользователя'}.\n"
                f"💳 Текущий баланс: {await get_balance(receiver_id)}")
        except Exception as e:
            logger.warning(f"Не удалось уведомить получателя {receiver_id}: {e}")
    else:
        await message.answer(f"❌ {msg}")

    await state.clear()

@router.message(Command("cancel"))
async def cmd_cancel_general(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Действие отменено.")
    else:
        await message.answer("🤷 Нет активного действия.")