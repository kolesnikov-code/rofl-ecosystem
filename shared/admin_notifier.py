import logging
import html
from datetime import datetime
from aiogram import Bot
from config import BOT_TOKEN, ADMIN_CHANNEL_ID

bot = Bot(token=BOT_TOKEN)
logger = logging.getLogger(__name__)


async def notify_new_user(telegram_id: int, eco_id: str, username: str, first_name: str, last_name: str,
                          gender: str = None, balance: int = 0):
    try:
        safe_username = html.escape(username)
        safe_first = html.escape(first_name)
        safe_last = html.escape(last_name)
        safe_eco_id = html.escape(eco_id)

        gender_text = {
            "male": "🧔 Мужской",
            "female": "👩 Женский",
            "other": "🤖 Другой / не указан"
        }.get(gender, "❓ Не указан")

        text = (
            f"🆕 <b>Новый пользователь!</b>\n\n"
            f"• <b>Eco ID:</b> <code>{safe_eco_id}</code>\n"
            f"• <b>Telegram ID:</b> <code>{telegram_id}</code>\n"
            f"• <b>Username:</b> @{safe_username}\n"
            f"• <b>Имя:</b> {safe_first} {safe_last}\n"
            f"• <b>Пол:</b> {gender_text}\n"
            f"• <b>Баланс:</b> {balance} рофлов\n"
            f"• <b>Дата регистрации:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        await bot.send_message(chat_id=ADMIN_CHANNEL_ID, text=text, parse_mode="HTML")
        logger.info(f"✅ Уведомление отправлено в канал для пользователя {telegram_id} (Eco ID: {eco_id})")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления в канал: {e}")

async def notify_channel_subscription(
    telegram_id: int,
    username: str,
    first_name: str,
    last_name: str,
    channel_name: str,
    channel_username: str,
    action: str,
    emoji: str = "✅"
):
    try:
        safe_username = html.escape(username)
        safe_first = html.escape(first_name)
        safe_last = html.escape(last_name)
        safe_channel = html.escape(channel_name)

        text = (
            f"{emoji} <b>Канал: {safe_channel}</b>\n"
            f"{channel_username}\n\n"
            f"👤 <b>Пользователь {action}</b>\n"
            f"• <b>Telegram ID:</b> <code>{telegram_id}</code>\n"
            f"• <b>Username:</b> @{safe_username}\n"
            f"• <b>Имя:</b> {safe_first} {safe_last}\n"
            f"• <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )

        await bot.send_message(
            chat_id=ADMIN_CHANNEL_ID,
            text=text,
            parse_mode="HTML"
        )
        logger.info(f"📢 Уведомление о {action.lower()} на канал {channel_username} от {telegram_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления о подписке: {e}")