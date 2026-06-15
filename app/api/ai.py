from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ai.photo_analyzer import analyze_lot_photo_evidence
from app.db.database import SessionLocal
from app.db.models import MediaAsset


router = APIRouter(prefix="/ai", tags=["AI"])


class LotPhotoAnalysisRequest(BaseModel):
    title: str = ""
    description: str = ""
    image_urls: List[str] = Field(default_factory=list)
    questionnaire: Dict[str, Any] = Field(default_factory=dict)


def _asset_id_from_url(url: str) -> str:
    path = urlparse(url or "").path.strip("/")
    if not path:
        return ""
    return path.split("/")[-1]


@router.post("/analyze-lot-photo")
def analyze_lot_photo(request: LotPhotoAnalysisRequest):
    if not request.image_urls:
        raise HTTPException(status_code=400, detail="Загрузите хотя бы одно фото товара")

    db = SessionLocal()
    try:
        images: List[Dict[str, Any]] = []
        seen_asset_ids = set()

        for image_url in request.image_urls[:3]:
            asset_id = _asset_id_from_url(image_url)
            if not asset_id or asset_id in seen_asset_ids:
                continue
            seen_asset_ids.add(asset_id)

            asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id).first()
            if not asset:
                continue

            images.append(
                {
                    "filename": asset.filename,
                    "content_type": asset.content_type,
                    "data": bytes(asset.data or b""),
                }
            )

        if not images:
            raise HTTPException(status_code=404, detail="Загруженные фото не найдены в хранилище")

        return analyze_lot_photo_evidence(
            images=images,
            questionnaire=request.questionnaire,
            title=request.title,
            description=request.description,
        )
    finally:
        db.close()
