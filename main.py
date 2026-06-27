import logging
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import func

from config import BOT_TOKEN, ADMIN_IDS
from database import Session, User, Category, Product, Order, SupportTicket, init_db
from keyboards import *
from states import ShopStates
from crypto_pay import create_invoice
from admin import is_admin, show_admin_panel, start_mailing, process_mailing, add_product_start, process_add_product_category, process_add_product_name, process_add_product_description, process_add_product_price, process_add_product_stock, process_add_product_photo, add_category_command, show_users, show_stats

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

init_db()

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
        reply_markup=welcome_keyboard()
    )


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
            reply_markup=back_to_menu_keyboard()
        )
        await callback.answer()
        return

    text = "📂 *Наши товары:*\n\n"
    for p in products:
        stock_emoji = "🟢" if p.stock > 0 else "🔴"
        text += f"• {p.name} | {p.price}$ | {stock_emoji} {p.stock}шт\n"

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=products_list_keyboard(products)
    )
    await callback.answer()


def products_list_keyboard(products):
    buttons = []
    for p in products:
        buttons.append([
            InlineKeyboardButton(
                text=f"{p.name} | {p.price}$",
                callback_data=f"product_{p.id}",
                style="primary" if p.stock > 0 else "danger"
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад в меню",
            callback_data="back_to_welcome",
            style="danger"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== ТОВАР ====================
@dp.callback_query(F.data.startswith("product_"))
async def show_product(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])

    session = Session()
    product = session.query(Product).get(product_id)
    session.close()

    if not product:
        await callback.answer("Товар не найден")
        return

    text = (
        f"📦 *{product.name}*\n\n"
        f"{product.description or 'Описание отсутствует'}\n\n"
        f"💰 Цена: {product.price}$\n"
        f"📦 В наличии: {product.stock} шт."
    )

    in_stock = product.stock > 0

    if product.photo_id:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=product.photo_id,
            caption=text,
            parse_mode="Markdown",
            reply_markup=product_detail_keyboard(product_id, in_stock)
        )
    else:
        await callback.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=product_detail_keyboard(product_id, in_stock)
        )
    await callback.answer()


# ==================== ПОКУПКА ====================
@dp.callback_query(F.data.startswith("buy_now_"))
async def buy_product(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[2])

    session = Session()
    product = session.query(Product).get(product_id)
    user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
    session.close()

    if not product or product.stock <= 0:
        await callback.answer("❌ Товар отсутствует!")
        return

    if user.balance < product.price:
        await callback.message.edit_text(
            f"❌ *Недостаточно средств!*\n\n"
            f"💰 Ваш баланс: {user.balance}$\n"
            f"💵 Стоимость товара: {product.price}$\n\n"
            f"Пополните баланс в профиле.",
            parse_mode="Markdown",
            reply_markup=product_detail_keyboard(product_id, True)
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"🛒 *Подтверждение покупки*\n\n"
        f"📦 Товар: {product.name}\n"
        f"💰 Цена: {product.price}$\n"
        f"💳 Ваш баланс: {user.balance}$\n\n"
        f"Подтвердите покупку:",
        parse_mode="Markdown",
        reply_markup=buy_confirm_keyboard(product_id)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("confirm_buy_"))
async def confirm_buy(callback: types.CallbackQuery):
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

    order = Order(
        user_id=user.id,
        product_id=product.id,
        quantity=1,
        total=product.price,
        status='paid'
    )
    session.add(order)
    session.commit()
    session.close()

    await callback.message.edit_text(
        f"✅ *Покупка успешна!*\n\n"
        f"📦 Товар: {product.name}\n"
        f"💰 Стоимость: {product.price}$\n"
        f"💳 Остаток баланса: {user.balance}$\n\n"
        f"⏳ Ожидайте выдачу товара в течение 5 минут.",
        parse_mode="Markdown",
        reply_markup=back_to_menu_keyboard()
    )
    await callback.answer("🎉 Поздравляем с покупкой!")


# ==================== ПРОФИЛЬ ====================
@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
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
        reply_markup=profile_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "my_orders")
