FROM python:3.11-slim
WORKDIR /app
COPY bots/main-bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
WORKDIR /app/bots/main-bot
CMD ["python", "bot.py"]