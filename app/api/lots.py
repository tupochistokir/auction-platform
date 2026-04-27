from fastapi import APIRouter, HTTPException

from app.pricing.math_core import calculate_full_pricing
from app.schemas.lot import LotCreate

router = APIRouter(prefix="/lots", tags=["Lots"])

lots_db = [
    {
        "id": 1,
        "title": "Vintage leather jacket",
        "brand": "Levi's",
        "start_price": 4500,
        "current_price": 5200,
        "condition": "good",
        "description": "Vintage jacket in good condition",
    },
    {
        "id": 2,
        "title": "Brown wool coat",
        "brand": "No name",
        "start_price": 3000,
        "current_price": 3000,
        "condition": "excellent",
        "description": "Classic brown coat",
    },
]


@router.get("/")
def get_lots():
    return {"lots": lots_db}


@router.post("/")
def create_lot(lot: LotCreate):
    try:
        pricing = calculate_full_pricing(lot.questionnaire.dict())
        new_lot = {
            "id": len(lots_db) + 1,
            "title": lot.title,
            "brand": lot.questionnaire.brand,
            "start_price": pricing["recommended_start_price"],
            "current_price": pricing["recommended_start_price"],
            "description": lot.description,
            "questionnaire": lot.questionnaire.dict(),
            "analysis": pricing,
            "base_price": pricing["base_price"],
            "recommended_start_price": pricing["recommended_start_price"],
            "attractiveness": pricing["auction_attractiveness"],
            "recommended_bid_info": pricing["recommended_bid"],
            "expected_final_price": pricing["expected_final_price"],
            "recommended_bid_step": pricing["recommended_bid_step"],
        }
        lots_db.append(new_lot)
        return {
            "message": "Лот успешно рассчитан единой математической моделью",
            "lot": new_lot,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка создания лота: {exc}")
