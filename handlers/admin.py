from aiogram import Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    FSInputFile,
)
from config import ADMIN_IDS
from database.db import db
from services.export import export_user_to_excel

router = Router(name=__name__)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# Главное меню /admin
@router.message(F.text == "/admin")
async def admin_menu(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ У вас нет прав администратора.")

    await message.answer(
        "🛠 <b>Админ-панель:</b>\n"
        "/stats — Показать статистику\n"
        "/users — Список пользователей\n"
        "/all_transactions — Топ 10 транзакций\n"
        "/user [telegram_id] — Подробно о пользователе",
        parse_mode="HTML"
    )


# Статистика /stats
@router.message(F.text == "/stats")
async def show_stats(message: Message):
    if not is_admin(message.from_user.id):
        return

    users = await db.execute("SELECT COUNT(*) FROM users", fetchval=True)
    txs = await db.execute("SELECT COUNT(*) FROM transactions", fetchval=True)
    await message.answer(f"📊 Статистика:\nПользователей: {users}\nТранзакций: {txs}")


# Список пользователей /users
@router.message(F.text == "/users")
async def show_users(message: Message):
    if not is_admin(message.from_user.id):
        return

    rows = await db.execute("SELECT telegram_id, username FROM users", fetch=True)
    text = "\n".join([
        f"{row['username'] or 'без ника'} — {row['telegram_id']}"
        for row in rows
    ])
    await message.answer(f"👥 Список пользователей:\n{text or 'Нет пользователей.'}")


# Топ транзакций /all_transactions
@router.message(F.text == "/all_transactions")
async def show_transactions(message: Message):
    if not is_admin(message.from_user.id):
        return

    rows = await db.execute(
        """
        SELECT t.id, t.amount, t.type, t.date, t.note,
               c.name as category_name,
               u.username, u.telegram_id
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN users u ON t.user_id = u.id
        ORDER BY t.amount DESC
        LIMIT 10
        """,
        fetch=True,
    )

    if not rows:
        return await message.answer("🧾 Нет транзакций.")

    text_lines = []
    for row in rows:
        user_info = f"@{row['username']}" if row['username'] else f"id:{row['telegram_id']}"
        line = (
            f"#{row['id']} | 💰 {row['amount']} ₽ ({row['type']})\n"
            f"📂 {row['category_name'] or 'Без категории'} | 👤 {user_info} | "
            f"📅 {row['date'].strftime('%d.%m.%Y')}"
        )
        if row["note"]:
            line += f"\n💬 {row['note']}"
        text_lines.append(line)

    await message.answer("🧾 <b>Топ 10 транзакций:</b>\n\n" + "\n\n".join(text_lines), parse_mode="HTML")


# Инфо о пользователе + кнопки
@router.message(F.text.startswith("/user"))
async def get_user_info(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        return await message.answer("❗ Использование: /user [telegram_id]")

    telegram_id = int(parts[1])
    user = await db.execute(
        "SELECT * FROM users WHERE telegram_id = $1", telegram_id, fetchrow=True
    )
    if not user:
        return await message.answer("❌ Пользователь не найден.")

    text = (
        f"👤 <b>Информация:</b>\n"
        f"<b>ID:</b> <code>{user['telegram_id']}</code>\n"
        f"<b>Username:</b> @{user['username'] or '—'}\n"
        f"<b>Имя:</b> {user.get('first_name') or '—'}\n"
        f"<b>Дата регистрации:</b> {user['created_at'].strftime('%Y-%m-%d %H:%M')}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Экспортировать", callback_data=f"export_user:{telegram_id}")],
        [InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_user:{telegram_id}")]
    ])

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# Кнопка 📤 Экспорт
@router.callback_query(F.data.startswith("export_user:"))
async def export_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    telegram_id = int(callback.data.split(":")[1])
    path = await export_user_to_excel(telegram_id)
    await callback.message.answer_document(FSInputFile(path))


# Кнопка ❌ Удалить
@router.callback_query(F.data.startswith("delete_user:"))
async def delete_user(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    telegram_id = int(callback.data.split(":")[1])
    user_id = await db.execute(
        "SELECT id FROM users WHERE telegram_id = $1", telegram_id, fetchval=True
    )
    if not user_id:
        return await callback.message.edit_text("❌ Пользователь не найден.")

    await db.execute("DELETE FROM transactions WHERE user_id = $1", user_id, execute=True)
    await db.execute("DELETE FROM categories WHERE user_id = $1", user_id, execute=True)
    await db.execute("DELETE FROM users WHERE id = $1", user_id, execute=True)

    await callback.message.edit_text("✅ Пользователь и все его данные удалены.")