async def my_orders(callback: types.CallbackQuery):
    session = Session()
    user = session.query(User).filter_by(telegram_id=callback.from_user.id).first()
    orders = session.query(Order).filter_by(user_id=user.id).order_by(Order.created_at.desc()).limit(10).all()
    session.close()

    if not orders:
        await callback.message.edit_text(
            "📦 У вас пока нет покупок.",
            reply_markup=back_to_profile_keyboard()
        )
        await callback.answer()
        return

    text = "📦 *Ваши последние покупки:*\n\n"
    for order in orders:
        status_emoji = "✅" if order.status == "paid" else "⏳"
        text += f"{status_emoji} {order.product.name} — {order.total}$\n"

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_profile_keyboard())
    await callback.answer()


# ==================== ПОПОЛНЕНИЕ ====================
@dp.callback_query(F.data == "deposit")
async def deposit_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "💰 *Пополнение баланса*\n\n"
        "Введите сумму в долларах (мин. 7$)\n"
        "Пополнение происходит через Crypto Bot\n\n"
        "⌨️ *Пример:* `10`, `15.5`, `100`",
        parse_mode="Markdown",
        reply_markup=cancel_deposit_keyboard()
    )
    await state.set_state(ShopStates.deposit_amount)
    await callback.answer()


@dp.message(ShopStates.deposit_amount)
async def process_deposit_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))

        if amount < 7:
            await message.answer(
                "❌ Минимальная сумма пополнения — 7$\n"
                "Пожалуйста, введите сумму от 7$",
                reply_markup=cancel_deposit_keyboard()
            )
            return

        invoice = await create_invoice(message.from_user.id, amount)

        if not invoice:
            await message.answer(
                "❌ Ошибка создания счёта. Попробуйте позже.",
                reply_markup=back_to_profile_keyboard()
            )
            await state.set_state(ShopStates.browsing)
            return

        await message.answer(
            f"💳 *Счёт создан!*\n\n"
            f"💰 Сумма: {amount} USDT\n"
            f"🆔 Номер счёта: {invoice.invoice_id}\n\n"
            f"🔗 Ссылка для оплаты:\n"
            f"{invoice.bot_invoice_url}\n\n"
            f"⏳ Счёт действителен 60 минут\n"
            f"📱 После оплаты баланс пополнится автоматически",
            parse_mode="Markdown",
            reply_markup=back_to_profile_keyboard()
        )
        await state.set_state(ShopStates.browsing)

    except ValueError:
        await message.answer(
            "❌ Введите число\nПример: `10` или `15.5`",
            parse_mode="Markdown",
            reply_markup=cancel_deposit_keyboard()
        )
    except Exception as e:
        await message.answer(
            "❌ Ошибка создания счёта\nПопробуйте позже",
            reply_markup=back_to_profile_keyboard()
        )
        print(f"Ошибка: {e}")
        await state.set_state(ShopStates.browsing)


# ==================== ИНФОРМАЦИЯ ====================
@dp.callback_query(F.data == "info")
async def show_info(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ *Информация о боте*\n\n"
        "🏪 Название магазина: *Kosmos Shop*\n"
        "📅 Создан: 14.02.2026\n"
        "📦 Продано товаров за Май: 183 товаров\n"
        "🆘 Тех поддержка: @KosmossShop_Supp\n\n"
        "⭐️ Спасибо, что выбираете нас!",
        parse_mode="Markdown",
        reply_markup=back_to_menu_keyboard()
    )
    await callback.answer()


# ==================== ПОДДЕРЖКА ====================
@dp.callback_query(F.data == "support")
async def show_support(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔄 *Замены и Техподдержка*\n\n"
        "❓ Что-то случилось? Вы можете тут подать заявку\n"
        "или написать нашему менеджеру.\n\n"
        "👨‍💼 Работает 24/7, ответит и решит проблему:\n"
        "• Технические проблемы — в течение часа\n"
        "• Остальные вопросы — в течение 25 минут\n\n"
        "📱 @KosmossShop_Supp\n\n"
        "✍️ Или напишите, что случилось👇",
        parse_mode="Markdown",
        reply_markup=support_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "submit_ticket")
async def submit_ticket(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 *Подача заявки*\n\n"
        "Опишите вашу проблему подробно.\n"
        "Мы свяжемся с вами в ближайшее время.\n\n"
        "❌ Для отмены отправьте /cancel",
        parse_mode="Markdown"
    )
    await state.set_state(ShopStates.support_ticket)
    await callback.answer()


