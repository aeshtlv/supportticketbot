"""
Telegram Support Bot
Система пересылки сообщений с Reply в групповой чат
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import get_db
from handlers import user_router, support_router, admin_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Действия при запуске"""
    from config import SUPPORT_CHAT_ID, ADMIN_IDS
    
    logger.info("Инициализация базы данных...")
    db = get_db()
    await db.init_db()
    logger.info("База данных инициализирована")
    
    bot_info = await bot.get_me()
    logger.info(f"Бот запущен: @{bot_info.username}")
    logger.info(f"SUPPORT_CHAT_ID: {SUPPORT_CHAT_ID}")
    logger.info(f"ADMIN_IDS: {ADMIN_IDS}")
    
    # Проверяем доступ к чату поддержки
    if SUPPORT_CHAT_ID:
        try:
            chat = await bot.get_chat(SUPPORT_CHAT_ID)
            logger.info(f"Support chat: {chat.title} (ID: {chat.id})")
        except Exception as e:
            logger.error(f"Cannot access support chat: {e}")


async def on_shutdown(bot: Bot):
    """Действия при остановке"""
    logger.info("Остановка бота...")
    db = get_db()
    await db.close()
    logger.info("Бот остановлен")


async def main():
    """Главная функция"""
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен! Создайте файл .env с токеном бота.")
        sys.exit(1)
    
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутеров (порядок важен!)
    # Сначала админ, потом пользователи, потом поддержка (чтобы поддержка не перехватывала все)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    dp.include_router(support_router)
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    logger.info("Запуск бота...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
