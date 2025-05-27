# Профиль пользователя
from aiogram import Router, F
from aiogram.types import Message
from database.db import db

router = Router()

# Обработка команды /profile
@router.message(F.text == "/profile")
async def profile_command(message: Message):
    await show_profile(message)

# Обработка кнопки "👤 Профиль"
@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    tg_id = message.from_user.id
    user = await db.execute(
        "SELECT id, username, first_name, created_at FROM users WHERE telegram_id = $1",
        tg_id,
        fetchrow=True
    )
    if not user:
        await message.answer("Пользователь не найден.")
        return

    income = await db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = $1 AND type = 'income'",
        user['id'], fetchval=True
    )
    expense = await db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = $1 AND type = 'expense'",
        user['id'], fetchval=True
    )
    count = await db.execute(
        "SELECT COUNT(*) FROM transactions WHERE user_id = $1",
        user['id'], fetchval=True
    )

    await message.answer(
        f"👤 <b>Профиль</b>\n"
        f"Имя: {user['first_name']}\n"
        f"Username: @{user['username']}\n"
        f"Дата регистрации: {user['created_at'].date()}\n\n"
        f"📊 Транзакций: {count}\n"
        f"📈 Общий доход: {income:.2f} ₽\n"
        f"📉 Общий расход: {expense:.2f} ₽"
    )
