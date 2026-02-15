import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

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

# Состояния для перевода
class SendState(StatesGroup):
    waiting_identifier = State()
    waiting_amount = State()

@router.message(Command("send"))
async def cmd_send(message: types.Message, state: FSMContext):
    args = message.text.split()
    # Если есть аргументы, пробуем быстрый перевод
    if len(args) == 3:
        await quick_send(message)
        return
    # Иначе запускаем пошаговый диалог
    await state.set_state(SendState.waiting_identifier)
    await message.answer(
        "💸 Введи **получателя** — можно использовать:\n"
        "• @username\n"
        "• Telegram ID (число)\n"
        "• ROFL ID (например, ROFL-0000001)\n\n"
        "_(или отправь /cancel для отмены)_",
        parse_mode="Markdown"
    )

async def quick_send(message: types.Message):
    """Быстрый перевод в формате /send @username сумма"""
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
        await message.answer("❌ Ошибка конфигурации базы данных.")
        return

    receiver_id = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            if target.startswith('@'):
                clean = target[1:]
                row = await conn.fetchrow(
                    "SELECT telegram_id FROM users WHERE username ILIKE $1", clean
                )
                if row:
                    receiver_id = row[0]
            elif target.startswith('ROFL-') or target.startswith('KLM_'):
                row = await conn.fetchrow(
                    "SELECT telegram_id FROM users WHERE eco_id = $1", target
                )
                if row:
                    receiver_id = row[0]
            elif target.isdigit():
                tg_id = int(target)
                row = await conn.fetchrow(
                    "SELECT telegram_id FROM users WHERE telegram_id = $1", tg_id
                )
                if row:
                    receiver_id = row[0]
            else:
                await message.answer("❌ Неверный формат получателя.")
                return
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Ошибка поиска получателя: {e}")
        await message.answer("❌ Ошибка при поиске получателя.")
        return

    if not receiver_id:
        await message.answer(f"❌ Получатель {target} не найден в экосистеме.")
        return
    if receiver_id == sender_id:
        await message.answer("❌ Нельзя переводить самому себе.")
        return

    success, msg, details = await transfer_coins(sender_id, receiver_id, amount)

    if success:
        sender_balance = await get_balance(sender_id)
        receiver_balance = await get_balance(receiver_id)
        await message.answer(
            f"✅ {msg}\n\n"
            f"💸 Отправлено: {amount} рофлов\n"
            f"🧾 Комиссия (25%): {details['commission']} рофлов (сожжена)\n"
            f"📥 {target} получил: {details['receive']} рофлов\n"
            f"💳 Твой баланс: {sender_balance} рофлов"
        )
        try:
            await message.bot.send_message(
                receiver_id,
                f"📥 Вам перевели {details['receive']} рофлов от @{message.from_user.username or 'пользователя'}.\n"
                f"💳 Текущий баланс: {receiver_balance} рофлов"
            )
            logger.info(f"✅ Уведомление отправлено получателю {receiver_id}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось уведомить получателя {receiver_id}: {e}")
    else:
        await message.answer(f"❌ {msg}")

