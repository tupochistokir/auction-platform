from fastapi import APIRouter, HTTPException

from app.pricing.math_core import calculate_full_pricing
from app.schemas.lot import LotCreate

router = APIRouter(prefix="/pricing", tags=["Pricing"])


@router.post("/estimate")
def estimate_price(lot: LotCreate):
    """Return the same pricing model that is used to publish auctions."""
    try:
        questionnaire = lot.questionnaire.dict()
        pricing = calculate_full_pricing(questionnaire)

        cost_price = round(pricing["base_price"] * 0.6, 2)
        expected_seller_profit = round(pricing["expected_final_price"] - cost_price, 2)
        platform_fee = round(pricing["expected_final_price"] * 0.05, 2)
        auction_gain = round(
            pricing["expected_final_price"] - pricing["recommended_start_price"],
            2,
        )

        return {
            "title": lot.title,
            "analysis": pricing,
            "base_price": pricing["base_price"],
            "recommended_start_price": pricing["recommended_start_price"],
            "recommended_bid_step": pricing["recommended_bid_step"],
            "recommended_bid_info": pricing["recommended_bid"],
            "expected_final_price": pricing["expected_final_price"],
            "confirmed_value_score": pricing["confirmed_value_score"],
            "attractiveness": pricing["auction_attractiveness"],
            "auction_attractiveness": pricing["auction_attractiveness"],
            "expected_seller_profit": expected_seller_profit,
            "auction_gain": auction_gain,
            "cost_price": cost_price,
            "platform_fee": platform_fee,
            "formula_explanation": pricing["formula_explanation"],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка расчета математической модели: {exc}",
        )
