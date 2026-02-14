FROM python:3.11-slim

WORKDIR /app

# Копируем файл с зависимостями и устанавливаем их
COPY bots/main-bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект (включая shared и bots)
COPY . .

# Устанавливаем рабочую директорию для запуска бота
WORKDIR /app/bots/main-bot

# Запускаем бота
CMD ["python", "bot.py"]