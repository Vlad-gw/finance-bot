# handlers/start.py

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from database.db import db
from utils.keyboards import main_menu, back_keyboard

router = Router()

# Обработчик команды /start
@router.message(CommandStart())
async def cmd_start(message: Message):
    user = await db.execute(
        "SELECT id FROM users WHERE telegram_id = $1",
        message.from_user.id,
        fetchval=True
    )
    if not user:
        await db.execute(
            "INSERT INTO users (telegram_id, username, first_name) VALUES ($1, $2, $3)",
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            execute=True
        )
    await message.answer(
        f"Привет, <b>{message.from_user.first_name}</b>!\nЯ помогу тебе вести учёт финансов. \nВыбери действие:",
        reply_markup=main_menu()
    )

from aiogram.fsm.context import FSMContext

@router.message(F.text == "🔙 Назад")
async def go_back(message: Message, state: FSMContext):
    await state.clear()  # Сброс состояния FSM
    await message.answer("🔁 Главное меню:", reply_markup=main_menu())
