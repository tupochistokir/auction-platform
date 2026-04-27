from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Integer, String, Float, JSON
from app.db.database import Base


def default_auction_end_time():
    return datetime.utcnow() + timedelta(days=7)


class Auction(Base):
    __tablename__ = "auctions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    brand = Column(String)
    seller_name = Column(String, default="Кирилл")
    current_price = Column(Float)
    start_price = Column(Float)
    description = Column(String)
    status = Column(String)
    recommended_bid_step = Column(Float)
    questionnaire = Column(JSON)
    analysis = Column(JSON)
    image_url = Column(String, nullable=True)
    image_urls = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, default=default_auction_end_time)

class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer)
    user = Column(String)
    amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer)
    user = Column(String)
    amount = Column(Float)
    status = Column(String, default="pending")  # pending / accepted / rejected
    recommendation = Column(String, nullable=True)
    seller_wait_utility = Column(Float, nullable=True)
    risk_discount = Column(Float, nullable=True)
    counter_amount = Column(Float, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    display_name = Column(String)
    password_hash = Column(String)
    password_salt = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
