from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from datetime import datetime
from states.transaction_states import DeleteState
from database.db import db
from utils.keyboards import main_menu, back_keyboard  # ✅ добавлено
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

router = Router()

# 🔹 Шаг 1: старт удаления
@router.message(F.text == "🗑 Удаление транзакций")
async def start_deletion(message: Message, state: FSMContext):
    await state.set_state(DeleteState.choosing_date)
    await message.answer(
        "📅 Выберите <b>начальную дату</b> для удаления транзакций:",
        reply_markup=await SimpleCalendar().start_calendar()
    )

# 🔹 Шаг 2: выбор начальной даты
@router.callback_query(SimpleCalendarCallback.filter(), DeleteState.choosing_date)
async def choose_start_date(callback_query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected, start_date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        await callback_query.answer()
        await state.update_data(start_date=start_date)
        await state.set_state(DeleteState.entering_filter_value)
        await callback_query.message.answer(
            "📅 Выберите <b>конечную дату</b>:",
            reply_markup=await SimpleCalendar().start_calendar()
        )

# 🔹 Шаг 3: выбор конечной даты
@router.callback_query(SimpleCalendarCallback.filter(), DeleteState.entering_filter_value)
async def choose_end_date(callback_query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected, end_date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        await callback_query.answer()
        data = await state.get_data()
        await state.update_data(end_date=end_date)

        start_str = data['start_date'].strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="confirm_delete"),
                InlineKeyboardButton(text="❌ Нет", callback_data="cancel_delete")
            ]
        ])

        await state.set_state(DeleteState.confirming)
        await callback_query.message.answer(
            f"Вы уверены, что хотите удалить транзакции\n<b>с {start_str} по {end_str}</b>?",
            reply_markup=keyboard
        )

# 🔹 Шаг 4: подтверждение удаления
@router.callback_query(F.data == "confirm_delete", DeleteState.confirming)
async def confirm_deletion(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    start = datetime.combine(data['start_date'], datetime.min.time())
    end = datetime.combine(data['end_date'], datetime.max.time())

    user_id = await db.execute(
        "SELECT id FROM users WHERE telegram_id = $1",
        callback.from_user.id,
        fetchval=True
    )

    deleted = await db.execute(
        "DELETE FROM transactions WHERE user_id = $1 AND date BETWEEN $2 AND $3 RETURNING id",
        user_id, start, end, fetch=True
    )

    await state.clear()
    await callback.message.answer(
        f"✅ Удалено транзакций: <b>{len(deleted)}</b>",
        reply_markup=main_menu()
    )

# 🔹 Шаг 5: отмена удаления
@router.callback_query(F.data == "cancel_delete", DeleteState.confirming)
async def cancel_deletion(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Удаление отменено.")
    await state.clear()
    await callback.message.answer("❌ Удаление транзакций отменено.", reply_markup=main_menu())

# 🔙 Обработчик кнопки "Назад"
@router.message(F.text == "🔙 Назад")
async def go_back_from_delete(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🔁 Главное меню:", reply_markup=main_menu())
