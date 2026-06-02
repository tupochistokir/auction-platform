import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.lots import router as lots_router
from app.api.pricing import router as pricing_router
from app.api.auctions import router as auctions_router
from app.api.auth import router as auth_router
from app.config import get_frontend_origins, get_upload_dir

from app.db.database import engine, Base, ensure_sqlite_schema
from app.db import models

Base.metadata.create_all(bind=engine)
ensure_sqlite_schema()
upload_dir = get_upload_dir()
os.makedirs(upload_dir, exist_ok=True)

app = FastAPI(title="Auction Platform API")

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
    return {"message": "Auction Platform API is running"}


app.include_router(lots_router)
app.include_router(pricing_router)
app.include_router(auctions_router)
app.include_router(auth_router)
