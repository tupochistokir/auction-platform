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
        seller_requested_start_price = round(float(lot.start_price or 0), 2)
        seller_price_delta = round(
            seller_requested_start_price - pricing["recommended_start_price"],
            2,
        )

        return {
            "title": lot.title,
            "analysis": pricing,
            "pricing_labels": {
                "base_price": "P_base — рыночная resale-оценка",
                "recommended_start_price": "P_start — рекомендуемая стартовая цена торгов",
                "auction_potential_pre": "A_pre — потенциал аукциона до старта",
                "auction_activity_live": "A_live — текущая активность торгов",
                "demand_score": "D — фактические торговые действия",
                "interest_score": "I — интерес без обязательной ставки",
            },
            "pricing_pipeline_explanation": {
                "base_price": "P_base берётся из обученной ML-модели по признакам товара; если модель недоступна, используется резервная формула.",
                "market_signals": "D, I и V считаются из реальной активности лота: просмотров, лайков, избранного, ставок и разброса цен.",
                "confirmed_value": "Q объединяет подтверждаемую ценность вещи: бренд, состояние, редкость и винтажность.",
                "start_price": "Стартовая цена включает базовый аукционный дисконт 5% и дополнительную поправку на привлекательность A.",
                "final_price": "Прогноз финала строится ML-моделью по цене, старту и рыночной активности; fallback остаётся интерпретируемой формулой.",
            },
            "seller_questionnaire": pricing.get("seller_questionnaire", {}),
            "pricing_questionnaire": pricing.get("pricing_questionnaire", {}),
            "evidence_report": pricing.get("evidence_report", {}),
            "seller_requested_start_price": seller_requested_start_price,
            "seller_price_delta": seller_price_delta,
            "base_price": pricing.get("base_price", 0),
            "base_price_before_calibration": pricing.get("base_price_before_calibration", 0),
            "base_price_source": pricing.get("base_price_source", "fallback_formula"),
            "model_available": pricing.get("model_available", False),
            "resale_calibration": pricing.get("resale_calibration", {}),
            "brand_score": pricing.get("brand_score", 0),
            "brand_confidence": pricing.get("brand_confidence", 0),
            "brand_source": pricing.get("brand_source", "not_provided"),
            "brand_normalized": pricing.get("brand_normalized", "unknown"),
            "missing_features": pricing.get("missing_features", []),
            "condition_score": pricing.get("condition_score", 0),
            "vintage_score": pricing.get("vintage_score", 0),
            "rarity_score": pricing.get("rarity_score", 0),
            "demand_score": pricing.get("demand_score", 0),
            "interest_score": pricing.get("interest_score", 0),
            "uncertainty_score": pricing.get("uncertainty_score", 0),
            "auction_potential_pre": pricing.get("auction_potential_pre", 0),
            "auction_activity_live": pricing.get("auction_activity_live", 0),
            "price_pressure_score": pricing.get("price_pressure_score", 0),
            "confirmed_value_score": pricing.get("confirmed_value_score", 0),
            "auction_attractiveness": pricing.get("auction_attractiveness", 0),
            "auction_attractiveness_deprecated": pricing.get(
                "auction_attractiveness_deprecated",
                False,
            ),
            "market_signals": pricing.get("market_signals", {}),
            "data_provenance": pricing.get("data_provenance", {}),
            "calculation_trace": pricing.get("calculation_trace", {}),
            "base_price_model_metadata": pricing.get("base_price_model_metadata", {}),
            "recommended_start_price": pricing.get("recommended_start_price", 0),
            "model_recommended_start_price": pricing.get("model_recommended_start_price", 0),
            "initial_bid_step": pricing.get("initial_bid_step", 0),
            "live_recommended_bid_step": pricing.get("live_recommended_bid_step", 0),
            "recommended_bid_step": pricing.get("recommended_bid_step", 0),
            "recommended_bid_info": pricing.get("recommended_bid", {}),
            "conservative_final_price": pricing.get("conservative_final_price", 0),
            "expected_final_price": pricing.get("expected_final_price", 0),
            "optimistic_final_price": pricing.get("optimistic_final_price", 0),
            "final_price_source": pricing.get("final_price_source", "fallback_formula"),
            "final_price_model_available": pricing.get("final_price_model_available", False),
            "auction_behavior": pricing.get("auction_behavior", {}),
            "auction_behavior_source": pricing.get(
                "auction_behavior_source",
                "Online Auctions Dataset",
            ),
            "bids_bucket": pricing.get("bids_bucket"),
            "median_final_start_ratio": pricing.get("median_final_start_ratio"),
            "fashion_transfer_factor": pricing.get("fashion_transfer_factor"),
            "auction_uplift": pricing.get("auction_uplift"),
            "pricing_confidence": pricing.get("pricing_confidence"),
            "live_activity_detected": pricing.get("live_activity_detected"),
            "attractiveness": pricing.get("auction_attractiveness", 0),
            "expected_seller_profit": expected_seller_profit,
            "auction_gain": auction_gain,
            "cost_price": cost_price,
            "platform_fee": platform_fee,
            "formula_explanation": pricing.get("formula_explanation", {}),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка расчета математической модели: {exc}",
        )
