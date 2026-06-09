import os

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.lots import router as lots_router
from app.api.pricing import router as pricing_router
from app.api.auctions import router as auctions_router
from app.api.auth import router as auth_router
from app.config import get_frontend_origins, get_upload_diagnostics, get_upload_dir

from app.db.database import SessionLocal, engine, Base, ensure_sqlite_schema, get_database_diagnostics
from app.db import models

try:
    from ml.inference import get_model_diagnostics
except Exception as exc:
    def get_model_diagnostics():
        return {"error": f"{exc.__class__.__name__}: {exc}"}

Base.metadata.create_all(bind=engine)
ensure_sqlite_schema()
upload_dir = get_upload_dir()
os.makedirs(upload_dir, exist_ok=True)

app = FastAPI(title="Auction Platform API")
APP_RELEASE = "2026-06-09-kiki-demo-rescue"

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_frontend_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


def _media_storage_diagnostics(database_diagnostics: dict) -> dict:
    diagnostics = get_upload_diagnostics()
    persistent_media_storage = bool(database_diagnostics.get("persistent_storage"))
    diagnostics.update(
        {
            "storage_backend": "database",
            "persistent_media_storage": persistent_media_storage,
            "persistent_uploads": persistent_media_storage,
            "warning": (
                None
                if persistent_media_storage
                else "Image uploads need persistent database storage."
            ),
        }
    )
    return diagnostics


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
        "uploads": _media_storage_diagnostics(diagnostics),
        "models": get_model_diagnostics(),
        "counts": counts,
    }


@app.get("/media/{asset_id}")
def get_media(asset_id: str):
    db = SessionLocal()
    try:
        asset = db.query(models.MediaAsset).filter(models.MediaAsset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Фото не найдено")

        return Response(
            content=bytes(asset.data or b""),
            media_type=asset.content_type or "application/octet-stream",
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )
    finally:
        db.close()


app.include_router(lots_router)
app.include_router(pricing_router)
app.include_router(auctions_router)
app.include_router(auth_router)
