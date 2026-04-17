from fastapi import APIRouter
from app.pricing.attractiveness import calculate_attractiveness
from app.pricing.recommendation import calculate_recommended_bid
from app.pricing.bid_step import calculate_bid_step
from app.schemas.lot import LotCreate
from app.ai.analyzer import analyze_lot
from app.ml.price_model import estimate_base_price_ml
from app.pricing.reserve_price import get_adjusted_base_price, calculate_reserve_price
from app.pricing.forecast import (
    calculate_expected_final_price,
    calculate_expected_seller_profit,
    calculate_platform_fee,
    calculate_auction_gain
)

router = APIRouter(prefix="/pricing", tags=["Pricing"])


@router.post("/estimate")
def estimate_price(lot: LotCreate):
    analysis = analyze_lot(lot.questionnaire.dict())

        # 1. ML оценка (основа)
    ml_price = estimate_base_price_ml(lot.questionnaire.dict())
    
    # 2. корректировка правилами
    base_price = get_adjusted_base_price(
        category=lot.questionnaire.category,
        brand=lot.questionnaire.brand,
        condition=lot.questionnaire.condition,
        estimated_age=lot.questionnaire.estimated_age,
        has_tag=lot.questionnaire.has_tag
    )
    
    # 3. комбинируем (очень важно)
    base_price = 0.7 * ml_price + 0.3 * base_price
    base_price = round(base_price, 2)

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
    
    auction_gain = calculate_auction_gain(
        expected_final_price=expected_final_price,
        reserve_price=recommended_start_price
    )
    
    cost_price = base_price * 0.6  # предположим закупка за 60%
    
    expected_seller_profit = calculate_expected_seller_profit(
        expected_final_price=expected_final_price,
        cost_price=cost_price
    )
    
    platform_fee = calculate_platform_fee(
        expected_final_price=expected_final_price
    )

    return {
        "title": lot.title,
        "analysis": analysis,
        "attractiveness": attractiveness,
        "base_price": base_price,
        "recommended_start_price": recommended_start_price,
        "recommended_bid_step": recommended_bid_step,
        "recommended_bid_info": recommended_bid_info,
        "expected_final_price": expected_final_price,
        "expected_seller_profit": expected_seller_profit,
        "auction_gain": auction_gain,
        "cost_price": cost_price,
        "platform_fee": platform_fee
    }