import asyncio
from aiohttp import web
from aiocryptopay import AioCryptoPay, Networks
from aiocryptopay.models.update import Update

from config import BOT_TOKEN, CRYPTO_TOKEN, ADMIN_IDS
from database import Session, User

crypto = AioCryptoPay(token=CRYPTO_TOKEN, network=Networks.MAIN_NET)
app = web.Application()


@crypto.pay_handler()
async def handle_payment(update: Update, app):
    """Обработчик успешной оплаты"""
    try:
        user_id = int(update.payload)
        amount = float(update.amount)
        asset = update.asset

        print(f"💰 Получен платеж от {user_id} на {amount} {asset}")

        session = Session()
        user = session.query(User).filter_by(telegram_id=user_id).first()

        if user:
            old_balance = user.balance
            user.balance += amount
            session.commit()

            from aiogram import Bot
            bot = Bot(token=BOT_TOKEN)

            await bot.send_message(
                user_id,
                f"✅ *Баланс пополнен!*\n\n"
                f"💰 Сумма: {amount} {asset}\n"
                f"💳 Старый баланс: {old_balance}$\n"
                f"💎 Новый баланс: {user.balance}$",
                parse_mode="Markdown"
            )

            for admin_id in ADMIN_IDS:
                await bot.send_message(
                    admin_id,
                    f"💵 *Пополнение баланса*\n\n"
                    f"👤 Пользователь: {user.first_name}\n"
                    f"🆔 ID: {user_id}\n"
                    f"💰 Сумма: {amount} {asset}\n"
                    f"💎 Новый баланс: {user.balance}$",
                    parse_mode="Markdown"
                )

            print(f"✅ Баланс пользователя {user_id} пополнен на {amount} {asset}")
        else:
            print(f"❌ Пользователь {user_id} не найден")

        session.close()

    except Exception as e:
        print(f"❌ Ошибка обработки платежа: {e}")


app.add_routes([web.post('/crypto-webhook', crypto.get_updates)])


async def start_webhook_server():
    """Запуск веб-сервера для вебхука"""
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=8080)
    await site.start()
    print("✅ Веб-сервер запущен на порту 8080")

    while True:
        await asyncio.sleep(3600)
