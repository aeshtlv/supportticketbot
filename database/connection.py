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
        """Инициализация БД - создание таблиц и миграции"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Миграции для добавления новых колонок
        await self._migrate_db()
    
    async def _migrate_db(self):
        """Выполняет миграции базы данных"""
        async with self.engine.begin() as conn:
            # Проверяем и добавляем колонку is_banned если её нет
            try:
                await conn.execute(
                    "ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT 0"
                )
            except Exception:
                # Колонка уже существует, пропускаем
                pass
            
            # Проверяем и добавляем другие колонки если нужно
            try:
                await conn.execute(
                    "ALTER TABLE tickets ADD COLUMN topic_id INTEGER"
                )
            except Exception:
                pass
            
            try:
                await conn.execute(
                    "ALTER TABLE message_links ADD COLUMN topic_id INTEGER"
                )
            except Exception:
                pass
    
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
