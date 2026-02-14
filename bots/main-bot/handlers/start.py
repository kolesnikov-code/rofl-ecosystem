from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from shared.database import (
    add_user, get_balance, set_user_gender, get_user_gender,
    register_referral, get_ref_code
)
import os
import asyncpg
import logging

router = Router()
logger = logging.getLogger(__name__)

class GenderState(StatesGroup):
    waiting_gender = State()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user = message.from_user
    telegram_id = user.id
    username = user.username or ""
    first_name = user.first_name or ""
    last_name = user.last_name or ""

    args = message.text.split()
    referrer_code = None
    if len(args) > 1:
        param = args[1]
        if param.startswith("ref_"):
            referrer_code = param[4:]

    existing_gender = await get_user_gender(telegram_id)
    if existing_gender:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if DATABASE_URL:
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                await conn.execute(
                    "UPDATE users SET username = $1 WHERE telegram_id = $2",
                    username, telegram_id
                )
            finally:
                await conn.close()
        balance = await get_balance(telegram_id)
        await message.answer(
            f"👋 С возвращением, {first_name}!\n"
            f"💰 Твой баланс: {balance} рофлов.\n\n"
            f"📌 /catalog — все проекты\n"
            f"🎁 /daily — ежедневный бонус\n"
            f"💸 /send — перевести рофлы\n"
            f"🔗 /ref — реферальная ссылка"
        )
        return

    eco_id = await add_user(telegram_id, username, first_name, last_name)

    await state.update_data(
        telegram_id=telegram_id,
        eco_id=eco_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        referrer_code=referrer_code
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧔 Мужской", callback_data="gender_male")],
        [InlineKeyboardButton(text="👩 Женский", callback_data="gender_female")],
        [InlineKeyboardButton(text="🤖 Другой / Не скажу", callback_data="gender_other")]
    ])

    await message.answer(
        "👋 Привет! Мы уважаем твой пол — так бот будет общаться с тобой корректно.\n\n"
        "**Выбери вариант:**",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await state.set_state(GenderState.waiting_gender)

@router.callback_query(GenderState.waiting_gender, F.data.startswith("gender_"))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    gender_code = callback.data.split("_")[1]
    data = await state.get_data()

    telegram_id = data['telegram_id']
    eco_id = data['eco_id']
    username = data['username']
    first_name = data['first_name']
    last_name = data['last_name']
    referrer_code = data.get('referrer_code')

    await set_user_gender(telegram_id, gender_code)

    if referrer_code:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if DATABASE_URL:
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                row = await conn.fetchrow(
                    "SELECT telegram_id FROM users WHERE ref_code = $1", referrer_code
                )
                if row and row[0] != telegram_id:
                    referrer_id = row[0]
                    await register_referral(referrer_id, telegram_id)
            finally:
                await conn.close()

    balance = await get_balance(telegram_id)

    if gender_code == "male":
        welcome_text = (
            f"✅ Отлично, брат! Ты зарегистрирован в системе **ROFL**.\n\n"
            f"💰 На твой счёт залетело **{balance} рофлов** — не профукай.\n"
            f"🆔 Твой ROFL ID: `{eco_id}`\n"
            f"📌 Команда /balance покажет твою заначку.\n"
            f"🎁 Каждый день забирай /daily — серия увеличивает бонус.\n"
            f"🔗 Приглашай друзей — /ref\n\n"
            f"Го смотреть, что тут есть → /catalog"
        )
    elif gender_code == "female":
        welcome_text = (
            f"✅ Отлично, сестрёнка! Ты зарегистрирована в системе **ROFL**.\n\n"
            f"💰 На твой счёт залетело **{balance} рофлов** — не профукай.\n"
            f"🆔 Твой ROFL ID: `{eco_id}`\n"
            f"📌 Команда /balance покажет твою заначку.\n"
            f"🎁 Каждый день забирай /daily — серия увеличивает бонус.\n"
            f"🔗 Приглашай друзей — /ref\n\n"
            f"Го смотреть, что тут есть → /catalog"
        )
    else:
        welcome_text = (
            f"✅ Принято! Ты зарегистрирован(а) в системе **ROFL**.\n\n"
            f"💰 На твой счёт залетело **{balance} рофлов** — не профукай.\n"
            f"🆔 Твой ROFL ID: `{eco_id}`\n"
            f"📌 Команда /balance покажет твою заначку.\n"
            f"🎁 Каждый день забирай /daily — серия увеличивает бонус.\n"
            f"🔗 Приглашай друзей — /ref\n\n"
            f"Го смотреть, что тут есть → /catalog"
        )

    await callback.message.edit_text(welcome_text, parse_mode="Markdown")
    await callback.answer()

    from shared.admin_notifier import notify_new_user
    await notify_new_user(
        telegram_id=telegram_id,
        eco_id=eco_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        gender=gender_code,
        balance=balance
    )

    await state.clear()