import logging
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import func

from config import BOT_TOKEN, ADMIN_IDS
from database import Session, User, Category, Product, Order, SupportTicket, init_db
from states import ShopStates
from crypto_pay import create_invoice

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

init_db()

# ==================== КЛАВИАТУРЫ (ВСЁ ИНЛАЙН) ====================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📂 Категории", callback_data="categories", style="success")],
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data="info", style="primary")],
        [InlineKeyboardButton(text="🔄 Техподдержка", callback_data="support", style="danger")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile", style="primary")]
    ])

def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main", style="primary")]
    ])

def support_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Подать заявку", callback_data="submit_ticket", style="primary")],
        [InlineKeyboardButton(text="👨‍💼 Написать менеджеру", url="https://t.me/KosmossShop_Supp", style="success")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main", style="danger")]
    ])

def profile_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="deposit", style="success")],
        [InlineKeyboardButton(text="📦 Мои покупки", callback_data="my_orders", style="primary")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main", style="danger")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_mailing", style="primary")],
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product", style="success")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users", style="primary")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats", style="primary")],
        [InlineKeyboardButton(text="◀️ Выход", callback_data="back_to_main", style="danger")]
    ])

def is_admin(user_id: int) -> bool:
    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()
    session.close()
    return user and user.is_admin

# ==================== СТАРТ ====================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        session.add(user)
        session.commit()

        args = message.text.split()
        if len(args) > 1:
            try:
                referrer_id = int(args[1])
                referrer = session.query(User).filter_by(telegram_id=referrer_id).first()
                if referrer and referrer.id != user.id:
                    user.referrer_id = referrer.id
                    referrer.balance += 1.0
                    session.commit()
                    await bot.send_message(
                        referrer.telegram_id,
                        "🎉 Вы получили 1$ за приглашение нового пользователя!"
                    )
            except:
                pass

    session.close()
    await state.set_state(ShopStates.browsing)

    await message.answer(
        "🚀 *Салют*, ты попал в *Kosmos Shop*!\n\n"
        "✨ Идеальный вариант для покупки *логов Gu* 🔥\n"
        "Также у нас есть много чего другого!\n\n"
        "🌟 Осваивайся, удачного ворка! 💪",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ==================== НАЗАД ====================
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ShopStates.browsing)
    await callback.message.edit_text(
        "🚀 *Салют*, ты попал в *Kosmos Shop*!\n\n"
        "✨ Идеальный вариант для покупки *логов Gu* 🔥\n"
        "Также у нас есть много чего другого!\n\n"
        "🌟 Осваивайся, удачного ворка! 💪",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )
    await callback.answer()

# ==================== КАТЕГОРИИ ====================
@dp.callback_query(F.data == "categories")
async def show_categories(callback: types.CallbackQuery):
    session = Session()
    products = session.query(Product).all()
    session.close()

    if not products:
        await callback.message.edit_text(
            "📂 *Товары*\n\nВ магазине пока нет товаров.",
            parse_mode="Markdown",
            reply_markup=back_menu()
        )
        await callback.answer()
        return

    buttons = []
    for p in products:
        stock_emoji = "🟢" if p.stock > 0 else "🔴"
        buttons.append([InlineKeyboardButton(
            text=f"{p.name} | {p.price}$ | {stock_emoji} {p.stock}шт",
            callback_data=f"product_{p.id}",
            style="primary" if p.stock > 0 else "danger"
        )])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main", style="danger")])

    await callback.message.edit_text(
        "📂 *Наши товары:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()

# ==================== ИНФОРМАЦИЯ ====================
@dp.callback_query(F.data == "info")
async def info_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ *Информация о боте*\n\n"
        "🏪 Название магазина: *Kosmos Shop*\n"
        "📅 Создан: 14.02.2026\n"
        "📦 Продано товаров за Май: 183 товаров\n"
        "🆘 Тех поддержка: @KosmossShop_Supp\n\n"
        "⭐️ Спасибо, что выбираете нас!",
        parse_mode="Markdown",
        reply_markup=back_menu()
    )
    await callback.answer()

# ==================== ТЕХПОДДЕРЖКА ====================
@dp.callback_query(F.data == "support")
async def support_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔄 *Техподдержка*\n\n"
        "❓ Что-то случилось? Вы можете подать заявку\n"
        "или написать нашему менеджеру.\n\n"
        "👨‍💼 Работает 24/7:\n"
        "• Технические проблемы — в течение часа\n"
        "• Остальные вопросы — в течение 25 минут\n\n"
        "📱 @KosmossShop_Supp",
        parse_mode="Markdown",
        reply_markup=support_menu()
    )
    await callback.answer()

# ==================== ПРОФИЛЬ ====================
@dp.callback_query(F.data == "profile")
async def profile_handler(callback: types.CallbackQuery):
    session = Session()
    user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
    orders_count = session.query(Order).filter_by(user_id=user.id).count()
    referrals_count = session.query(User).filter_by(referrer_id=user.id).count()
    session.close()

    await callback.message.edit_text(
        f"👤 *Ваш профиль*\n\n"
        f"🆔 ID: {callback.from_user.id}\n"
        f"👤 Имя: {callback.from_user.first_name}\n"
        f"💰 Баланс: {user.balance}$\n"
        f"📦 Покупок: {orders_count}\n"
        f"👥 Приглашено: {referrals_count}\n\n"
        f"💎 Статус: {'VIP' if orders_count >= 10 else 'Обычный покупатель'}",
        parse_mode="Markdown",
        reply_markup=profile_menu()
    )
    await callback.answer()

# ==================== МОИ ПОКУПКИ ====================
@dp.callback_query(F.data == "my_orders")
async def my_orders(callback: types.CallbackQuery):
    session = Session()
    user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
    orders = session.query(Order).filter_by(user_id=user.id).order_by(Order.created_at.desc()).limit(10).all()
    session.close()

    if not orders:
        await callback.message.edit_text(
            "📦 У вас пока нет покупок.",
            reply_markup=profile_menu()
        )
        await callback.answer()
        return

    text = "📦 *Ваши последние покупки:*\n\n"
    for order in orders:
        status_emoji = "✅" if order.status == "paid" else "⏳"
        text += f"{status_emoji} {order.product.name} — {order.total}$\n"

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=profile_menu())
    await callback.answer()

# ==================== ОСТАЛЬНЫЕ ОБРАБОТЧИКИ (товары, покупка и т.д.) ====================
# ... (оставляем остальные обработчики без изменений, они уже есть в проекте)

# ==================== АДМИНКА ====================
@dp.message(Command("adm"))
async def admin_panel(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    session = Session()
    users_count = session.query(User).count()
    orders_count = session.query(Order).count()
    total_revenue = session.query(Order).filter_by(status='paid').with_entities(
        func.sum(Order.total)
    ).scalar() or 0
    session.close()

    await message.answer(
        f"🔐 *Админ-панель*\n\n"
        f"👥 Всего пользователей: {users_count}\n"
        f"📦 Всего заказов: {orders_count}\n"
        f"💰 Общая выручка: {round(total_revenue, 2)}$\n\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_menu()
    )
    await state.set_state(ShopStates.browsing)

# ==================== ЗАПУСК ====================
async def main():
    print("🚀 Бот Kosmos Shop запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
