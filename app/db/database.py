from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./auction.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def ensure_sqlite_schema() -> None:
    """Add lightweight SQLite columns used by the current app version."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    columns_to_add = {
        "auctions": {
            "seller_name": "VARCHAR",
            "created_at": "DATETIME",
            "end_time": "DATETIME",
        },
        "bids": {
            "created_at": "DATETIME",
        },
        "offers": {
            "created_at": "DATETIME",
            "recommendation": "VARCHAR",
            "seller_wait_utility": "FLOAT",
            "risk_discount": "FLOAT",
            "counter_amount": "FLOAT",
            "decided_at": "DATETIME",
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
