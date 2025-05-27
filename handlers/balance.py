# Показ баланса
from aiogram import Router, F
from aiogram.types import Message
from database.db import db

router = Router()

@router.message(F.text == "💰 Показать баланс")
async def show_balance(message: Message):
    user_id = await db.execute("SELECT id FROM users WHERE telegram_id = $1", message.from_user.id, fetchval=True)
    income = await db.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = $1 AND type = 'income'", user_id, fetchval=True)
    expense = await db.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = $1 AND type = 'expense'", user_id, fetchval=True)
    balance = income - expense

    await message.answer(
        f"💰 <b>Баланс:</b> {balance:.2f} ₽\n📈 Доходы: {income:.2f} ₽\n📉 Расходы: {expense:.2f} ₽"
    )
