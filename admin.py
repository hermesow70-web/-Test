import asyncio
import csv
import io
from datetime import datetime

from aiogram import types
from aiogram.fsm.context import FSMContext
from sqlalchemy import func

from database import Session, User, Product, Category, Order
from keyboards import admin_keyboard
from states import ShopStates


def is_admin(user_id: int) -> bool:
    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()
    session.close()
    return user and user.is_admin


async def show_admin_panel(message: types.Message, edit: bool = False):
    session = Session()
    users_count = session.query(User).count()
    orders_count = session.query(Order).count()
    total_revenue = session.query(Order).filter_by(status='paid').with_entities(
        func.sum(Order.total)
    ).scalar() or 0
    session.close()

    text = (
        f"🔐 *Админ-панель*\n\n"
        f"👥 Всего пользователей: {users_count}\n"
        f"📦 Всего заказов: {orders_count}\n"
        f"💰 Общая выручка: {round(total_revenue, 2)}$\n\n"
        f"Выберите действие:"
    )

    if edit:
        await message.edit_text(text, parse_mode="Markdown", reply_markup=admin_keyboard())
    else:
        await message.answer(text, parse_mode="Markdown", reply_markup=admin_keyboard())


async def start_mailing(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📨 *Рассылка*\n\n"
        "Отправьте сообщение, которое хотите разослать всем пользователям.\n"
        "Это может быть текст, фото, видео или любой другой файл.\n\n"
        "⏳ После отправки начнется рассылка.\n"
        "❌ Для отмены отправьте /cancel",
        parse_mode="Markdown"
    )
    await state.set_state(ShopStates.admin_mailing)
    await callback.answer()


async def process_mailing(message: types.Message, state: FSMContext, bot):
    await message.answer("📨 Начинаю рассылку... Это может занять некоторое время.")

    session = Session()
    users = session.query(User).all()
    session.close()

    success = 0
    failed = 0

    for user in users:
        try:
            if message.text:
                await bot.send_message(user.telegram_id, message.text)
            elif message.photo:
                await bot.send_photo(user.telegram_id, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                await bot.send_video(user.telegram_id, message.video.file_id, caption=message.caption)
            elif message.document:
                await bot.send_document(user.telegram_id, message.document.file_id, caption=message.caption)
            success += 1
        except:
            failed += 1
        await asyncio.sleep(0.05)

    await message.answer(
        f"✅ Рассылка завершена!\n"
        f"📤 Отправлено: {success}\n"
        f"❌ Не доставлено: {failed}"
    )
    await state.set_state(ShopStates.browsing)
    await show_admin_panel(message)


async def add_product_start(callback: types.CallbackQuery, state: FSMContext):
    session = Session()
    categories = session.query(Category).all()
    session.close()

    if not categories:
        await callback.message.edit_text(
            "❌ Сначала создайте категорию!\nИспользуйте /add_category <название>"
        )
        return

    cat_list = "\n".join([f"• {cat.id}: {cat.name}" for cat in categories])

    await callback.message.edit_text(
        f"➕ *Добавление товара*\n\n"
        f"📂 *Доступные категории:*\n{cat_list}\n\n"
        f"Введите *ID категории* для товара:",
        parse_mode="Markdown"
    )
    await state.set_state(ShopStates.admin_add_product_category)
    await callback.answer()


async def process_add_product_category(message: types.Message, state: FSMContext):
    try:
        category_id = int(message.text)
        session = Session()
        category = session.query(Category).get(category_id)
        session.close()

        if not category:
            await message.answer("❌ Категория не найдена. Попробуйте снова:")
            return

        await state.update_data(category_id=category_id)
        await message.answer(f"📂 Категория: {category.name}\n\nВведите *название товара*:", parse_mode="Markdown")
        await state.set_state(ShopStates.admin_add_product_name)
    except ValueError:
        await message.answer("❌ Введите число (ID категории)")


async def process_add_product_name(message: types.Message, state: FSMContext):
    await state.update_data(product_name=message.text)
    await message.answer("Введите *описание товара*:", parse_mode="Markdown")
    await state.set_state(ShopStates.admin_add_product_description)


async def process_add_product_description(message: types.Message, state: FSMContext):
    await state.update_data(product_description=message.text)
    await message.answer("Введите *цену* товара (в $):", parse_mode="Markdown")
    await state.set_state(ShopStates.admin_add_product_price)


async def process_add_product_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text.replace(',', '.'))
        if price < 0:
            raise ValueError
        await state.update_data(product_price=price)
        await message.answer("Введите *количество* товара (в наличии):", parse_mode="Markdown")
        await state.set_state(ShopStates.admin_add_product_stock)
    except ValueError:
        await message.answer("❌ Введите корректную цену (число):")


