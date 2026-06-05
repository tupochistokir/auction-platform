import os
import uuid

from fastapi import HTTPException, UploadFile

from app.config import get_public_base_url
from app.db.models import MediaAsset


ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))


def store_upload_file_as_media(db, file: UploadFile) -> str:
    content_type = (file.content_type or "").lower()
    extension = ALLOWED_IMAGE_TYPES.get(content_type)
    if not extension:
        raise HTTPException(status_code=400, detail="Можно загружать только JPG, PNG или WebP")

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Файл пустой")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Фото должно быть меньше 8 МБ")

    asset_id = str(uuid.uuid4())
    original_name = os.path.basename(file.filename or "")[:180]
    filename = original_name or f"{asset_id}{extension}"

    db.add(
        MediaAsset(
            id=asset_id,
            filename=filename,
            content_type=content_type,
            data=data,
        )
    )
    db.flush()
    return f"{get_public_base_url()}/media/{asset_id}"
