"""
Конфигурация бота
Создайте файл .env с переменными:
    BOT_TOKEN=your_telegram_bot_token_here
    OPERATOR_IDS=123456789,987654321
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ID операторов (через запятую в .env)
OPERATOR_IDS: list[int] = [
    int(x.strip()) 
    for x in os.getenv("OPERATOR_IDS", "").split(",") 
    if x.strip().isdigit()
]

# Путь к базе данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///support_bot.db")

# Настройки тикетов
MAX_SUBJECT_LENGTH = 255
MAX_OPEN_TICKETS_PER_USER = 5

