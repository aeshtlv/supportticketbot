"""
Подключение к базе данных
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import DATABASE_URL
from database.models import Base


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, url: str = DATABASE_URL):
        self.engine = create_async_engine(url, echo=False)
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def init_db(self):
        """Инициализация БД - создание таблиц"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def close(self):
        """Закрытие соединения"""
        await self.engine.dispose()


# Глобальный экземпляр
_db: Database | None = None


def get_db() -> Database:
    """Получить экземпляр базы данных"""
    global _db
    if _db is None:
        _db = Database()
    return _db
