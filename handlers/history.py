from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from datetime import datetime
from states.transaction_states import FilterState
from database.db import db
from utils.keyboards import main_menu, back_keyboard

router = Router()

# 🔹 Шаг 1: вход в историю
@router.message(F.text == "📜 История транзакций")
async def start_history_filter(message: Message, state: FSMContext):
    await state.set_state(FilterState.choosing_filter_type)
    await message.answer(
        "Вы вошли в раздел истории транзакций.\nНажмите 🔙 Назад, чтобы выйти.",
        reply_markup=back_keyboard()
    )
    await message.answer(
        "📅 Выберите <b>начальную дату</b> периода:",
        reply_markup=await SimpleCalendar().start_calendar()
    )

# 🔹 Шаг 2: выбор начальной даты
@router.callback_query(SimpleCalendarCallback.filter(), FilterState.choosing_filter_type)
async def choose_start(callback_query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected, start_date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        await callback_query.answer()
        await state.update_data(start_date=start_date)
        await state.set_state(FilterState.entering_filter_value)
        await callback_query.message.answer(
            "📅 Выберите <b>конечную дату</b>:",
            reply_markup=await SimpleCalendar().start_calendar()
        )

# 🔹 Шаг 3: выбор конца периода и вывод транзакций
@router.callback_query(SimpleCalendarCallback.filter(), FilterState.entering_filter_value)
async def choose_end(callback_query: CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected, end_date = await SimpleCalendar().process_selection(callback_query, callback_data)
    if selected:
        await callback_query.answer()
        data = await state.get_data()

        start_dt = datetime.combine(data["start_date"], datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        readable_start = data["start_date"].strftime("%d %B %Y")
        readable_end = end_date.strftime("%d %B %Y")
        await callback_query.message.answer(
            f"📅 Вы выбрали период:\n<b>с {readable_start} по {readable_end}</b>"
        )

        user_id = await db.execute(
            "SELECT id FROM users WHERE telegram_id = $1",
            callback_query.from_user.id,
            fetchval=True
        )

        transactions = await db.execute(
            """
            SELECT t.id, t.type, c.name, t.amount, t.date, t.note
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = $1 AND t.date BETWEEN $2 AND $3
            ORDER BY t.date DESC
            """,
            user_id, start_dt, end_dt,
            fetch=True
        )

        if not transactions:
            await callback_query.message.answer("❌ Нет транзакций за выбранный период.")
        else:
            for tx in transactions:
                type_ru = "Доход" if tx["type"] == "income" else "Расход"
                text = (
                    f"<b>{type_ru}</b> | {tx['name']} | {tx['amount']} ₽ | "
                    f"{tx['date'].strftime('%d.%m.%Y %H:%M')}"
                )
                if tx['note']:
                    text += f"\n💬 {tx['note']}"

                delete_button = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_txn_{tx['id']}")]
                    ]
                )
                await callback_query.message.answer(text, reply_markup=delete_button)

        await state.clear()

# 🔹 Удаление транзакции
@router.callback_query(F.data.startswith("delete_txn_"))
async def delete_transaction_by_id(callback: CallbackQuery):
    txn_id = int(callback.data.removeprefix("delete_txn_"))
    await db.execute("DELETE FROM transactions WHERE id = $1", txn_id, execute=True)
    await callback.answer("Удалено ✅")
    await callback.message.edit_text("❌ Транзакция удалена.")

# 🔙 Назад
@router.message(F.text == "🔙 Назад")
async def go_back_from_history(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🔁 Главное меню:", reply_markup=main_menu())
