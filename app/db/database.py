import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auction.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def ensure_sqlite_schema() -> None:
    """Add lightweight SQLite columns used by the current app version."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    columns_to_add = {
        "auctions": {
            "seller_id": "INTEGER",
            "seller_name": "VARCHAR",
            "created_at": "DATETIME",
            "end_time": "DATETIME",
            "final_price": "FLOAT",
            "views_count": "INTEGER DEFAULT 0",
            "likes_count": "INTEGER DEFAULT 0",
            "favorites_count": "INTEGER DEFAULT 0",
            "total_bids": "INTEGER DEFAULT 0",
        },
        "bids": {
            "user_id": "INTEGER",
            "created_at": "DATETIME",
        },
        "offers": {
            "user_id": "INTEGER",
            "created_at": "DATETIME",
            "recommendation": "VARCHAR",
            "seller_wait_utility": "FLOAT",
            "risk_discount": "FLOAT",
            "counter_amount": "FLOAT",
            "decided_at": "DATETIME",
        },
        "users": {
            "avatar_url": "VARCHAR",
            "phone": "VARCHAR",
            "age": "INTEGER",
            "city": "VARCHAR",
            "bio": "VARCHAR",
            "is_incognito": "BOOLEAN DEFAULT 0",
        },
        "auction_interactions": {
            "viewed_at": "DATETIME",
            "liked_at": "DATETIME",
            "favorited_at": "DATETIME",
            "updated_at": "DATETIME",
        },
    }

    with engine.begin() as connection:
        for table_name, columns in columns_to_add.items():
            if table_name not in table_names:
                continue

            existing_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }

            for column_name, column_type in columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                    )
