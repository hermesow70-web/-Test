from aiogram.fsm.state import State, StatesGroup

class ShopStates(StatesGroup):
    browsing = State()
    deposit_amount = State()
    support_ticket = State()
    
    # Админские состояния
    admin_add_category = State()
    admin_add_product_category = State()
    admin_add_product_name = State()
    admin_add_product_description = State()
    admin_add_product_price = State()
    admin_add_product_stock = State()
    admin_add_product_photo = State()
    admin_mailing = State()
