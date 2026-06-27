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
        [InlineKeyboardButton(text="📂 Добавить категорию", callback_data="admin_add_category", style="success")],
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product", style="primary")],
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_mailing", style="primary")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users", style="primary")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats", style="primary")],
        [InlineKeyboardButton(text="📋 Заявки", callback_data="admin_tickets", style="primary")],
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

@dp.callback_query(F.data == "admin_panel")
async def back_to_admin_panel(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    await state.clear()
    await state.set_state(ShopStates.browsing)
    
    session = Session()
    users_count = session.query(User).count()
    orders_count = session.query(Order).count()
    total_revenue = session.query(Order).filter_by(status='paid').with_entities(func.sum(Order.total)).scalar() or 0
    session.close()

    await callback.message.edit_text(
        f"🔐 *Админ-панель*\n\n👥 Всего пользователей: {users_count}\n📦 Всего заказов: {orders_count}\n💰 Общая выручка: {round(total_revenue, 2)}$\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_menu()
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

# ==================== ПОДДЕРЖКА ====================
@dp.callback_query(F.data == "support")
async def support_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔄 *Техподдержка*\n\n❓ Что-то случилось? Вы можете подать заявку\nили написать нашему менеджеру.\n\n👨‍💼 Работает 24/7:\n• Технические проблемы — в течение часа\n• Остальные вопросы — в течение 25 минут\n\n📱 @KosmossShop_Supp",
        parse_mode="Markdown",
        reply_markup=support_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "submit_ticket")
async def submit_ticket(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 *Подача заявки*\n\nОпишите вашу проблему подробно.\nМы свяжемся с вами в ближайшее время.\n\n❌ Для отмены отправьте /cancel",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="back_to_main", style="danger")]
        ])
    )
    await state.set_state(ShopStates.support_ticket)
    await callback.answer()

@dp.message(ShopStates.support_ticket)
async def process_ticket(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) == 0:
        await message.answer(
            "❌ Сообщение не может быть пустым!\n\nОпишите вашу проблему:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="back_to_main", style="danger")]
            ])
        )
        return
    
    if len(message.text.strip()) < 10:
        await message.answer(
            "❌ Сообщение слишком короткое (минимум 10 символов).\n\nОпишите проблему подробнее:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="back_to_main", style="danger")]
            ])
        )
        return
    
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()
    
    if not user:
        session.close()
        await message.answer(
            "❌ Пользователь не найден. Используйте /start",
            reply_markup=main_menu()
        )
        await state.clear()
        await state.set_state(ShopStates.browsing)
        return

    try:
        ticket = SupportTicket(
            user_id=user.id, 
            message=message.text.strip(), 
            status='open',
            created_at=datetime.now()
        )
        session.add(ticket)
        session.commit()
        
        admin_notification = (
            f"📨 *Новая заявка в поддержку!*\n\n"
            f"🆔 ID заявки: {ticket.id}\n"
            f"👤 Пользователь: {message.from_user.first_name}\n"
            f"🆔 Telegram ID: {message.from_user.id}\n"
            f"👤 Username: @{message.from_user.username or 'Не указан'}\n"
            f"📝 Сообщение:\n{message.text.strip()}\n\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id, 
                    admin_notification, 
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="✅ Ответить", 
                            callback_data=f"reply_ticket_{ticket.id}_{message.from_user.id}",
                            style="success"
                        )]
                    ])
                )
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")
        
        session.close()
        
        await message.answer(
            "✅ *Заявка отправлена!*\n\n"
            f"🆔 Номер заявки: {ticket.id}\n"
            "⏳ Ожидайте ответа в ближайшее время.\n"
            "📱 Наши менеджеры свяжутся с вами в этом чате.",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
        
        await state.clear()
        await state.set_state(ShopStates.browsing)
        
    except Exception as e:
        session.rollback()
        session.close()
        logging.error(f"Ошибка при создании заявки: {e}")
        await message.answer(
            "❌ Произошла ошибка при отправке заявки.\n"
            "Попробуйте позже или напишите менеджеру напрямую: @KosmossShop_Supp",
            reply_markup=main_menu()
        )
        await state.clear()
        await state.set_state(ShopStates.browsing)

# ==================== ОТВЕТ АДМИНА НА ЗАЯВКУ ====================
@dp.callback_query(F.data.startswith("reply_ticket_"))
async def reply_to_ticket(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    parts = callback.data.split("_")
    ticket_id = int(parts[2])
    user_id = int(parts[3])
    
    await state.update_data(
        reply_ticket_id=ticket_id,
        reply_user_id=user_id
    )
    
    await callback.message.answer(
        f"✉️ *Ответ на заявку #{ticket_id}*\n\n"
        f"Введите сообщение для пользователя:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_panel", style="danger")]
        ])
    )
    await state.set_state(ShopStates.admin_reply_ticket)
    await callback.answer()

