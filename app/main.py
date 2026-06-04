import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.lots import router as lots_router
from app.api.pricing import router as pricing_router
from app.api.auctions import router as auctions_router
from app.api.auth import router as auth_router
from app.config import get_frontend_origins, get_upload_dir

from app.db.database import engine, Base, ensure_sqlite_schema, get_database_diagnostics
from app.db import models

Base.metadata.create_all(bind=engine)
ensure_sqlite_schema()
upload_dir = get_upload_dir()
os.makedirs(upload_dir, exist_ok=True)

app = FastAPI(title="Auction Platform API")
APP_RELEASE = "2026-06-05-persistence-diagnostics"

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_frontend_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


@app.get("/")
def read_root():
    return {
        "message": "Auction Platform API is running",
        "release": APP_RELEASE,
    }


@app.get("/health")
def health_check():
    diagnostics = get_database_diagnostics()
    counts = {"users": None, "auctions": None}

    try:
        from app.db.database import SessionLocal

        db = SessionLocal()
        try:
            counts["users"] = db.query(models.User).count()
            counts["auctions"] = db.query(models.Auction).count()
        finally:
            db.close()
    except Exception as exc:
        counts["error"] = exc.__class__.__name__

    return {
        "status": "ok",
        "release": APP_RELEASE,
        "database": diagnostics,
        "counts": counts,
    }


app.include_router(lots_router)
app.include_router(pricing_router)
app.include_router(auctions_router)
app.include_router(auth_router)
