from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


# ==================== ОБЫЧНЫЕ КНОПКИ ДЛЯ МЕНЮ ====================
def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📂 Категории")],
            [KeyboardButton(text="ℹ️ Информация")],
            [KeyboardButton(text="🔄 Техподдержка")],
            [KeyboardButton(text="👤 Профиль")]
        ],
        resize_keyboard=True
    )

def back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )


# ==================== ИНЛАЙН КНОПКИ ====================
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
            callback_data="back_to_welcome",
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
                callback_data="back_to_welcome",
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
                text="◀️ Назад",
                callback_data="back_to_welcome",
                style="danger"
            )
        ]
    ])


def cancel_deposit_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❌ Отменить пополнение",
                callback_data="back_to_welcome",
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
                text="◀️ Назад",
                callback_data="back_to_welcome",
                style="danger"
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
                callback_data="back_to_welcome",
                style="primary"
            )
        ]
    ])
