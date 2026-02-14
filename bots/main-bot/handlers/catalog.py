from aiogram import Router, types
from aiogram.filters import Command

router = Router()

# ---------- Обработчик кнопки (уже есть) ----------
@router.callback_query(lambda c: c.data == "show_projects")
async def show_projects_callback(callback: types.CallbackQuery):
    await show_projects_message(callback.message)
    await callback.answer()

# ---------- Обработчик команды /catalog ----------
@router.message(Command("catalog"))
async def cmd_catalog(message: types.Message):
    await show_projects_message(message)

# ---------- Общая функция отправки каталога ----------
async def show_projects_message(target: types.Message):
    """Отправляет список проектов в чат (работает и для message, и для callback)."""
    projects_text = """
🚀 <b>Экосистема ROFL</b>

📌 <b>Каналы:</b>
• @code_money — Код и деньги | Золотая клавиатура
• @investor_pro — Инвестор | Акции, Золото, Недвижка
• @job_online — Онлайн-работа России
• @family_pro — PRO Детей | Mom&Woman
• @market_slivki — Сливки маркетплейсов
• @easy_money — Простые деньги
• @kolesnikov_pro — Kolesnikov Pro | Заработок

🎮 <b>Игры и боты:</b>
• @quiz_million_bot — Квиз на миллион
• @rps_game_bot — 🪨✂️📜 Камень‑ножницы‑бумага
• @school_formulas_bot — School formulas (решалка задач)
• @anonymous_giver_bot — Щедрый аноним (конкурсы)

🧠 <b>AI‑ассистенты (скоро):</b>
• 🤖 AI‑психолог
• 🤖 Цифровая мама
• 🤖 AI‑репетитор
• 🤖 AI‑помощник программиста

🌐 <b>Сайты и сервисы:</b>
• https://kolesnikov.pro
• https://code.money
• https://edu.code.money — платформа курсов

🔐 <b>LoLSchool — школа мемов и денег</b>
• Скоро открытие. Ты первый, кто узнал!
"""
    await target.answer(projects_text, parse_mode="HTML")