@dp.message(ShopStates.admin_reply_ticket)
async def process_admin_reply(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    
    data = await state.get_data()
    ticket_id = data.get('reply_ticket_id')
    user_id = data.get('reply_user_id')
    
    if not ticket_id or not user_id:
        await message.answer("❌ Ошибка: данные заявки не найдены", reply_markup=admin_menu())
        await state.clear()
        return
    
    if not message.text or len(message.text.strip()) == 0:
        await message.answer(
            "❌ Сообщение не может быть пустым!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отменить", callback_data="admin_panel", style="danger")]
            ])
        )
        return
    
    try:
        session = Session()
        ticket = session.query(SupportTicket).get(ticket_id)
        if ticket:
            ticket.status = 'answered'
            ticket.answered_at = datetime.now()
            ticket.answer = message.text.strip()
            session.commit()
        session.close()
        
        try:
            await bot.send_message(
                user_id,
                f"📨 *Ответ на вашу заявку #{ticket_id}*\n\n"
                f"Сообщение от поддержки:\n{message.text.strip()}\n\n"
                f"Если у вас остались вопросы, создайте новую заявку.",
                parse_mode="Markdown",
                reply_markup=main_menu()
            )
            await message.answer(
                f"✅ Ответ отправлен пользователю!\n"
                f"🆔 Заявка #{ticket_id} помечена как обработанная.",
                reply_markup=admin_menu()
            )
        except Exception as e:
            logging.error(f"Не удалось отправить ответ пользователю {user_id}: {e}")
            await message.answer(
                f"⚠️ Не удалось отправить сообщение пользователю.\n"
                f"Возможно, пользователь заблокировал бота.\n"
                f"Заявка #{ticket_id} помечена как обработанная.",
                reply_markup=admin_menu()
            )
        
        await state.clear()
        
    except Exception as e:
        logging.error(f"Ошибка при обработке ответа на заявку: {e}")
        await message.answer(
            "❌ Произошла ошибка при отправке ответа.",
            reply_markup=admin_menu()
        )
        await state.clear()

# ==================== ПРОСМОТР ВСЕХ ЗАЯВОК (АДМИН) ====================
@dp.callback_query(F.data == "admin_tickets")
async def admin_tickets(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    
    session = Session()
    tickets = session.query(SupportTicket).filter_by(status='open').order_by(SupportTicket.created_at.desc()).all()
    session.close()
    
    if not tickets:
        await callback.message.edit_text(
            "📋 *Заявки в поддержку*\n\n✅ Нет открытых заявок.",
            parse_mode="Markdown",
            reply_markup=admin_menu()
        )
        await callback.answer()
        return
    
    text = "📋 *Открытые заявки:*\n\n"
    for ticket in tickets:
        user = session.query(User).get(ticket.user_id)
        username = user.first_name if user else "Неизвестный"
        text += f"🆔 #{ticket.id} | {username} | {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"📝 {ticket.message[:50]}...\n\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_tickets", style="primary")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel", style="danger")]
        ])
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

# ==================== АДМИН-ПАНЕЛЬ ====================
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

