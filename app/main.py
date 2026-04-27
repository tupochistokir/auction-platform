from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.lots import router as lots_router
from app.api.pricing import router as pricing_router
from app.api.auctions import router as auctions_router

from app.db.database import engine, Base, ensure_sqlite_schema
from app.db import models

Base.metadata.create_all(bind=engine)
ensure_sqlite_schema()

app = FastAPI(title="Auction Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
def read_root():
    return {"message": "Auction Platform работает 🚀"}


app.include_router(lots_router)
app.include_router(pricing_router)
app.include_router(auctions_router)
