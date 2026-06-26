import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import func

from config import BOT_TOKEN, ADMIN_IDS, WEBHOOK_URL, WEBHOOK_SECRET
from database import Session, User, Category, Product, Order, SupportTicket, init_db
from keyboards import *
from states import ShopStates
from crypto_pay import create_invoice
from admin import *
from webhook_server import start_webhook_server

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

        # Реферальная ссылка
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
    await callback.message.edit_text(
        "📂 *Категории товаров*\n\nВыберите категорию:",
        parse_mode="Markdown",
        reply_markup=categories_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("category_"))
async def show_products(callback: types.CallbackQuery):
    category_id = int(callback.data.split("_")[1])

    session = Session()
    category = session.query(Category).get(category_id)
    products = session.query(Product).filter_by(category_id=category_id).all()
    session.close()

    if not products:
        await callback.message.edit_text(
            f"📂 *{category.name}*\n\nВ этой категории пока нет товаров.",
            parse_mode="Markdown",
            reply_markup=back_to_categories_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📂 *{category.name}*\n\nВыберите товар:",
        parse_mode="Markdown",
        reply_markup=products_keyboard(products, category_id)
    )
    await callback.answer()


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
        f"🆔 ID: {callback.from_user.id}\
