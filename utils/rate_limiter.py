"""
Защита от спама - rate limiting
"""
import asyncio
import time
from collections import defaultdict
from typing import Dict, Tuple


class RateLimiter:
    """Rate limiter для защиты от спама"""
    
    def __init__(self, max_messages: int = 5, time_window: int = 60):
        """
        Args:
            max_messages: Максимальное количество сообщений
            time_window: Временное окно в секундах
        """
        self.max_messages = max_messages
        self.time_window = time_window
        self.user_messages: Dict[int, list[float]] = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def check_rate_limit(self, user_id: int) -> Tuple[bool, int]:
        """
        Проверяет, не превышен ли лимит сообщений
        
        Returns:
            (is_allowed, wait_seconds)
        """
        async with self.lock:
            now = time.time()
            messages = self.user_messages[user_id]
            
            # Удаляем старые сообщения (старше time_window)
            messages[:] = [msg_time for msg_time in messages if now - msg_time < self.time_window]
            
            if len(messages) >= self.max_messages:
                # Превышен лимит
                oldest_message = min(messages)
                wait_seconds = int(self.time_window - (now - oldest_message)) + 1
                return False, wait_seconds
            
            # Добавляем текущее сообщение
            messages.append(now)
            return True, 0
    
    async def reset_user(self, user_id: int):
        """Сбросить счётчик для пользователя"""
        async with self.lock:
            if user_id in self.user_messages:
                del self.user_messages[user_id]


# Глобальный экземпляр
rate_limiter = RateLimiter(max_messages=5, time_window=60)

