import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHANNEL_ID = os.getenv("ADMIN_CHANNEL_ID")

if not BOT_TOKEN or not ADMIN_CHANNEL_ID:
    raise ValueError("❌ BOT_TOKEN или ADMIN_CHANNEL_ID не заданы в .env")