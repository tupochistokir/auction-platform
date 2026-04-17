from fastapi import APIRouter
from app.schemas.lot import LotCreate
from app.ai.analyzer import analyze_lot
from app.pricing.reserve_price import get_adjusted_base_price, calculate_reserve_price
from app.pricing.bid_step import calculate_bid_step
from app.pricing.attractiveness import calculate_attractiveness
from app.pricing.recommendation import calculate_recommended_bid
from app.pricing.forecast import (
    calculate_expected_final_price,
    calculate_expected_seller_profit,
    calculate_platform_fee
)

router = APIRouter(prefix="/lots", tags=["Lots"])

lots_db = [
    {
        "id": 1,
        "title": "Vintage leather jacket",
        "brand": "Levi's",
        "start_price": 4500,
        "current_price": 5200,
        "condition": "good",
        "description": "Vintage jacket in good condition"
    },
    {
        "id": 2,
        "title": "Brown wool coat",
        "brand": "No name",
        "start_price": 3000,
        "current_price": 3000,
        "condition": "excellent",
        "description": "Classic brown coat"
    }
]


@router.get("/")
def get_lots():
    return {"lots": lots_db}


@router.post("/")
def create_lot(lot: LotCreate):
    analysis = analyze_lot(lot.questionnaire.dict())
    base_price = get_adjusted_base_price(
        category=lot.questionnaire.category,
        brand=lot.questionnaire.brand,
        condition=lot.questionnaire.condition,
        estimated_age=lot.questionnaire.estimated_age,
        has_tag=lot.questionnaire.has_tag
    )
    attractiveness = calculate_attractiveness(
        value_score=analysis["value_score"],
        brand=lot.questionnaire.brand,
        estimated_age=lot.questionnaire.estimated_age,
        has_tag=lot.questionnaire.has_tag
    )
    
    recommended_start_price = calculate_reserve_price(
        base_price=base_price,
        attractiveness=attractiveness
    )
    recommended_bid_step = calculate_bid_step(
        base_price=base_price,
        value_score=analysis["value_score"]
    )

    recommended_bid_info = calculate_recommended_bid(
        current_price=recommended_start_price,
        base_price=base_price,
        value_score=analysis["value_score"],
        bid_step=recommended_bid_step
    )

    expected_final_price = calculate_expected_final_price(
        base_price=base_price,
        attractiveness=attractiveness,
        value_score=analysis["value_score"]
    )
    
    expected_seller_profit = calculate_expected_seller_profit(
        expected_final_price=expected_final_price,
        reserve_price=recommended_start_price
    )
    
    platform_fee = calculate_platform_fee(
        expected_final_price=expected_final_price
    )

    new_lot = {
        "id": len(lots_db) + 1,
        "title": lot.title,
        "start_price": lot.start_price,
        "current_price": lot.start_price,
        "description": lot.description,
        "questionnaire": lot.questionnaire.dict(),
        "analysis": analysis,
        "base_price": base_price,
        "recommended_start_price": recommended_start_price,
        "attractiveness": attractiveness,
        "recommended_bid_info": recommended_bid_info,
        "expected_final_price": expected_final_price,
        "expected_seller_profit": expected_seller_profit,
        "platform_fee": platform_fee,
        "recommended_bid_step": recommended_bid_step
    }
    lots_db.append(new_lot)
    return {
        "message": "Лот успешно создан",
        "lot": new_lot
    }