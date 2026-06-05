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
RENDER_DATA_DIR = "/var/data"
RENDER_UPLOAD_DIR = f"{RENDER_DATA_DIR}/uploads"
LOCAL_UPLOAD_DIR = "uploads"


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
        if configured_dir.startswith(RENDER_DATA_DIR) and not os.path.ismount(RENDER_DATA_DIR):
            return LOCAL_UPLOAD_DIR
        return configured_dir

    if os.path.ismount(RENDER_DATA_DIR):
        return RENDER_UPLOAD_DIR

    return LOCAL_UPLOAD_DIR


def get_upload_diagnostics() -> dict:
    upload_dir = get_upload_dir()
    return {
        "configured_upload_dir": os.getenv("UPLOAD_DIR", "").strip() or None,
        "active_upload_dir": upload_dir,
        "render_data_dir_exists": os.path.isdir(RENDER_DATA_DIR),
        "render_data_dir_is_mount": os.path.ismount(RENDER_DATA_DIR),
        "persistent_uploads": upload_dir.startswith(RENDER_DATA_DIR)
        and os.path.ismount(RENDER_DATA_DIR),
        "warning": (
            "Uploads are not persistent until a Render Disk is mounted at /var/data."
            if os.getenv("RENDER")
            and not (
                upload_dir.startswith(RENDER_DATA_DIR)
                and os.path.ismount(RENDER_DATA_DIR)
            )
            else None
        ),
    }
