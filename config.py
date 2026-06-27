import os
from dotenv import load_dotenv

# Пытаемся загрузить из .env
load_dotenv()

# Если .env не работает — используем значения напрямую
BOT_TOKEN = os.getenv('BOT_TOKEN') or "8645391239:AAGvuHc6CMN3c22g9M-jpNZ4hIGkYrTv_6Q"
CRYPTO_TOKEN = os.getenv('CRYPTO_TOKEN') or "601388:AAzYuTp7GYpzv4kQvd9m7JLBNUV3sQ183JR"
ADMIN_IDS = [int(os.getenv('ADMIN_IDS', '595471006'))]
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET') or "KosmosShopSecretKey2026"
WEBHOOK_URL = os.getenv('WEBHOOK_URL') or "https://kosmos-shop.bothost.net/webhook"
