"""
Конфигурация бота
Создайте файл .env с переменными:
    BOT_TOKEN=your_telegram_bot_token_here
    SUPPORT_CHAT_ID=-1001234567890
    ADMIN_IDS=123456789,987654321
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ID чата поддержки (группа/супергруппа)
SUPPORT_CHAT_ID = os.getenv("SUPPORT_CHAT_ID", "")

# ID администраторов (через запятую)
ADMIN_IDS: list[int] = [
    int(x.strip()) 
    for x in os.getenv("ADMIN_IDS", "").split(",") 
    if x.strip().isdigit()
]

# Путь к базе данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///support_bot.db")