# ---------- Пошаговый ввод получателя ----------
@router.message(SendState.waiting_identifier, ~F.text.startswith('/'))
async def send_identifier(message: types.Message, state: FSMContext):
    identifier = message.text.strip()
    sender_id = message.from_user.id
    logger.info(f"📥 [send_identifier] Ввод от {sender_id}: '{identifier}'")

    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL не установлен!")
        await message.answer("❌ Ошибка конфигурации базы данных. Попробуй позже.")
        await state.clear()
        return

    receiver_id = None
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            if identifier.startswith('@'):
                clean = identifier[1:].strip()
                row = await conn.fetchrow(
                    "SELECT telegram_id FROM users WHERE username ILIKE $1", clean
                )
                if row:
                    receiver_id = row[0]
                    logger.info(f"✅ Найден пользователь по username: ID {receiver_id}")

            elif identifier.startswith('ROFL-') or identifier.startswith('KLM_'):
                row = await conn.fetchrow(
                    "SELECT telegram_id FROM users WHERE eco_id = $1", identifier
                )
                if row:
                    receiver_id = row[0]
                    logger.info(f"✅ Найден пользователь по ROFL ID: ID {receiver_id}")

            elif identifier.isdigit():
                tg_id = int(identifier)
                row = await conn.fetchrow(
                    "SELECT telegram_id FROM users WHERE telegram_id = $1", tg_id
                )
                if row:
                    receiver_id = row[0]
                    logger.info(f"✅ Найден пользователь по Telegram ID: ID {receiver_id}")

            else:
                logger.warning(f"❌ Неверный формат идентификатора: {identifier}")
                await message.answer(
                    "❌ Неверный формат.\n"
                    "Используй:\n"
                    "• @username\n"
                    "• Telegram ID (только цифры)\n"
                    "• ROFL ID (например, ROFL-0000001)"
                )
                return
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"❌ Ошибка БД при поиске получателя {identifier}: {e}")
        await message.answer("❌ Ошибка при поиске пользователя. Попробуй позже.")
        await state.clear()
        return

    if not receiver_id:
        logger.warning(f"❌ Пользователь {identifier} не найден в БД")
        await message.answer(f"❌ Пользователь {identifier} не найден в экосистеме.")
        await state.clear()
        return

    if receiver_id == sender_id:
        logger.warning(f"❌ Попытка перевода самому себе: {sender_id}")
        await message.answer("❌ Нельзя переводить самому себе.")
        await state.clear()
        return

    # Сохраняем данные и запрашиваем сумму — используем HTML, экранируем identifier
    await state.update_data(receiver_id=receiver_id, receiver_identifier=identifier)
    try:
        await message.answer(
            f"📤 Получатель: {html.escape(identifier)}\n\n"
            "Введи <b>сумму</b> перевода (минимум 100 рофлов):\n"
            "<i>(отправь /cancel для отмены)</i>",
            parse_mode="HTML"
        )
        await state.set_state(SendState.waiting_amount)
        logger.info(f"✅ Получатель {identifier} (ID: {receiver_id}) найден, запрос суммы, состояние -> waiting_amount")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке запроса суммы: {e}")
        await state.clear()
        return

# ---------- Ввод суммы ----------
@router.message(SendState.waiting_amount, ~F.text.startswith('/'))
async def send_amount(message: types.Message, state: FSMContext):
    sender_id = message.from_user.id
    logger.info(f"📥 [send_amount] Ввод суммы от {sender_id}: '{message.text}'")

    try:
        amount = int(message.text)
        if amount < 100:
            await message.answer("❌ Минимальная сумма — 100 рофлов.")
            return
    except ValueError:
        await message.answer("❌ Сумма должна быть числом.")
        return

    data = await state.get_data()
    receiver_id = data['receiver_id']
    receiver_identifier = data['receiver_identifier']

    success, msg, details = await transfer_coins(sender_id, receiver_id, amount)

    if success:
        sender_balance = await get_balance(sender_id)
        await message.answer(
            f"✅ {msg}\n\n"
            f"💸 Отправлено: {amount} рофлов\n"
            f"🧾 Комиссия (25%): {details['commission']} рофлов (сожжена)\n"
            f"📥 {html.escape(receiver_identifier)} получил: {details['receive']} рофлов\n"
            f"💳 Твой баланс: {sender_balance} рофлов"
        )
        try:
            await message.bot.send_message(
                receiver_id,
                f"📥 Вам перевели {details['receive']} рофлов от @{message.from_user.username or 'пользователя'}.\n"
                f"💳 Текущий баланс: {await get_balance(receiver_id)} рофлов"
            )
            logger.info(f"✅ Уведомление отправлено получателю {receiver_id}")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось уведомить получателя {receiver_id}: {e}")
    else:
        await message.answer(f"❌ {msg}")

    await state.clear()
    logger.info(f"💰 Перевод от {sender_id} к {receiver_id} на сумму {amount} завершён")

# ---------- Отмена ----------
@router.message(Command("cancel"), StateFilter(SendState))
async def cancel_send(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Перевод отменён.")