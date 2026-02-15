import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery
from shared.database import update_balance, add_transaction

router = Router()
STAR_TO_ROFL = 1.5

@router.message(Command("buy"))
async def cmd_buy(message: types.Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❓ Используй: /buy [сумма]")
        return
    try:
        rofl_amount = int(args[1])
        if rofl_amount < 100:
            await message.answer("❌ Минимум 100.")
            return
    except ValueError:
        await message.answer("❌ Сумма должна быть числом.")
        return
    stars = max(1, int(rofl_amount / STAR_TO_ROFL))
    rofl_amount = int(stars * STAR_TO_ROFL)
    await message.answer_invoice(
        title="Покупка рофлов",
        description=f"💰 {rofl_amount} рофлов за {stars} ⭐️",
        payload=f"rofl_{rofl_amount}",
        currency="XTR",
        prices=[LabeledPrice(label="XTR", amount=stars)]
    )

@router.pre_checkout_query()
async def pre_checkout_handler(q: PreCheckoutQuery):
    await q.answer(ok=True)

@router.message(lambda m: m.successful_payment)
async def payment_success(message: types.Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("rofl_"):
        rofl_amount = int(payload.split("_")[1])
        await update_balance(message.from_user.id, rofl_amount)
        await add_transaction(message.from_user.id, rofl_amount, "purchase", "Покупка")
        await message.answer(f"✅ Оплата прошла! Зачислено **{rofl_amount} рофлов**.", parse_mode="Markdown")