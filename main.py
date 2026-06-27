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

# ==================== КЛАВИАТУРЫ ====================
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

def cancel_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="back_to_main", style="danger")]
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
async def categories_handler(callback: types.CallbackQuery):
    session = Session()
    products = session.query(Product).all()
    session.close()

    if not products:
        await callback.message.edit_text("📂 *Товары*\n\nВ магазине пока нет товаров.", parse_mode="Markdown", reply_markup=back_menu())
        await callback.answer()
        return

    buttons = []
    for p in products:
        stock_emoji = "🟢" if p.stock > 0 else "🔴"
        buttons.append([InlineKeyboardButton(text=f"{p.name} | {p.price}$ | {stock_emoji} {p.stock}шт", callback_data=f"product_{p.id}", style="primary" if p.stock > 0 else "danger")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main", style="danger")])

    await callback.message.edit_text("📂 *Наши товары:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

# ==================== ТОВАР ====================
@dp.callback_query(F.data.startswith("product_"))
async def product_handler(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    session = Session()
    product = session.query(Product).get(product_id)
    session.close()

    if not product:
        await callback.answer("Товар не найден")
        return

    text = f"📦 *{product.name}*\n\n{product.description or 'Описание отсутствует'}\n\n💰 Цена: {product.price}$\n📦 В наличии: {product.stock} шт."
    in_stock = product.stock > 0

    buttons = []
    if in_stock:
        buttons.append([InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{product_id}", style="success")])
    else:
        buttons.append([InlineKeyboardButton(text="❌ Нет в наличии", callback_data="no_stock", style="danger")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="categories", style="primary")])

    if product.photo_id:
        await callback.message.delete()
        await callback.message.answer_photo(photo=product.photo_id, caption=text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    else:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

# ==================== ПОКУПКА ====================
@dp.callback_query(F.data.startswith("buy_"))
async def buy_handler(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    session = Session()
    product = session.query(Product).get(product_id)
    user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
    session.close()

    if not product or product.stock <= 0:
        await callback.answer("❌ Товар отсутствует!")
        return

    if user.balance < product.price:
        await callback.message.edit_text(f"❌ *Недостаточно средств!*\n\n💰 Ваш баланс: {user.balance}$\n💵 Стоимость товара: {product.price}$\n\nПополните баланс в профиле.", parse_mode="Markdown", reply_markup=back_menu())
        await callback.answer()
        return

    # Подтверждение
    buttons = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_buy_{product_id}", style="success")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data=f"product_{product_id}", style="danger")]
    ]
    await callback.message.edit_text(f"🛒 *Подтверждение покупки*\n\n📦 Товар: {product.name}\n💰 Цена: {product.price}$\n💳 Ваш баланс: {user.balance}$", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("confirm_buy_"))
async def confirm_buy_handler(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    session = Session()
    product = session.query(Product).get(product_id)
    user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()

    if not product or product.stock <= 0:
        await callback.answer("❌ Товара нет в наличии!")
        session.close()
        return

    if user.balance < product.price:
        await callback.answer("❌ Недостаточно средств!")
        session.close()
        return

    user.balance -= product.price
    product.stock -= 1
    order = Order(user_id=user.id, product_id=product.id, quantity=1, total=product.price, status='paid')
    session.add(order)
    session.commit()
    session.close()

    await callback.message.edit_text(f"✅ *Покупка успешна!*\n\n📦 Товар: {product.name}\n💰 Стоимость: {product.price}$\n💳 Остаток баланса: {user.balance}$\n\n⏳ Ожидайте выдачу товара в течение 5 минут.", parse_mode="Markdown", reply_markup=main_menu())
    await callback.answer("🎉 Поздравляем с покупкой!")

# ==================== ИНФОРМАЦИЯ ====================
@dp.callback_query(F.data == "info")
async def info_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ *Информация о боте*\n\n🏪 Название магазина: *Kosmos Shop*\n📅 Создан: 14.02.2026\n📦 Продано товаров за Май: 183 товаров\n🆘 Тех поддержка: @KosmossShop_Supp\n\n⭐️ Спасибо, что выбираете нас!",
        parse_mode="Markdown",
        reply_markup=back_menu()
    )
    await callback.answer()

# ==================== ПОДДЕРЖКА ====================
@dp.callback_query(F.data == "support")
async def support_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔄 *Техподдержка*\n\n❓ Что-то случилось? Вы можете подать заявку\nили написать нашему менеджеру.\n\n👨‍💼 Работает 24/7:\n• Технические проблемы — в течение часа\n• Остальные вопросы — в течение 25 минут\n\n📱 @KosmossShop_Supp",
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
        f"👤 *Ваш профиль*\n\n🆔 ID: {callback.from_user.id}\n👤 Имя: {callback.from_user.first_name}\n💰 Баланс: {user.balance}$\n📦 Покупок: {orders_count}\n👥 Приглашено: {referrals_count}\n\n💎 Статус: {'VIP' if orders_count >= 10 else 'Обычный покупатель'}",
        parse_mode="Markdown",
        reply_markup=profile_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "my_orders")
async def my_orders_handler(callback: types.CallbackQuery):
    session = Session()
    user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
    orders = session.query(Order).filter_by(user_id=user.id).order_by(Order.created_at.desc()).limit(10).all()
    session.close()

    if not orders:
        await callback.message.edit_text("📦 У вас пока нет покупок.", reply_markup=profile_menu())
        await callback.answer()
        return

    text = "📦 *Ваши последние покупки:*\n\n"
    for order in orders:
        status_emoji = "✅" if order.status == "paid" else "⏳"
        text += f"{status_emoji} {order.product.name} — {order.total}$\n"

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=profile_menu())
    await callback.answer()

# ==================== ПОПОЛНЕНИЕ ====================
@dp.callback_query(F.data == "deposit")
async def deposit_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "💰 *Пополнение баланса*\n\nВведите сумму в долларах (мин. 7$)\nПополнение происходит через Crypto Bot\n\n⌨️ *Пример:* `10`, `15.5`, `100`",
        parse_mode="Markdown",
        reply_markup=cancel_menu()
    )
    await state.set_state(ShopStates.deposit_amount)
    await callback.answer()

@dp.message(ShopStates.deposit_amount)
async def process_deposit(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount < 7:
            await message.answer("❌ Минимальная сумма пополнения — 7$", reply_markup=cancel_menu())
            return

        invoice = await create_invoice(message.from_user.id, amount)
        if not invoice:
            await message.answer("❌ Ошибка создания счёта. Попробуйте позже.", reply_markup=back_menu())
            await state.set_state(ShopStates.browsing)
            return

        await message.answer(
            f"💳 *Счёт создан!*\n\n💰 Сумма: {amount} USDT\n🆔 Номер счёта: {invoice.invoice_id}\n\n🔗 Ссылка для оплаты:\n{invoice.bot_invoice_url}\n\n⏳ Счёт действителен 60 минут\n📱 После оплаты баланс пополнится автоматически",
            parse_mode="Markdown",
            reply_markup=back_menu()
        )
        await state.set_state(ShopStates.browsing)
    except:
        await message.answer("❌ Введите число\nПример: `10` или `15.5`", parse_mode="Markdown", reply_markup=cancel_menu())

# ==================== АДМИНКА ====================
@dp.message(Command("adm"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return

    session = Session()
    users_count = session.query(User).count()
    orders_count = session.query(Order).count()
    total_revenue = session.query(Order).filter_by(status='paid').with_entities(func.sum(Order.total)).scalar() or 0
    session.close()

    await message.answer(
        f"🔐 *Админ-панель*\n\n👥 Всего пользователей: {users_count}\n📦 Всего заказов: {orders_count}\n💰 Общая выручка: {round(total_revenue, 2)}$\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_menu()
    )

# ==================== НЕИЗВЕСТНЫЕ ====================
@dp.message()
async def unknown(message: types.Message):
    await message.answer("Используйте кнопки для навигации.", reply_markup=main_menu())

# ==================== ЗАПУСК ====================
async def main():
    print("🚀 БОТ ЗАПУЩЕН!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
