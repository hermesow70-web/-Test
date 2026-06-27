from database import Session, User, init_db

init_db()
session = Session()
user = session.query(User).filter_by(telegram_id=595471006).first()

if user:
    user.is_admin = True
    session.commit()
    print("✅ Ты стал админом!")
else:
    print("❌ Пользователь не найден. Напиши /start в боте.")

session.close()
