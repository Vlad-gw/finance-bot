from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from states.export_states import ExportState
from database.db import db
from services.excel import generate_excel
from datetime import date
from utils.keyboards import main_menu, back_keyboard

router = Router()

# 🔹 Старт экспорта
@router.message(F.text == "📁 Экспорт в Excel")
async def start_export(message: Message, state: FSMContext):
    await state.set_state(ExportState.choosing_period_type)
    await message.answer(
        "Выберите тип экспорта:\n1 — весь период\n2 — конкретный месяц",
        reply_markup=back_keyboard()
    )

# 🔹 Выбор типа периода
@router.message(ExportState.choosing_period_type)
async def choose_type(message: Message, state: FSMContext):
    if message.text.strip() == "1":
        telegram_id = message.from_user.id
        transactions = await db.execute(
            """
            SELECT t.type, c.name, t.amount, t.date, t.note
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = (SELECT id FROM users WHERE telegram_id = $1)
            ORDER BY t.date
            """,
            telegram_id,
            fetch=True
        )
        file_path = generate_excel(transactions)
        await message.answer_document(FSInputFile(file_path), caption="📁 Все транзакции")
        await state.clear()
    elif message.text.strip() == "2":
        await state.set_state(ExportState.choosing_year)
        await message.answer("Введите год (например, 2025):", reply_markup=back_keyboard())
    else:
        await message.answer("Введите 1 или 2", reply_markup=back_keyboard())

# 🔹 Ввод года
@router.message(ExportState.choosing_year)
async def choose_year(message: Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await start_export(message, state)
        return

    try:
        year = int(message.text)
        await state.update_data(year=year)
        await state.set_state(ExportState.choosing_month)
        await message.answer("Введите месяц (например, 04):", reply_markup=back_keyboard())
    except ValueError:
        await message.answer("Введите корректный год", reply_markup=back_keyboard())

# 🔹 Ввод месяца и генерация Excel
@router.message(ExportState.choosing_month)
async def choose_month(message: Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await state.set_state(ExportState.choosing_year)
        await message.answer("Введите год (например, 2025):", reply_markup=back_keyboard())
        return

    try:
        month = int(message.text)
        data = await state.get_data()
        start_date = date(data["year"], month, 1)
        end_date = date(data["year"] + (month == 12), (month % 12) + 1, 1)

        telegram_id = message.from_user.id
        transactions = await db.execute(
            """
            SELECT t.type, c.name, t.amount, t.date, t.note
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = (SELECT id FROM users WHERE telegram_id = $1)
            AND t.date >= $2 AND t.date < $3
            ORDER BY t.date
            """,
            telegram_id, start_date, end_date,
            fetch=True
        )

        file_path = generate_excel(transactions)
        await message.answer_document(FSInputFile(file_path),
                                      caption=f"📁 Транзакции за {month:02}.{data['year']}")
        await state.clear()
    except Exception as e:
        await message.answer(f"⚠️ Ошибка: {e}", reply_markup=back_keyboard())

# 🔙 Обработчик кнопки "Назад" из любого состояния
@router.message(F.text == "🔙 Назад")
async def cancel_export(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🔁 Главное меню:", reply_markup=main_menu())
