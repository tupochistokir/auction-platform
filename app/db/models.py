from datetime import datetime, timedelta

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Float, JSON, LargeBinary, UniqueConstraint
from app.db.database import Base


def default_auction_end_time():
    return datetime.utcnow() + timedelta(days=7)


class Auction(Base):
    __tablename__ = "auctions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    brand = Column(String)
    seller_id = Column(Integer, nullable=True)
    seller_name = Column(String, default="Кирилл")
    current_price = Column(Float)
    start_price = Column(Float)
    final_price = Column(Float, nullable=True)
    description = Column(String)
    status = Column(String)
    recommended_bid_step = Column(Float)
    questionnaire = Column(JSON)
    analysis = Column(JSON)
    views_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    favorites_count = Column(Integer, default=0)
    total_bids = Column(Integer, default=0)
    image_url = Column(String, nullable=True)
    image_urls = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, default=default_auction_end_time)

class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer)
    user_id = Column(Integer, nullable=True)
    user = Column(String)
    amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer)
    user_id = Column(Integer, nullable=True)
    user = Column(String)
    amount = Column(Float)
    status = Column(String, default="pending")  # pending / accepted / rejected
    recommendation = Column(String, nullable=True)
    seller_wait_utility = Column(Float, nullable=True)
    risk_discount = Column(Float, nullable=True)
    counter_amount = Column(Float, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuctionInteraction(Base):
    __tablename__ = "auction_interactions"
    __table_args__ = (
        UniqueConstraint("auction_id", "user_id", name="uq_auction_interaction_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer, index=True)
    user_id = Column(Integer, index=True)
    viewed = Column(Boolean, default=False)
    liked = Column(Boolean, default=False)
    favorited = Column(Boolean, default=False)
    viewed_at = Column(DateTime, nullable=True)
    liked_at = Column(DateTime, nullable=True)
    favorited_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    display_name = Column(String)
    avatar_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    city = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    is_incognito = Column(Boolean, default=False)
    password_recovery_question = Column(String, nullable=True)
    password_recovery_answer_hash = Column(String, nullable=True)
    password_recovery_answer_salt = Column(String, nullable=True)
    password_hash = Column(String)
    password_salt = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=True)
    content_type = Column(String)
    data = Column(LargeBinary)
    created_at = Column(DateTime, default=datetime.utcnow)
