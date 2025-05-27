# handlers/transactions.py (с поддержкой кнопки "🔙 Назад")

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime
from database.db import db
from states.transaction_states import IncomeState, ExpenseState
from utils.keyboards import main_menu, back_keyboard
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

router = Router()

# ==== ДОХОД ====
@router.message(F.text.lower().contains("добавить доход"))
async def start_income(message: Message, state: FSMContext):
    await state.set_state(IncomeState.choosing_date)
    await message.answer("Выберите дату дохода:", reply_markup=await SimpleCalendar().start_calendar())

@router.callback_query(SimpleCalendarCallback.filter(), IncomeState.choosing_date)
async def income_date_callback(callback_query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected, selected_date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        await callback_query.answer()
        await state.update_data(date=selected_date)
        await state.set_state(IncomeState.choosing_time)
        readable = selected_date.strftime("%d %B %Y")
        await callback_query.message.answer(
            f"🗓️ Вы выбрали дату: <b>{readable}</b>\n"
            f"🕒 Теперь введите время дохода в формате <b>ЧЧ:ММ</b>:",
            reply_markup=back_keyboard()
        )

@router.message(IncomeState.choosing_time)
async def income_time(message: Message, state: FSMContext):
    try:
        selected_time = datetime.strptime(message.text.strip(), "%H:%M").time()
        data = await state.get_data()
        full_datetime = datetime.combine(data["date"], selected_time)
        await state.update_data(datetime=full_datetime)
        await state.set_state(IncomeState.choosing_category)

        categories = ["ЗП", "Подарок", "Фриланс", "Возврат долга", "Продажа"]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cat, callback_data=f"cat_income_{cat}")] for cat in categories
        ])
        await message.answer("Выберите категорию дохода:", reply_markup=keyboard)
    except ValueError:
        await message.answer("Введите корректное время в формате ЧЧ:ММ")

@router.callback_query(F.data.startswith("cat_income_"), IncomeState.choosing_category)
async def income_category_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    category = callback.data.removeprefix("cat_income_")
    user_id = await db.execute("SELECT id FROM users WHERE telegram_id = $1", callback.from_user.id, fetchval=True)

    cat_id = await db.execute(
        "SELECT id FROM categories WHERE user_id = $1 AND name = $2 AND type = 'income'",
        user_id, category, fetchval=True
    ) or await db.execute(
        "INSERT INTO categories (user_id, name, type) VALUES ($1, $2, 'income') RETURNING id",
        user_id, category, fetchval=True
    )

    await state.update_data(category_id=cat_id)
    await state.set_state(IncomeState.entering_amount)
    await callback.message.answer("Введите сумму дохода:", reply_markup=back_keyboard())

@router.message(IncomeState.entering_amount)
async def income_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
        await state.set_state(IncomeState.entering_note)
        await message.answer("Добавьте комментарий (или напишите - для пропуска):", reply_markup=back_keyboard())
    except ValueError:
        await message.answer("Введите корректную сумму:")

@router.message(IncomeState.entering_note)
async def income_note(message: Message, state: FSMContext):
    note = None if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    user_id = await db.execute("SELECT id FROM users WHERE telegram_id = $1", message.from_user.id, fetchval=True)

    await db.execute(
        "INSERT INTO transactions (user_id, category_id, amount, date, type, note) VALUES ($1, $2, $3, $4, 'income', $5)",
        user_id, data['category_id'], data['amount'], data['datetime'], note, execute=True
    )
    await state.clear()
    await message.answer("✅ Доход сохранён!", reply_markup=main_menu())

# ==== РАСХОД ====
@router.message(F.text.lower().contains("добавить расход"))
async def start_expense(message: Message, state: FSMContext):
    await state.set_state(ExpenseState.choosing_date)
    await message.answer("Выберите дату расхода:", reply_markup=await SimpleCalendar().start_calendar())

@router.callback_query(SimpleCalendarCallback.filter(), ExpenseState.choosing_date)
async def expense_date_callback(callback_query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected, selected_date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        await callback_query.answer()
        await state.update_data(date=selected_date)
        await state.set_state(ExpenseState.choosing_time)
        readable = selected_date.strftime("%d %B %Y")
        await callback_query.message.answer(
            f"🗓️ Вы выбрали дату: <b>{readable}</b>\n"
            f"🕒 Теперь введите время расхода в формате <b>ЧЧ:ММ</b>:",
            reply_markup=back_keyboard()
        )

@router.message(ExpenseState.choosing_time)
async def expense_time(message: Message, state: FSMContext):
    try:
        selected_time = datetime.strptime(message.text.strip(), "%H:%M").time()
        data = await state.get_data()
        full_datetime = datetime.combine(data["date"], selected_time)
        await state.update_data(datetime=full_datetime)
        await state.set_state(ExpenseState.choosing_category)

        categories = ["Еда", "Транспорт", "Квартира", "Здоровье", "Развлечения", "Подписки", "Другое"]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=cat, callback_data=f"cat_expense_{cat}")] for cat in categories
        ])
        await message.answer("Выберите категорию расхода:", reply_markup=keyboard)
    except ValueError:
        await message.answer("Введите корректное время в формате ЧЧ:ММ")

@router.callback_query(F.data.startswith("cat_expense_"), ExpenseState.choosing_category)
async def expense_category_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    category = callback.data.removeprefix("cat_expense_")
    if category.lower() == "другое":
        await state.set_state(ExpenseState.entering_custom_category)
        await callback.message.answer("Введите название новой категории:", reply_markup=back_keyboard())
    else:
        await state.update_data(category_name=category)
        await state.set_state(ExpenseState.entering_amount)
        await callback.message.answer("Введите сумму расхода:", reply_markup=back_keyboard())

@router.message(ExpenseState.entering_custom_category)
async def expense_custom_category(message: Message, state: FSMContext):
    await state.update_data(category_name=message.text.strip())
    await state.set_state(ExpenseState.entering_amount)
    await message.answer("Введите сумму расхода:", reply_markup=back_keyboard())

@router.message(ExpenseState.entering_amount)
async def expense_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        await state.update_data(amount=amount)
        await state.set_state(ExpenseState.entering_note)
        await message.answer("Добавьте комментарий (или напишите - для пропуска):", reply_markup=back_keyboard())
    except ValueError:
        await message.answer("Введите корректную сумму:")

@router.message(ExpenseState.entering_note)
async def expense_note(message: Message, state: FSMContext):
    note = None if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    user_id = await db.execute("SELECT id FROM users WHERE telegram_id = $1", message.from_user.id, fetchval=True)

    cat_id = await db.execute(
        "SELECT id FROM categories WHERE user_id = $1 AND name = $2 AND type = 'expense'",
        user_id, data['category_name'], fetchval=True
    ) or await db.execute(
        "INSERT INTO categories (user_id, name, type) VALUES ($1, $2, 'expense') RETURNING id",
        user_id, data['category_name'], fetchval=True
    )

    await db.execute(
        "INSERT INTO transactions (user_id, category_id, amount, date, type, note) VALUES ($1, $2, $3, $4, 'expense', $5)",
        user_id, cat_id, data['amount'], data['datetime'], note, execute=True
    )
    await state.clear()
    await message.answer("✅ Расход сохранён!", reply_markup=main_menu())

# Теперь добавлена кнопка возврата во всех этапах ввода.
