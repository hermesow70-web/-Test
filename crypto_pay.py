from aiocryptopay import AioCryptoPay, Networks
from config import CRYPTO_TOKEN

crypto = AioCryptoPay(token=CRYPTO_TOKEN, network=Networks.MAIN_NET)


async def create_invoice(user_id: int, amount: float, asset: str = 'USDT'):
    """Создание счёта для пополнения"""
    try:
        invoice = await crypto.create_invoice(
            asset=asset,
            amount=amount,
            description=f'Пополнение баланса Kosmos Shop',
            payload=str(user_id)
        )
        return invoice
    except Exception as e:
        print(f"Ошибка создания счёта: {e}")
        return None
