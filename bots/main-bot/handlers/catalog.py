import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.callback_query(lambda c: c.data == "show_projects")
async def show_projects_callback(callback: types.CallbackQuery):
    await show_projects_message(callback.message)
    await callback.answer()

@router.message(Command("catalog"))
async def cmd_catalog(message: types.Message):
    await show_projects_message(message)

async def show_projects_message(target: types.Message):
    text = """
🚀 <b>Экосистема ROFL</b>

📌 <b>Каналы:</b>
• @code_money — Код и деньги
• @investor_pro — Инвестор
• @job_online — Работа
• @family_pro — PRO Семью
• @market_slivki — Сливки
• @easy_money — Простые деньги
• @kolesnikov_pro — Kolesnikov Pro

🎮 <b>Игры и боты:</b>
• @rps_game_bot — КНБ
• @quiz_million_bot — Квиз
• @school_formulas_bot — Формулы
• @anonymous_giver_bot — Аноним

🌐 <b>Сайты:</b>
• https://kolesnikov.pro
• https://code.money
"""
    await target.answer(text, parse_mode="HTML")