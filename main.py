"""
Telegram Support Bot с тикет-системой
Точка входа
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
from handlers import user_router, operator_router, common_router


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    from config import OPERATOR_IDS
    
    logger.info("Инициализация базы данных...")
    db = get_db()
    await db.init_db()
    logger.info("База данных инициализирована")
    
    # Информация о боте
    bot_info = await bot.get_me()
    logger.info(f"Бот запущен: @{bot_info.username}")
    
    # Проверка операторов
    if OPERATOR_IDS:
        logger.info(f"Операторы: {OPERATOR_IDS}")
    else:
        logger.warning("⚠️ OPERATOR_IDS пуст! Укажите ID операторов в .env")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger.info("Остановка бота...")
    db = get_db()
    await db.close()
    logger.info("Бот остановлен")


async def main():
    """Главная функция запуска бота"""
    
    # Проверка токена
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен! Создайте файл .env с токеном бота.")
        sys.exit(1)
    
    # Создание бота и диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Используем memory storage для FSM
    # В продакшене лучше использовать RedisStorage
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутеров
    # Порядок важен! common_router должен быть первым для обработки /start и /help
    dp.include_router(common_router)
    dp.include_router(operator_router)
    dp.include_router(user_router)
    
    # Регистрация событий startup/shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запуск polling
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

