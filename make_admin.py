from database import Session, User, init_db

def make_admin():
    init_db()
    session = Session()
    user = session.query(User).filter_by(telegram_id=595471006).first()
    
    if user:
        user.is_admin = True
        session.commit()
        print(f"✅ Пользователь {user.telegram_id} ({user.first_name}) стал админом!")
    else:
        print("❌ Пользователь не найден. Напиши /start в боте сначала.")
    
    session.close()

if __name__ == "__main__":
    make_admin()
