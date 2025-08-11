from sqlalchemy import (
    Column, Integer, String, ForeignKey, Text, Boolean,
    DECIMAL, DateTime
)
from sqlalchemy.orm import relationship, DeclarativeBase, mapped_column, Mapped
from datetime import datetime
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin


class Base(DeclarativeBase):
    pass

class User(Base,UserMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(200))  # Hashed password
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="user")
    cart_items = relationship("CartItem", back_populates="user")
    addresses = relationship("Address", back_populates="user")

class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)

    subcategories = relationship("Category")
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String(150))
    description = Column(Text)
    price = Column(DECIMAL(10, 2))
    discount = Column(Integer)
    stock_quantity = Column(Integer)
    image_url = Column(String)
    category_id = Column(Integer, ForeignKey('categories.id'))
    created_at = Column(DateTime, default=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    cart_items = relationship("CartItem", back_populates="product")

class Order(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String(20))  # pending, paid, shipped, etc.
    total_amount = Column(DECIMAL(10, 2))
    created_at = Column(DateTime, default=datetime.utcnow)

    address_id = Column(Integer, ForeignKey('addresses.id'))
    address = relationship("Address", back_populates="orders")
    payment_method = Column(String(50))  # e.g., 'Cash on Delivery', 'Card', etc.

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer)
    price_each = Column(DECIMAL(10, 2))

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class CartItem(Base):
    __tablename__ = 'cart_items'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    quantity = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")


class Address(Base):
    __tablename__ = 'addresses'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))

    full_name = Column(String(100))
    phone = Column(String(20))

    street = Column(String(200))        # Renamed from address_line1
    address_line2 = Column(String(200)) # Optional secondary line
    city = Column(String(100))
    zip_code = Column(String(20))       # Renamed from postal_code
    country = Column(String(100))

    user = relationship("User", back_populates="addresses")

    # Fix for backref from Order
    orders = relationship("Order", back_populates="address")




