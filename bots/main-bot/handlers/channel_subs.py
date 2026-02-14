from aiogram import Router, Bot
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.types import ChatMemberUpdated
import logging
from config import ADMIN_CHANNEL_ID
from config_channels import CHANNEL_DICT
from shared.admin_notifier import notify_channel_subscription

router = Router()
logger = logging.getLogger(__name__)

@router.chat_member(
    ChatMemberUpdatedFilter(
        member_status_changed=(
            IS_NOT_MEMBER >> IS_MEMBER,  # подписался
            IS_MEMBER >> IS_NOT_MEMBER   # отписался
        )
    )
)
async def on_channel_subscription(event: ChatMemberUpdated, bot: Bot):
    """
    Отслеживает ПОДПИСКУ и ОТПИСКУ пользователей на каналы,
    где бот является АДМИНИСТРАТОРОМ.
    """
    chat = event.chat
    user = event.from_user
    old_status = event.old_chat_member
    new_status = event.new_chat_member

    # --- 1. Проверяем, является ли чат одним из наших каналов ---
    channel_username = chat.username
    if channel_username:
        channel_username = f"@{channel_username}"
        display_name = CHANNEL_DICT.get(channel_username)
    else:
        display_name = None

    if not display_name:
        # Игнорируем чужие каналы
        return

    # --- 2. Определяем тип события ---
    was_member = old_status.is_chat_member()
    is_member_now = new_status.is_chat_member()

    if not was_member and is_member_now:
        action = "ПОДПИСАЛСЯ"
        emoji = "✅"
    elif was_member and not is_member_now:
        action = "ОТПИСАЛСЯ"
        emoji = "❌"
    else:
        return

    # --- 3. Отправляем уведомление в админ-канал ---
    await notify_channel_subscription(
        telegram_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        channel_name=display_name,
        channel_username=channel_username,
        action=action,
        emoji=emoji
    )