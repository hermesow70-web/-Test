from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Boolean, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()
engine = create_engine('sqlite:///shop.db', echo=False)
Session = sessionmaker(bind=engine)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String, nullable=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    balance = Column(Float, default=0.0)
    referrer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    orders = relationship('Order', back_populates='user')
    referrals = relationship('User', backref='referrer', remote_side=[id])
    tickets = relationship('SupportTicket', back_populates='user')


class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    products = relationship('Product', back_populates='category')


class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String, nullable=True)
    price = Column(Float)
    stock = Column(Integer, default=0)
    category_id = Column(Integer, ForeignKey('categories.id'))
    photo_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    category = relationship('Category', back_populates='products')
    orders = relationship('Order', back_populates='product')


class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer, default=1)
    total = Column(Float)
    status = Column(String, default='pending')  # pending, paid, delivered, cancelled
    created_at = Column(DateTime, default=datetime.now)

    user = relationship('User', back_populates='orders')
    product = relationship('Product', back_populates='orders')


class SupportTicket(Base):
    __tablename__ = 'support_tickets'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    message = Column(String)
    status = Column(String, default='open')  # open, in_progress, closed
    created_at = Column(DateTime, default=datetime.now)

    user = relationship('User', back_populates='tickets')


def init_db():
    Base.metadata.create_all(engine)

    # Создаём тестовые категории, если их нет
    session = Session()
    if session.query(Category).count() == 0:
        categories = [
            Category(name="🎮 Логи Gu", description="Логи для игр"),
            Category(name="🖥 Аксессуары", description="Игровые аксессуары"),
            Category(name="👕 Одежда", description="Мерч и одежда")
        ]
        session.add_all(categories)
        session.commit()
    session.close()
