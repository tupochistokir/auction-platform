import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import String, create_engine, func, inspect, text
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import Base
from app.db.models import Auction, AuctionInteraction, Bid, MediaAsset, Offer, User


TABLE_MODELS = [User, Auction, Bid, Offer, AuctionInteraction, MediaAsset]


def normalize_postgres_url(url: str) -> str:
    normalized = (url or "").strip()
    if normalized.startswith("postgres://"):
        normalized = normalized.replace("postgres://", "postgresql://", 1)
    return normalized


def sqlite_url_from_path(path: str) -> str:
    if path.startswith("sqlite:"):
        return path
    return f"sqlite:///{Path(path).resolve().as_posix()}"


def serialize_row(row) -> dict:
    return {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
    }


def table_counts(session) -> dict:
    existing_tables = set(inspect(session.bind).get_table_names())
    return {
        model.__tablename__: session.query(model).count()
        for model in TABLE_MODELS
        if model.__tablename__ in existing_tables
    }


def destination_has_rows(session) -> bool:
    return any(count > 0 for count in table_counts(session).values())


def reset_postgres_sequences(session, engine) -> None:
    if engine.dialect.name != "postgresql":
        return

    for model in TABLE_MODELS:
        if "id" not in model.__table__.columns:
            continue
        if isinstance(model.__table__.columns["id"].type, String):
            continue
        max_id = session.query(func.max(model.id)).scalar() or 0
        if not max_id:
            continue

        sequence_name = session.execute(
            text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
            {"table_name": model.__tablename__},
        ).scalar()
        if not sequence_name:
            continue

        session.execute(
            text("SELECT setval(CAST(:sequence_name AS regclass), :max_id, true)"),
            {"sequence_name": sequence_name, "max_id": int(max_id)},
        )


def copy_rows(source_session, target_session) -> dict:
    copied = {}
    existing_tables = set(inspect(source_session.bind).get_table_names())
    for model in TABLE_MODELS:
        if model.__tablename__ not in existing_tables:
            copied[model.__tablename__] = 0
            continue
        rows = source_session.query(model).order_by(model.id.asc()).all()
        for row in rows:
            target_session.merge(model(**serialize_row(row)))
        copied[model.__tablename__] = len(rows)
    return copied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy Auction Platform data from a local SQLite file to PostgreSQL. "
            "The SQLite file is never deleted."
        )
    )
    parser.add_argument(
        "--sqlite-path",
        default=os.getenv("SQLITE_BACKUP_PATH", "auction.db"),
        help="Path to the SQLite database file or a sqlite:/// URL.",
    )
    parser.add_argument(
        "--postgres-url",
        default=os.getenv("POSTGRES_DATABASE_URL") or os.getenv("DATABASE_URL"),
        help="PostgreSQL DATABASE_URL. postgres:// URLs are accepted.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Drop and recreate PostgreSQL tables before copying.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Allow copying into a non-empty PostgreSQL database.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print SQLite row counts; do not connect to PostgreSQL.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sqlite_path = args.sqlite_path
    sqlite_file = Path(sqlite_path.replace("sqlite:///", "", 1))

    if not sqlite_path.startswith("sqlite:") and not sqlite_file.exists():
        raise SystemExit(f"SQLite source not found: {sqlite_file}")

    source_engine = create_engine(
        sqlite_url_from_path(sqlite_path),
        connect_args={"check_same_thread": False},
    )
    SourceSession = sessionmaker(bind=source_engine)

    with SourceSession() as source_session:
        source_counts = table_counts(source_session)
        print(f"SQLite source: {sqlite_path}")
        print(f"SQLite row counts: {source_counts}")

        if args.dry_run:
            print("Dry run complete. SQLite was not modified.")
            return

        postgres_url = normalize_postgres_url(args.postgres_url or "")
        if not postgres_url:
            raise SystemExit("Set --postgres-url or POSTGRES_DATABASE_URL.")
        if postgres_url.startswith("sqlite:"):
            raise SystemExit("Destination must be PostgreSQL, not SQLite.")

        target_engine = create_engine(postgres_url)
        TargetSession = sessionmaker(bind=target_engine)

        if args.replace:
            Base.metadata.drop_all(bind=target_engine)
        Base.metadata.create_all(bind=target_engine)

        with TargetSession() as target_session:
            if not args.replace and not args.append and destination_has_rows(target_session):
                raise SystemExit(
                    "PostgreSQL destination is not empty. "
                    "Use --append to merge or --replace to recreate its tables."
                )

            copied = copy_rows(source_session, target_session)
            reset_postgres_sequences(target_session, target_engine)
            target_session.commit()

        print(f"Copied rows: {copied}")
        print("Done. SQLite source was not deleted or changed.")


if __name__ == "__main__":
    main()
