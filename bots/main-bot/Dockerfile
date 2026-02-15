FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN ls -la /app
RUN ls -la /app/bots/main-bot || echo "Папка bots/main-bot не найдена"
WORKDIR /app/bots/main-bot
CMD ["python", "bot.py"]