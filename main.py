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
        [InlineKeyboardButton(text="📂 Категории", callback_data="categories")],
        [InlineKeyboardButton(text="ℹ️ Информация", callback_data="info")],
        [InlineKeyboardButton(text="🔄 Техподдержка", callback_data="support")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ])

def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])

def support_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Подать заявку", callback_data="submit_ticket")],
        [InlineKeyboardButton(text="👨‍💼 Написать менеджеру", url="https://t.me/KosmossShop_Supp")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])

def profile_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="deposit")],
        [InlineKeyboardButton(text="📦 Мои покупки", callback_data="my_orders")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Рассылка", callback_data="admin_mailing")],
        [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="◀️ Выход", callback_data="back_to_main")]
    ])

# ==================== УНИВЕРСАЛЬНЫЙ ЛОГГЕР (ДЛЯ ОТЛАДКИ) ====================
@dp.callback_query()
async def log_all_callbacks(callback: types.CallbackQuery):
    """Логирует все нажатия - временно, для диагностики"""
    print(f"🔘 КЛИК: {callback.data} от {callback.from_user.id}")
    
    # Если это info и обработчик не сработал - обработаем здесь же
    if callback.data == "info":
        print("⚠️ Обработчик info не сработал! Обрабатываю в универсальном...")
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
        await callback.answer("✅ Информация загружена!")

# ==================== ИНФОРМАЦИЯ ====================
@dp.callback_query(F.data == "info")
async def info_handler(callback: types.CallbackQuery):
    """Обработчик кнопки Информация"""
    print(f"✅ ОСНОВНОЙ ОБРАБОТЧИК info СРАБОТАЛ!")
    
    try:
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
        await callback.answer("✅ Информация загружена!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)

# ==================== ВСЕ ОСТАЛЬНЫЕ ОБРАБОТЧИКИ ====================
# ... (ваш код)

# ==================== ЗАПУСК ====================
async def main():
    print("🚀 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
