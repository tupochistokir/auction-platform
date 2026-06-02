import os
from typing import List

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


DEFAULT_FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def get_frontend_origins() -> List[str]:
    raw_origins = os.getenv("FRONTEND_ORIGINS", "")
    env_origins = [
        origin.strip().rstrip("/")
        for origin in raw_origins.split(",")
        if origin.strip()
    ]
    return DEFAULT_FRONTEND_ORIGINS + env_origins


def get_public_base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def get_upload_dir() -> str:
    configured_dir = os.getenv("UPLOAD_DIR", "").strip()
    if configured_dir:
        return configured_dir

    if os.getenv("RENDER") and os.path.isdir("/var/data"):
        return "/var/data/uploads"

    return "uploads"
