import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import logging
import asyncpg
import html
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from shared.database import transfer_coins, get_balance

router = Router()
logger = logging.getLogger(__name__)

class SendState(StatesGroup):
    waiting_identifier = State()
    waiting_amount = State()

@router.message(Command("send"))
async def cmd_send(message: types.Message, state: FSMContext):
    args = message.text.split()
    if len(args) == 3:
        await quick_send(message)
        return
    await state.set_state(SendState.waiting_identifier)
    await message.answer(
        "💸 Введи получателя (@username, Telegram ID или ROFL ID):\n_(отправь /cancel для отмены)_",
        parse_mode="Markdown"
    )

async def quick_send(message: types.Message):
    args = message.text.split()
    target = args[1]
    try:
        amount = int(args[2])
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Сумма должна быть положительным числом.")
        return

    sender_id = message.from_user.id
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        await message.answer("❌ Ошибка БД.")
        return

    receiver_id = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            if target.startswith('@'):
                clean = target[1:]
                row = await conn.fetchrow("SELECT telegram_id FROM users WHERE username ILIKE $1", clean)
                if row:
                    receiver_id = row[0]
            elif target.startswith('ROFL-') or target.startswith('KLM_'):
                row = await conn.fetchrow("SELECT telegram_id FROM users WHERE eco_id = $1", target)
                if row:
                    receiver_id = row[0]
            elif target.isdigit():
                tg_id = int(target)
                row = await conn.fetchrow("SELECT telegram_id FROM users WHERE telegram_id = $1", tg_id)
                if row:
                    receiver_id = row[0]
            else:
                await message.answer("❌ Неверный формат получателя.")
                return
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}")
        await message.answer("❌ Ошибка при поиске получателя.")
        return

    if not receiver_id:
        await message.answer(f"❌ Получатель {target} не найден.")
        return
    if receiver_id == sender_id:
        await message.answer("❌ Нельзя переводить себе.")
        return

    success, msg, details = await transfer_coins(sender_id, receiver_id, amount)
    if success:
        sender_balance = await get_balance(sender_id)
        receiver_balance = await get_balance(receiver_id)
        await message.answer(
            f"✅ {msg}\n\n"
            f"💸 Отправлено: {amount} рофлов\n"
            f"🧾 Комиссия (25%): {details['commission']}\n"
            f"📥 {target} получил: {details['receive']}\n"
            f"💳 Твой баланс: {sender_balance}"
        )
        try:
            await message.bot.send_message(receiver_id,
                f"📥 Вам перевели {details['receive']} рофлов от @{message.from_user.username or 'пользователя'}.\n"
                f"💳 Текущий баланс: {receiver_balance}")
        except Exception as e:
            logger.warning(f"Не удалось уведомить {receiver_id}: {e}")
    else:
        await message.answer(f"❌ {msg}")

# ---------- Пошаговый ввод ----------
@router.message(SendState.waiting_identifier, ~F.text.startswith('/'))
async def send_identifier(message: types.Message, state: FSMContext):
    identifier = message.text.strip()
    sender_id = message.from_user.id
    logger.info(f"📥 Ввод получателя: {identifier}")

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        await message.answer("❌ Ошибка БД.")
        await state.clear()
        return

    receiver_id = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            if identifier.startswith('@'):
                clean = identifier[1:].strip()
                row = await conn.fetchrow("SELECT telegram_id FROM users WHERE username ILIKE $1", clean)
                if row:
                    receiver_id = row[0]
            elif identifier.startswith('ROFL-') or identifier.startswith('KLM_'):
                row = await conn.fetchrow("SELECT telegram_id FROM users WHERE eco_id = $1", identifier)
                if row:
                    receiver_id = row[0]
            elif identifier.isdigit():
                row = await conn.fetchrow("SELECT telegram_id FROM users WHERE telegram_id = $1", int(identifier))
                if row:
                    receiver_id = row[0]
            else:
                await message.answer("❌ Неверный формат.")
                return
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Ошибка БД: {e}")
        await message.answer("❌ Ошибка поиска.")
        await state.clear()
        return

    if not receiver_id:
        await message.answer(f"❌ Пользователь {identifier} не найден.")
        await state.clear()
        return
    if receiver_id == sender_id:
        await message.answer("❌ Нельзя переводить себе.")
        await state.clear()
        return

    await state.update_data(receiver_id=receiver_id, receiver_identifier=identifier)
    await message.answer(f"📤 Получатель: {identifier}\n\nВведи сумму (минимум 100):")
    await state.set_state(SendState.waiting_amount)

@router.message(SendState.waiting_amount, ~F.text.startswith('/'))
async def send_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 100:
            await message.answer("❌ Минимум 100.")
            return
    except ValueError:
        await message.answer("❌ Сумма должна быть числом.")
        return

    data = await state.get_data()
    receiver_id, receiver_identifier = data['receiver_id'], data['receiver_identifier']
    success, msg, details = await transfer_coins(message.from_user.id, receiver_id, amount)
    if success:
        sender_balance = await get_balance(message.from_user.id)
        await message.answer(
            f"✅ {msg}\n\n"
            f"💸 Отправлено: {amount} рофлов\n"
            f"🧾 Комиссия (25%): {details['commission']}\n"
            f"📥 {receiver_identifier} получил: {details['receive']}\n"
            f"💳 Твой баланс: {sender_balance}"
        )
        try:
            await message.bot.send_message(receiver_id,
                f"📥 Вам перевели {details['receive']} рофлов от @{message.from_user.username or 'пользователя'}.\n"
                f"💳 Текущий баланс: {await get_balance(receiver_id)}")
        except Exception as e:
            logger.warning(f"Не удалось уведомить {receiver_id}: {e}")
    else:
        await message.answer(f"❌ {msg}")

    await state.clear()

@router.message(Command("cancel"), StateFilter(SendState))
async def cancel_send(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Перевод отменён.")