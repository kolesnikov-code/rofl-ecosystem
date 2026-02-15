import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from aiogram import Router, types, Bot
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER
from aiogram.types import ChatMemberUpdated
import logging
from datetime import datetime
from config import ADMIN_CHANNEL_ID
from config_channels import CHANNEL_DICT
from shared.admin_notifier import notify_channel_subscription

router = Router()
logger = logging.getLogger(__name__)

@router.chat_member(
    ChatMemberUpdatedFilter(
        member_status_changed=(
            IS_NOT_MEMBER >> IS_MEMBER,
            IS_MEMBER >> IS_NOT_MEMBER
        )
    )
)
async def on_channel_subscription(event: ChatMemberUpdated, bot: Bot):
    chat = event.chat
    user = event.from_user
    old_status = event.old_chat_member
    new_status = event.new_chat_member

    channel_username = chat.username
    if channel_username:
        channel_username = f"@{channel_username}"
        display_name = CHANNEL_DICT.get(channel_username)
    else:
        display_name = None

    if not display_name:
        return

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