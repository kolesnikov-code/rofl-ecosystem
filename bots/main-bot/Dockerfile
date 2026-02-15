FROM python:3.11-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN ls -la /app
RUN ls -la /bots/main-bot || echo "Папка bots/main-bot не найдена"
WORKDIR /bots/main-bot
CMD ["python", "bot.py"]