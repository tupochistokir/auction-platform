from sqlalchemy import Column, Integer, String, Float, Boolean, JSON
from app.db.database import Base


class Auction(Base):
    __tablename__ = "auctions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    brand = Column(String)
    current_price = Column(Float)
    start_price = Column(Float)
    description = Column(String)
    status = Column(String)
    recommended_bid_step = Column(Float)
    questionnaire = Column(JSON)
    analysis = Column(JSON)
    image_url = Column(String, nullable=True)
    image_urls = Column(JSON, nullable=True)

class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer)
    user = Column(String)
    amount = Column(Float)

class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)
    auction_id = Column(Integer)
    user = Column(String)
    amount = Column(Float)
    status = Column(String, default="pending")  # pending / accepted / rejected