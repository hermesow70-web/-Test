from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Category, Product, Session


def welcome_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📂 Категории",
                callback_data="categories",
                style="success"
            )
        ],
        [
            InlineKeyboardButton(
                text="ℹ️ Информация",
                callback_data="info",
                style="primary"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Замены/Тех Поддержка",
                callback_data="support",
                style="danger"
            )
        ],
        [
            InlineKeyboardButton(
                text="👤 Профиль",
                callback_data="profile",
                style="primary"
            )
        ]
    ])


def categories_keyboard():
    session = Session()
    categories = session.query(Category).all()
    session.close()

    buttons = []
    for cat in categories:
        session = Session()
        count = session.query(Product).filter_by(category_id=cat.id).count()
        session.close()

        buttons.append([
            InlineKeyboardButton(
                text=f"📁 {cat.name} ({count})",
                callback_data=f"category_{cat.id}",
                style="primary"
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


def products_keyboard(products, category_id):
    buttons = []
    for product in products:
        stock_emoji = "🟢" if product.stock > 0 else "🔴"
        buttons.append([
            InlineKeyboardButton(
                text=f"{product.name} | {product.price}$ | {stock_emoji} {product.stock}шт",
                callback_data=f"product_{product.id}",
                style="primary" if product.stock > 0 else "danger"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад к категориям",
            callback_data="back_to_categories",
            style="danger"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_detail_keyboard(product_id, in_stock=True):
    buttons = []

    if in_stock:
        buttons.append([
            InlineKeyboardButton(
                text="🛒 Купить",
                callback_data=f"buy_now_{product_id}",
                style="success"
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text="❌ Нет в наличии",
                callback_data="no_stock",
                style="danger"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"back_to_products_{product_id}",
            style="primary"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def buy_confirm_keyboard(product_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтвердить покупку",
                callback_data=f"confirm_buy_{product_id}",
                style="success"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Отмена",
                callback_data=f"back_to_products_{product_id}",
                style="danger"
            )
        ]
    ])


def profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💰 Пополнить баланс",
                callback_data="deposit",
                style="success"
            )
        ],
        [
            InlineKeyboardButton(
                text="📦 Мои покупки",
                callback_data="my_orders",
                style="primary"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад в меню",
                callback_data="back_to_welcome",
                style="danger"
            )
        ]
    ])


def deposit_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="◀️ Назад в профиль",
                callback_data="back_to_profile",
                style="danger"
            )
        ]
    ])


def cancel_deposit_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❌ Отменить пополнение",
                callback_data="back_to_profile",
                style="danger"
            )
        ]
    ])


def support_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📝 Подать заявку",
                callback_data="submit_ticket",
                style="primary"
            )
        ],
        [
            InlineKeyboardButton(
                text="👨‍💼 Написать менеджеру",
                url="https://t.me/KosmossShop_Supp",
                style="success"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад в меню",
                callback_data="back_to_welcome",
                style="danger"
            )
        ]
    ])


def ticket_sent_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="◀️ Назад в меню",
                callback_data="back_to_welcome",
                style="primary"
            )
        ]
    ])


def back_to_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="◀️ Назад в меню",
                callback_data="back_to_welcome",
                style="primary"
            )
        ]
    ])


def back_to_profile_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="◀️ Назад в профиль",
                callback_data="back_to_profile",
                style="primary"
            )
        ]
    ])


def back_to_categories_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="◀️ Назад к категориям",
                callback_data="back_to_categories",
                style="primary"
            )
        ]
    ])


def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📨 Рассылка",
                callback_data="admin_mailing",
                style="primary"
            )
        ],
        [
            InlineKeyboardButton(
                text="➕ Добавить товар",
                callback_data="admin_add_product",
                style="success"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Всего пользователей",
                callback_data="admin_users",
                style="primary"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data="admin_stats",
                style="primary"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Выход",
                callback_data="back_to_welcome",
                style="danger"
            )
        ]
    ])
