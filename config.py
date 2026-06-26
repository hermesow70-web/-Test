import os
from dotenv import load_dotenv

load_dotenv()

# Токены
BOT_TOKEN = "8645391239:AAGvuHc6CMN3c22g9M-jpNZ4hIGkYrTv_6Q"
CRYPTO_TOKEN = "601388:AAzYuTp7GYpzv4kQvd9m7JLBNUV3sQ183JR"

# ID админа
ADMIN_IDS = [595471006]

# Секретный токен для вебхука
WEBHOOK_SECRET = "KosmosShopSecretKey2026"

# URL для вебхука (заменишь на свой после деплоя на BotHost)
# Пример: https://kosmos-shop.bothost.net
WEBHOOK_URL = "https://kosmos-shop.bothost.net/webhook"
CRYPTO_WEBHOOK_URL = "https://kosmos-shop.bothost.net/crypto-webhook"