# ==================== ДОБАВЛЕНИЕ КАТЕГОРИИ ====================
@dp.callback_query(F.data == "admin_add_category")
async def admin_add_category(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    await callback.message.edit_text(
        "📂 *Добавление категории*\n\nВведите *название категории*:",
        parse_mode="Markdown",
        reply_markup=cancel_menu()
    )
    await state.set_state(ShopStates.admin_add_category)
    await callback.answer()

@dp.message(ShopStates.admin_add_category)
async def process_add_category(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    category_name = message.text.strip()
    if not category_name:
        await message.answer("❌ Название не может быть пустым!")
        return

    session = Session()
    existing = session.query(Category).filter_by(name=category_name).first()
    if existing:
        await message.answer(f"❌ Категория '{category_name}' уже существует!", reply_markup=admin_menu())
        session.close()
        await state.set_state(ShopStates.browsing)
        return

    category = Category(name=category_name)
    session.add(category)
    session.commit()
    session.close()

    await message.answer(f"✅ Категория '{category_name}' создана!", reply_markup=admin_menu())
    await state.set_state(ShopStates.browsing)

# ==================== ДОБАВЛЕНИЕ ТОВАРА ====================
@dp.callback_query(F.data == "admin_add_product")
async def admin_add_product(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    session = Session()
    categories = session.query(Category).all()
    session.close()

    if not categories:
        await callback.message.edit_text(
            "❌ Нет категорий!\nСначала добавьте категорию через админ-панель.",
            reply_markup=admin_menu()
        )
        await callback.answer()
        return

    cat_list = "\n".join([f"• {cat.id}: {cat.name}" for cat in categories])
    await callback.message.edit_text(
        f"➕ *Добавление товара* (шаг 1/5)\n\n📂 *Доступные категории:*\n{cat_list}\n\nВведите *ID категории*:",
        parse_mode="Markdown",
        reply_markup=cancel_menu()
    )
    await state.set_state(ShopStates.admin_add_product_category)
    await callback.answer()

@dp.message(ShopStates.admin_add_product_category)
async def process_add_product_category(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        category_id = int(message.text.strip())
        session = Session()
        category = session.query(Category).get(category_id)
        session.close()

        if not category:
            await message.answer("❌ Категория не найдена! Попробуйте снова:", reply_markup=cancel_menu())
            return

        await state.update_data(category_id=category_id)
        await message.answer(
            f"✅ Категория выбрана: {category.name}\n\n➕ *Добавление товара* (шаг 2/5)\n\nВведите *название товара*:",
            parse_mode="Markdown",
            reply_markup=cancel_menu()
        )
        await state.set_state(ShopStates.admin_add_product_name)
    except ValueError:
        await message.answer("❌ Введите число (ID категории):", reply_markup=cancel_menu())

@dp.message(ShopStates.admin_add_product_name)
async def process_add_product_name(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    product_name = message.text.strip()
    if not product_name:
        await message.answer("❌ Название не может быть пустым!", reply_markup=cancel_menu())
        return

    await state.update_data(product_name=product_name)
    await message.answer(
        f"➕ *Добавление товара* (шаг 3/5)\n\nВведите *описание товара*:",
        parse_mode="Markdown",
        reply_markup=cancel_menu()
    )
    await state.set_state(ShopStates.admin_add_product_description)

@dp.message(ShopStates.admin_add_product_description)
async def process_add_product_description(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(product_description=message.text)
    await message.answer(
        f"➕ *Добавление товара* (шаг 4/5)\n\nВведите *цену* товара (в $):\nПример: `10`, `15.5`, `100`",
        parse_mode="Markdown",
        reply_markup=cancel_menu()
    )
    await state.set_state(ShopStates.admin_add_product_price)

@dp.message(ShopStates.admin_add_product_price)
async def process_add_product_price(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        price = float(message.text.replace(',', '.'))
        if price < 0:
            raise ValueError
        await state.update_data(product_price=price)
        await message.answer(
            f"➕ *Добавление товара* (шаг 5/5)\n\nВведите *количество* товара (в наличии):",
            parse_mode="Markdown",
            reply_markup=cancel_menu()
        )
        await state.set_state(ShopStates.admin_add_product_stock)
    except ValueError:
        await message.answer("❌ Введите корректную цену (число):", reply_markup=cancel_menu())

@dp.message(ShopStates.admin_add_product_stock)
async def process_add_product_stock(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    try:
        stock = int(message.text.strip())
        if stock < 0:
            raise ValueError

        data = await state.get_data()
        session = Session()

        product = Product(
            name=data['product_name'],
            description=data['product_description'],
            price=data['product_price'],
            stock=stock,
            category_id=data['category_id']
        )
        session.add(product)
        session.commit()

        category = session.query(Category).get(data['category_id'])
        session.close()

        await message.answer(
            f"✅ *Товар добавлен!*\n\n"
            f"📦 Название: {data['product_name']}\n"
            f"📂 Категория: {category.name}\n"
            f"💰 Цена: {data['product_price']}$\n"
            f"📦 В наличии: {stock} шт.\n\n"
            f"📸 Чтобы добавить фото, используйте команду /add_photo <id_товара>",
            parse_mode="Markdown",
            reply_markup=admin_menu()
        )
        await state.clear()
        await state.set_state(ShopStates.browsing)

    except ValueError:
        await message.answer("❌ Введите целое число (количество):", reply_markup=cancel_menu())

# ==================== ДОБАВЛЕНИЕ ФОТО К ТОВАРУ ====================
@dp.message(Command("add_photo"))
async def add_photo_command(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("❌ Использование: /add_photo <id_товара>\nПример: /add_photo 1")
        return

    try:
        product_id = int(args[1])
        await state.update_data(product_id=product_id)
        await message.answer(
            f"📸 *Добавление фото к товару ID: {product_id}*\n\nОтправьте фото:",
            parse_mode="Markdown",
            reply_markup=cancel_menu()
        )
        await state.set_state(ShopStates.admin_add_product_photo)
    except ValueError:
        await message.answer("❌ Введите число (ID товара)")

@dp.message(ShopStates.admin_add_product_photo)
async def process_add_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if not message.photo:
        await message.answer("❌ Отправьте фото!", reply_markup=cancel_menu())
        return

    data = await state.get_data()
    product_id = data.get('product_id')

    session = Session()
    product = session.query(Product).get(product_id)
    if not product:
        await message.answer("❌ Товар не найден!", reply_markup=admin_menu())
        session.close()
        await state.clear()
        await state.set_state(ShopStates.browsing)
        return

    product.photo_id = message.photo[-1].file_id
    session.commit()
    session.close()

    await message.answer(f"✅ Фото добавлено к товару ID: {product_id}!", reply_markup=admin_menu())
    await state.clear()
    await state.set_state(ShopStates.browsing)

# ==================== АДМИН-ОБРАБОТЧИКИ ====================
@dp.callback_query(F.data == "admin_mailing")
async def admin_mailing(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    await callback.message.edit_text("📨 *Рассылка*\n\nОтправьте сообщение для рассылки:", parse_mode="Markdown", reply_markup=cancel_menu())
    await state.set_state(ShopStates.admin_mailing)
    await callback.answer()

@dp.message(ShopStates.admin_mailing)
async def process_admin_mailing(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    session = Session()
    users = session.query(User).all()
    session.close()

    success = 0
    for user in users:
        try:
            await bot.send_message(user.telegram_id, message.text)
            success += 1
            await asyncio.sleep(0.05)
        except:
            pass

    await message.answer(f"✅ Рассылка завершена!\n📤 Отправлено: {success}", reply_markup=admin_menu())
    await state.set_state(ShopStates.browsing)

@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    session = Session()
    users = session.query(User).all()
    session.close()

    if not users:
        await callback.message.edit_text("📊 Пользователей пока нет.", reply_markup=admin_menu())
        await callback.answer()
        return

    text = "👥 *Список пользователей:*\n\n"
    session = Session()
    for user in users:
        orders_count = session.query(Order).filter_by(user_id=user.id).count()
        text += f"🆔 {user.telegram_id} | {user.first_name or 'Без имени'} | 💰 {user.balance}$ | 📦 {orders_count} покупок\n"
    session.close()

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return

    session = Session()
    users_count = session.query(User).count()
    orders_count = session.query(Order).count()
    paid_orders = session.query(Order).filter_by(status='paid').count()
    total_revenue = session.query(Order).filter_by(status='paid').with_entities(func.sum(Order.total)).scalar() or 0
    session.close()

    await callback.message.edit_text(
        f"📊 *Статистика*\n\n"
        f"👥 Всего пользователей: {users_count}\n"
        f"📦 Всего заказов: {orders_count}\n"
        f"✅ Оплаченных: {paid_orders}\n"
        f"💰 Выручка: {round(total_revenue, 2)}$",
        parse_mode="Markdown",
        reply_markup=admin_menu()
    )
    await callback.answer()

# ==================== КОМАНДА /CANCEL ====================
@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(ShopStates.browsing)
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=main_menu()
    )

# ==================== НЕИЗВЕСТНЫЕ ====================
@dp.message()
async def unknown(message: types.Message):
    await message.answer("Используйте кнопки для навигации.", reply_markup=main_menu())

# ==================== ЗАПУСК ====================
async def main():
    await bot.delete_webhook()
    print("🚀 БОТ ЗАПУЩЕН!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