@dp.message(ShopStates.support_ticket)
async def process_ticket(message: types.Message, state: FSMContext):
    session = Session()
    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    ticket = SupportTicket(
        user_id=user.id,
        message=message.text,
        status='open'
    )
    session.add(ticket)
    session.commit()

    for admin_id in ADMIN_IDS:
        await bot.send_message(
            admin_id,
            f"📨 *Новая заявка в поддержку!*\n\n"
            f"👤 Пользователь: {message.from_user.first_name}\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"📝 Сообщение:\n{message.text}",
            parse_mode="Markdown"
        )

    session.close()

    await message.answer(
        "✅ *Заявка отправлена!*\n\n"
        "Мы свяжемся с вами в ближайшее время.",
        parse_mode="Markdown",
        reply_markup=ticket_sent_keyboard()
    )
    await state.set_state(ShopStates.browsing)


# ==================== АДМИН-ПАНЕЛЬ ====================
@dp.message(Command("adm"))
async def admin_panel(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    await show_admin_panel(message)
    await state.set_state(ShopStates.browsing)


@dp.message(Command("add_balance"))
async def add_balance(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return

    args = message.text.split()
    if len(args) < 3:
        await message.answer("❌ Использование: /add_balance <telegram_id> <сумма>\nПример: /add_balance 595471006 10")
        return

    try:
        user_id = int(args[1])
        amount = float(args[2])

        session = Session()
        user = session.query(User).filter_by(telegram_id=user_id).first()

        if user:
            user.balance += amount
            session.commit()
            await message.answer(f"✅ Баланс пользователя {user_id} пополнен на {amount}$\n💰 Новый баланс: {user.balance}$")

            try:
                await bot.send_message(
                    user_id,
                    f"💰 Ваш баланс пополнен на {amount}$ администратором!\n💎 Новый баланс: {user.balance}$"
                )
            except:
                pass
        else:
            await message.answer("❌ Пользователь не найден")
        session.close()
    except:
        await message.answer("❌ Ошибка! Используй: /add_balance <id> <сумма>")


@dp.callback_query(F.data == "admin_mailing")
async def admin_mailing(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    await start_mailing(callback, state)


@dp.message(ShopStates.admin_mailing)
async def process_admin_mailing(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    await process_mailing(message, state, bot)


@dp.callback_query(F.data == "admin_add_product")
async def admin_add_product(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    await add_product_start(callback, state)


@dp.message(ShopStates.admin_add_product_category)
async def admin_add_product_category(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await process_add_product_category(message, state)


@dp.message(ShopStates.admin_add_product_name)
async def admin_add_product_name(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await process_add_product_name(message, state)


@dp.message(ShopStates.admin_add_product_description)
async def admin_add_product_description(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await process_add_product_description(message, state)


@dp.message(ShopStates.admin_add_product_price)
async def admin_add_product_price(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await process_add_product_price(message, state)


@dp.message(ShopStates.admin_add_product_stock)
async def admin_add_product_stock(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await process_add_product_stock(message, state)


@dp.message(ShopStates.admin_add_product_photo)
async def admin_add_product_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await process_add_product_photo(message, state, bot)


@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    await show_users(callback)


@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа")
        return
    await show_stats(callback)


@dp.message(Command("add_category"))
async def add_category(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    await add_category_command(message)


# ==================== НАЗАД ====================
@dp.callback_query(F.data == "back_to_welcome")
async def back_to_welcome(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ShopStates.browsing)
    await callback.message.delete()
    await callback.message.answer(
        "🚀 *Салют*, ты попал в *Kosmos Shop*!\n\n"
        "✨ Идеальный вариант для покупки *логов Gu* 🔥\n"
        "Также у нас есть много чего другого!\n\n"
        "🌟 Осваивайся, удачного ворка! 💪",
        parse_mode="Markdown",
        reply_markup=welcome_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_profile")
async def back_to_profile_callback(callback: types.CallbackQuery):
    await show_profile(callback)
    await callback.answer()


@dp.callback_query(F.data == "no_stock")
async def no_stock(callback: types.CallbackQuery):
    await callback.answer("❌ Товара нет в наличии!")


# ==================== НЕИЗВЕСТНЫЕ ====================
@dp.message()
async def unknown_message(message: types.Message):
    await message.answer(
        "Используйте кнопки для навигации.",
        reply_markup=welcome_keyboard()
    )


# ==================== ЗАПУСК ====================
async def main():
    print("🚀 Бот Kosmos Shop запускается в режиме polling...")
    print("✅ Бот готов к работе!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
