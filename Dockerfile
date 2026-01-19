FROM python:3.11-slim

# Метаданные
LABEL maintainer="Support Bot"
LABEL description="Telegram Support Bot with Ticket System"

# Переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Рабочая директория
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаём директорию для данных (БД)
RUN mkdir -p /app/data

# Запуск бота
CMD ["python", "main.py"]

