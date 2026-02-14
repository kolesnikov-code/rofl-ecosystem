import os
import asyncpg
import logging
import secrets
from datetime import datetime, timedelta

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ CRITICAL: DATABASE_URL environment variable is not set!")

async def init_db():
    """Создаёт таблицы и индексы."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                eco_id TEXT UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TIMESTAMP DEFAULT NOW(),
                balance INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
                daily_streak INTEGER DEFAULT 0,
                gender TEXT DEFAULT NULL,
                ref_code TEXT UNIQUE
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                amount INTEGER NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                related_id INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id SERIAL PRIMARY KEY,
                referrer_id BIGINT NOT NULL,
                referred_id BIGINT NOT NULL,
                level INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        # Индексы
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_telegram_id ON users(telegram_id)")
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_eco_id ON users(eco_id)")
        await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ref_code ON users(ref_code)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referred ON referrals(referred_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)")

        logging.info("✅ База данных PostgreSQL инициализирована")
    finally:
        await conn.close()

# ---------- Работа с пользователями ----------
async def generate_eco_id(conn) -> str:
    """Генерирует новый Eco ID в формате ROFL-0000001."""
    count = await conn.fetchval("SELECT COUNT(*) FROM users")
    next_id = (count or 0) + 1
    return f"ROFL-{next_id:07d}"

async def add_user(telegram_id: int, username: str, first_name: str, last_name: str) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow("SELECT eco_id FROM users WHERE telegram_id = $1", telegram_id)
        if row:
            return row[0]

        eco_id = await generate_eco_id(conn)
        await conn.execute(
            "INSERT INTO users (telegram_id, eco_id, username, first_name, last_name, balance) VALUES ($1, $2, $3, $4, $5, $6)",
            telegram_id, eco_id, username, first_name, last_name, 200
        )
        await add_transaction(telegram_id, 200, "welcome", "Бонус за регистрацию")
        return eco_id
    finally:
        await conn.close()

async def get_balance(telegram_id: int) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow("SELECT COALESCE(balance, 0) FROM users WHERE telegram_id = $1", telegram_id)
        return row[0] if row else 0
    finally:
        await conn.close()

async def update_balance(telegram_id: int, delta: int) -> int:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(
            "UPDATE users SET balance = COALESCE(balance, 0) + $1 WHERE telegram_id = $2",
            delta, telegram_id
        )
        row = await conn.fetchrow("SELECT COALESCE(balance, 0) FROM users WHERE telegram_id = $1", telegram_id)
        return row[0]
    finally:
        await conn.close()

async def get_eco_id(telegram_id: int) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow("SELECT eco_id FROM users WHERE telegram_id = $1", telegram_id)
        return row[0] if row else None
    finally:
        await conn.close()

# ---------- Функция для получения ROFL ID (псевдоним для get_eco_id) ----------
async def get_rofl_id(telegram_id: int) -> str:
    """Возвращает ROFL ID пользователя (то же самое, что eco_id)."""
    return await get_eco_id(telegram_id)

# ---------- Транзакции ----------
async def add_transaction(telegram_id: int, amount: int, type_: str, description: str = "", related_id: int = None):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(
            "INSERT INTO transactions (user_id, amount, type, description, related_id) VALUES ($1, $2, $3, $4, $5)",
            telegram_id, amount, type_, description, related_id
        )
    finally:
        await conn.close()

# ---------- Гендер ----------
async def set_user_gender(telegram_id: int, gender: str) -> bool:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute("UPDATE users SET gender = $1 WHERE telegram_id = $2", gender, telegram_id)
        return True
    finally:
        await conn.close()

async def get_user_gender(telegram_id: int) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow("SELECT gender FROM users WHERE telegram_id = $1", telegram_id)
        return row[0] if row else None
    finally:
        await conn.close()

# ---------- Ежедневный бонус ----------
async def get_daily_info(telegram_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow(
            "SELECT last_daily, daily_streak FROM users WHERE telegram_id = $1", telegram_id
        )
        if row:
            last = row[0]
            streak = row[1] if row[1] is not None else 0
            return last, streak
        return None, 0
    finally:
        await conn.close()

async def claim_daily(telegram_id: int):
    now = datetime.now()
    last, streak = await get_daily_info(telegram_id)

    if last:
        delta = now - last
        if delta < timedelta(hours=24):
            return None

    if last:
        if now - last < timedelta(hours=48):
            streak += 1
        else:
            streak = 1
    else:
        streak = 1

    bonus = min(50 + (streak - 1) * 10, 200)

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(
            """
            UPDATE users
            SET balance = COALESCE(balance, 0) + $1,
                last_daily = $2,
                daily_streak = $3
            WHERE telegram_id = $4
            """,
            bonus, now, streak, telegram_id
        )
    finally:
        await conn.close()

    new_balance = await get_balance(telegram_id)
    logging.info(f"✅ Ежедневный бонус: user={telegram_id}, bonus={bonus}, streak={streak}, new_balance={new_balance}")

    await add_transaction(telegram_id, bonus, "daily", f"Ежедневный бонус, день {streak}")
    return bonus, streak

# ---------- Переводы ----------
async def transfer_coins(sender_id: int, receiver_id: int, amount: int):
    if amount < 100:
        return False, "Минимальная сумма перевода — 100 рофлов.", None
    if sender_id == receiver_id:
        return False, "Нельзя переводить самому себе.", None

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        async with conn.transaction():
            sender_row = await conn.fetchrow(
                "SELECT COALESCE(balance, 0) FROM users WHERE telegram_id = $1 FOR UPDATE", sender_id
            )
            if not sender_row:
                return False, "Отправитель не найден в системе.", None
            sender_balance = sender_row[0]

            if sender_balance < amount:
                return False, f"Недостаточно средств. Твой баланс: {sender_balance} рофлов.", None

            receiver_row = await conn.fetchrow(
                "SELECT COALESCE(balance, 0) FROM users WHERE telegram_id = $1", receiver_id
            )
            if not receiver_row:
                return False, "Получатель не найден в системе.", None

            commission = int(amount * 0.25)
            receive_amount = amount - commission

            await conn.execute(
                "UPDATE users SET balance = COALESCE(balance, 0) - $1 WHERE telegram_id = $2",
                amount, sender_id
            )
            await conn.execute(
                "UPDATE users SET balance = COALESCE(balance, 0) + $1 WHERE telegram_id = $2",
                receive_amount, receiver_id
            )
    finally:
        await conn.close()

    await add_transaction(sender_id, -amount, "transfer_out", f"Перевод пользователю {receiver_id}", receiver_id)
    await add_transaction(receiver_id, receive_amount, "transfer_in", f"Получено от {sender_id}", sender_id)

    return True, "Перевод выполнен успешно!", {
        "amount": amount,
        "commission": commission,
        "receive": receive_amount,
        "sender": sender_id,
        "receiver": receiver_id
    }

# ---------- Реферальная система ----------
async def generate_ref_code(telegram_id: int) -> str:
    eco_id = await get_eco_id(telegram_id)
    if not eco_id:
        return None
    random_part = secrets.token_hex(2).upper()
    return f"REF_{eco_id}_{random_part}"

async def get_ref_code(telegram_id: int) -> str:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow("SELECT ref_code FROM users WHERE telegram_id = $1", telegram_id)
        if row and row[0]:
            return row[0]

        code = await generate_ref_code(telegram_id)
        await conn.execute(
            "UPDATE users SET ref_code = $1 WHERE telegram_id = $2",
            code, telegram_id
        )
        return code
    finally:
        await conn.close()

async def register_referral(referrer_id: int, referred_id: int):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow("SELECT id FROM referrals WHERE referred_id = $1", referred_id)
        if row:
            return

        await conn.execute(
            "INSERT INTO referrals (referrer_id, referred_id, level) VALUES ($1, $2, 1)",
            referrer_id, referred_id
        )
    finally:
        await conn.close()

    await update_balance(referrer_id, 1000)
    await add_transaction(referrer_id, 1000, "referral", f"Реферал {referred_id}")

    conn2 = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn2.fetchrow(
            "SELECT referrer_id FROM referrals WHERE referred_id = $1", referrer_id
        )
        if row:
            level2_id = row[0]
            await update_balance(level2_id, 500)
            await add_transaction(level2_id, 500, "referral_level2", f"Реферал {referred_id} (2 ур.)")
    finally:
        await conn2.close()