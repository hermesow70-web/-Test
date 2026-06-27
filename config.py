import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CRYPTO_TOKEN = os.getenv('CRYPTO_TOKEN')
ADMIN_IDS = [int(os.getenv('ADMIN_IDS'))]
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://kosmos-shop.bothost.net/webhook')
