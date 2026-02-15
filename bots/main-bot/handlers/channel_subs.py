from aiogram import Router, types, Bot
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.types import ChatMemberUpdated
import logging
from datetime import datetime
from ..config import ADMIN_CHANNEL_ID
from ..config_channels import CHANNEL_DICT
from shared.admin_notifier import notify_channel_subscription

router = Router()
logger = logging.getLogger(__name__)

@router.chat_member(
    ChatMemberUpdatedFilter(
        member_status_changed=(IS_NOT_MEMBER >> IS_MEMBER, IS_MEMBER >> IS_NOT_MEMBER)
    )
)
async def on_channel_subscription(event: ChatMemberUpdated, bot: Bot):
    chat = event.chat
    user = event.from_user
    old, new = event.old_chat_member, event.new_chat_member
    channel_username = f"@{chat.username}" if chat.username else None
    display_name = CHANNEL_DICT.get(channel_username) if channel_username else None
    if not display_name:
        return

    was = old.is_chat_member()
    now = new.is_chat_member()
    if not was and now:
        action, emoji = "ПОДПИСАЛСЯ", "✅"
    elif was and not now:
        action, emoji = "ОТПИСАЛСЯ", "❌"
    else:
        return

    await notify_channel_subscription(
        telegram_id=user.id, username=user.username or "",
        first_name=user.first_name or "", last_name=user.last_name or "",
        channel_name=display_name, channel_username=channel_username,
        action=action, emoji=emoji
    )