async def process_add_product_stock(message: types.Message, state: FSMContext):
    try:
        stock = int(message.text)
        if stock < 0:
            raise ValueError
        await state.update_data(product_stock=stock)
        await message.answer("📸 Отправьте *фото* товара (или отправьте /skip чтобы пропустить):", parse_mode="Markdown")
        await state.set_state(ShopStates.admin_add_product_photo)
    except ValueError:
        await message.answer("❌ Введите корректное количество (целое число):")


async def process_add_product_photo(message: types.Message, state: FSMContext, bot):
    if message.text and message.text == "/skip":
        await save_product(state, bot, message, photo_id=None)
        return

    if message.photo:
        photo_id = message.photo[-1].file_id
        await save_product(state, bot, message, photo_id)
    else:
        await message.answer("❌ Отправьте фото или /skip чтобы пропустить")


async def save_product(state: FSMContext, bot, message, photo_id=None):
    data = await state.get_data()

    session = Session()
    product = Product(
        name=data['product_name'],
        description=data['product_description'],
        price=data['product_price'],
        stock=data['product_stock'],
        category_id=data['category_id'],
        photo_id=photo_id
    )
    session.add(product)
    session.commit()

    category = session.query(Category).get(data['category_id'])
    session.close()

    await message.answer(
        f"✅ *Товар добавлен!*\n\n"
        f"📦 {data['product_name']}\n"
        f"📂 Категория: {category.name}\n"
        f"💰 Цена: {data['product_price']}$\n"
        f"📦 В наличии: {data['product_stock']} шт.",
        parse_mode="Markdown"
    )
    await state.clear()
    await show_admin_panel(message)


async def add_category_command(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Использование: /add_category <название категории>")
        return

    category_name = args[1]

    session = Session()
    existing = session.query(Category).filter_by(name=category_name).first()
    if existing:
        await message.answer(f"❌ Категория '{category_name}' уже существует!")
        session.close()
        return

    category = Category(name=category_name)
    session.add(category)
    session.commit()
    session.close()

    await message.answer(f"✅ Категория '{category_name}' создана!")


async def show_users(callback: types.CallbackQuery):
    session = Session()
    users = session.query(User).order_by(User.created_at.desc()).all()
    session.close()

    if not users:
        await callback.message.edit_text("📊 Пользователей пока нет.")
        return

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Telegram ID', 'Имя', 'Баланс', 'Покупок', 'Дата регистрации'])

    session = Session()
    for user in users:
        orders_count = session.query(Order).filter_by(user_id=user.id).count()
        writer.writerow([
            user.id,
            user.telegram_id,
            user.first_name or 'Не указано',
            user.balance,
            orders_count,
            user.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    session.close()

    output.seek(0)
    file = types.BufferedInputFile(
        output.getvalue().encode('utf-8'),
        filename=f'users_{datetime.now().strftime("%Y%m%d")}.csv'
    )

    await callback.message.delete()
    await callback.message.answer_document(
        document=file,
        caption=f"📊 Всего пользователей: {len(users)}"
    )
    await callback.answer()


async def show_stats(callback: types.CallbackQuery):
    session = Session()
    users_count = session.query(User).count()
    orders_count = session.query(Order).count()
    paid_orders = session.query(Order).filter_by(status='paid').count()
    total_revenue = session.query(Order).filter_by(status='paid').with_entities(
        func.sum(Order.total)
    ).scalar() or 0

    top_products = session.query(
        Product.name,
        func.sum(Order.quantity).label('total_sold')
    ).join(Order).filter(Order.status == 'paid').group_by(Product.id).order_by(
        func.sum(Order.quantity).desc()
    ).limit(5).all()
    session.close()

    text = (
        f"📊 *Статистика магазина*\n\n"
        f"👥 Всего пользователей: {users_count}\n"
        f"📦 Всего заказов: {orders_count}\n"
        f"✅ Оплаченных: {paid_orders}\n"
        f"💰 Общая выручка: {round(total_revenue, 2)}$\n\n"
        f"🏆 *Топ товаров:*\n"
    )

    if top_products:
        for i, (name, sold) in enumerate(top_products, 1):
            text += f"{i}. {name} — {sold} шт.\n"
    else:
        text += "Нет продаж\n"

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_keyboard())
    await callback.answer()
