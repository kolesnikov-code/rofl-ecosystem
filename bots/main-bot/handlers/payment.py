from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import LabeledPrice, PreCheckoutQuery
from shared.database import update_balance, add_transaction

router = Router()

# Курс: 1 Star = 1.5 рофла (бонус за покупку)
STAR_TO_ROFL = 1.5

@router.message(Command("buy"))
async def cmd_buy(message: types.Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "❓ Используй: `/buy [количество рофлов]`\n"
            "Например: `/buy 1000`",
            parse_mode="Markdown"
        )
        return

    try:
        rofl_amount = int(args[1])
        if rofl_amount < 100:
            await message.answer("❌ Минимальная сумма — 100 рофлов.")
            return
    except ValueError:
        await message.answer("❌ Сумма должна быть числом.")
        return

    stars = int(rofl_amount / STAR_TO_ROFL)
    if stars < 1:
        stars = 1
        rofl_amount = int(stars * STAR_TO_ROFL)

    prices = [LabeledPrice(label="XTR", amount=stars)]

    await message.answer_invoice(
        title="Покупка рофлов",
        description=f"💰 {rofl_amount} рофлов за {stars} ⭐️",
        payload=f"rofl_{rofl_amount}",
        currency="XTR",
        prices=prices,
        reply_markup=None
    )

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout: PreCheckoutQuery):
    await pre_checkout.answer(ok=True)

@router.message(lambda message: message.successful_payment is not None)
async def payment_success(message: types.Message):
    payment = message.successful_payment
    user_id = message.from_user.id
    payload = payment.invoice_payload

    if payload.startswith("rofl_"):
        rofl_amount = int(payload.split("_")[1])
        stars_spent = payment.total_amount

        await update_balance(user_id, rofl_amount)
        await add_transaction(
            user_id,
            rofl_amount,
            "purchase",
            f"Куплено за {stars_spent} ⭐️"
        )

        await message.answer(
            f"✅ Оплата прошла!\n"
            f"💰 На твой счёт зачислено **{rofl_amount} рофлов**.\n"
            f"Спасибо за поддержку! 🤝",
            parse_mode="Markdown"
        )