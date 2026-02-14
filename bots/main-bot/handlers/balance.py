import os
import asyncpg
import logging
import html
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from shared.database import get_balance, get_user_gender, transfer_coins, get_rofl_id

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
        [InlineKeyboardButton(text="💸 Перевести K-Coin", callback_data="transfer_start")]
    ])

    if gender == "male":
        text = (f"💰 Твой баланс: *{balance} рофлов*\n\n"
                "Не пыль на полке — срофли на скин или кинь братану.\n"
                "💬 Можно также использовать команду: /send @username сумма")
    elif gender == "female":
        text = (f"💰 Твой баланс: *{balance} рофлов*\n\n"
                "Не пыль на полке — срофли на скин или кинь подруге.\n"
                "💬 Можно также использовать команду: /send @username сумма")
    else:
        text = (f"💰 Твой баланс: *{balance} рофлов*\n\n"
                "Не пыль на полке — срофли на скин или кинь кому-нибудь.\n"
                "💬 Можно также использовать команду: /send @username сумма")

    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    logger.info(f"Баланс для {user_id}: {balance}, кнопка отправлена")

@router.callback_query(lambda c: c.data == "transfer_start")
async def transfer_start_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "💸 Введи **получателя** — можно использовать:\n"
        "• @username\n"
        "• Telegram ID (число)\n"
        "• ROFL ID (например, ROFL-0000001)\n\n"
        "_(или отправь /cancel для отмены)_",
        parse_mode="Markdown"
    )
    await state.set_state(TransferState.waiting_identifier)
    await callback.answer()
    logger.info(f"Пользователь {callback.from_user.id} начал перевод, состояние установлено в waiting_identifier")

@router.message(Command("cancel"), StateFilter(TransferState))
async def cmd_cancel_in_transfer(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Перевод отменён.")
    logger.info(f"Пользователь {message.from_user.id} отменил перевод")

@router.message(StateFilter(TransferState.waiting_identifier), F.text.startswith('/'))
@router.message(StateFilter(TransferState.waiting_amount), F.text.startswith('/'))
async def cancel_on_any_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("⏺️ Действие перевода отменено. Введи команду заново.")
    logger.info(f"Пользователь {message.from_user.id} ввёл команду во время перевода, состояние очищено")

@router.message(StateFilter(TransferState.waiting_identifier), ~F.text.startswith('/'))
async def transfer_identifier(message: types.Message, state: FSMContext):
    identifier = message.text.strip()
    sender_id = message.from_user.id
    logger.info(f"📥 [transfer_identifier] Ввод от {sender_id}: '{identifier}'")

    current_state = await state.get_state()
    if current_state != TransferState.waiting_identifier.state:
        logger.warning(f"⚠️ Состояние не совпадает: ожидалось {TransferState.waiting_identifier.state}, получено {current_state}")
        return

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

    await state.update_data(receiver_id=receiver_id, receiver_identifier=identifier)
    try:
        await message.answer(
            f"📤 Получатель: {html.escape(identifier)}\n\n"
            "Введи <b>сумму</b> перевода (минимум 100 рофлов):\n"
            "<i>(отправь /cancel для отмены)</i>",
            parse_mode="HTML"
        )
        await state.set_state(TransferState.waiting_amount)
        logger.info(f"✅ Получатель {identifier} (ID: {receiver_id}) найден, запрос суммы, состояние -> waiting_amount")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке запроса суммы: {e}")
        await state.clear()
        return

@router.message(StateFilter(TransferState.waiting_amount), ~F.text.startswith('/'))
async def transfer_amount(message: types.Message, state: FSMContext):
    sender_id = message.from_user.id
    logger.info(f"📥 [transfer_amount] Ввод суммы от {sender_id}: '{message.text}'")

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

@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("🤷 Нет активного действия для отмены.")
        return
    await state.clear()
    await message.answer("❌ Действие отменено.")
    logger.info(f"Пользователь {message.from_user.id} отменил действие (состояние {current_state})")