"""User-facing recommendation layer for auction participation.

The pricing core estimates market value and auction attractiveness. This module
translates those numerical outputs into buyer-oriented decisions: whether the
lot looks undervalued, how risky the current price is, and which bidding
strategy is consistent with the user's personal value limit.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.pricing.math_core import calculate_recommended_bid


EXPECTED_PRICE_CLOSE_BAND = 0.05
"""A 5% band around E[P_final] marks the zone where one or two bid steps can
turn a fair price into overpayment. It is used only as a named risk interval,
not as an arbitrary hidden coefficient."""

MIN_MODEL_BID_STEP_RATE = 0.03
MAX_MODEL_BID_STEP_RATE = 0.08
DEFAULT_BID_STEP_RATE = (MIN_MODEL_BID_STEP_RATE + MAX_MODEL_BID_STEP_RATE) / 2


def _number(value: Any, default: float = 0.0) -> float:
    """Safely convert a model field to float."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if number == number else default


def _money(value: Optional[float]) -> Optional[float]:
    """Round monetary values while preserving None."""
    if value is None:
        return None
    return round(float(value), 2)


def _resolve_bid_step(pricing_data: Dict[str, Any], base_price: float) -> float:
    """Get bid step from model output or reconstruct it from the model interval.

    The pricing model defines bid step as 3-8% of base price. If the backend
    passes `recommended_bid_step`, it is used directly. Otherwise the midpoint
    of that documented interval is used as a conservative fallback.
    """
    explicit_step = _number(
        pricing_data.get("recommended_bid_step", pricing_data.get("bid_step")),
        0.0,
    )
    if explicit_step > 0:
        return explicit_step
    return max(1.0, base_price * DEFAULT_BID_STEP_RATE)


def evaluate_lot_for_user(
    pricing_data: Dict[str, Any],
    current_price: float,
    user_value: float,
) -> Dict[str, Any]:
    """Evaluate whether the current auction price is attractive for a user.

    The function compares the current price with three interpretable anchors:
    base market price P_base, expected final price E[P_final], and the user's
    personal maximum value. This gives a transparent decision label rather than
    a black-box recommendation.
    """
    base_price = _number(pricing_data.get("base_price"))
    expected_final_price = _number(pricing_data.get("expected_final_price"))
    current_price = _number(current_price)
    user_value = _number(user_value)

    profit_potential = expected_final_price - current_price
    value_gap = user_value - current_price
    is_overpriced = current_price > expected_final_price
    is_undervalued = current_price < base_price

    close_to_expected = False
    if expected_final_price > 0:
        close_to_expected = (
            0 <= expected_final_price - current_price
            <= expected_final_price * EXPECTED_PRICE_CLOSE_BAND
        )

    if is_overpriced:
        recommendation = "overpriced"
    elif is_undervalued and profit_potential > 0:
        recommendation = "good_deal"
    elif close_to_expected:
        recommendation = "risky"
    else:
        recommendation = "neutral"

    return {
        "profit_potential": _money(profit_potential),
        "value_gap": _money(value_gap),
        "is_overpriced": is_overpriced,
        "is_undervalued": is_undervalued,
        "recommendation": recommendation,
    }


def recommend_bid_strategy(
    pricing_data: Dict[str, Any],
    current_price: float,
    user_value: float,
) -> Dict[str, Any]:
    """Recommend a bidding strategy using utility maximization from math_core.

    The bid amount is selected by `calculate_recommended_bid`, while the
    strategy label is determined by auction attractiveness A: high A means
    stronger expected competition, medium A means balanced bidding, and low A
    means the user should be conservative.
    """
    base_price = _number(pricing_data.get("base_price"))
    expected_final_price = _number(pricing_data.get("expected_final_price"))
    attractiveness = _number(
        pricing_data.get(
            "auction_activity_live",
            pricing_data.get("auction_attractiveness"),
        )
    )
    bid_step = _resolve_bid_step(pricing_data, base_price)

    bid_result = calculate_recommended_bid(
        current_price=_number(current_price),
        user_value=_number(user_value),
        bid_step=bid_step,
    )
    recommended_bid = bid_result.get("recommended_bid")

    if attractiveness > 0.7:
        strategy = "aggressive"
    elif attractiveness > 0.4:
        strategy = "balanced"
    else:
        strategy = "conservative"

    expected_profit = (
        expected_final_price - float(recommended_bid)
        if recommended_bid is not None
        else None
    )

    return {
        "recommended_bid": recommended_bid,
        "max_safe_bid": _money(_number(user_value)),
        "expected_profit": _money(expected_profit),
        "win_probability": bid_result.get("win_probability", 0.0),
        "strategy": strategy,
    }


def generate_user_advice(
    pricing_data: Dict[str, Any],
    current_price: float,
    user_value: float,
) -> Dict[str, Any]:
    """Generate readable advice from pricing and bidding signals.

    The advice combines valuation state, personal value gap, and competition
    intensity. It is intended for the product page: the user sees not only a
    number, but also the reason why the system suggests a cautious, balanced,
    or aggressive action.
    """
    valuation = evaluate_lot_for_user(pricing_data, current_price, user_value)
    strategy = recommend_bid_strategy(pricing_data, current_price, user_value)
    attractiveness = _number(
        pricing_data.get(
            "auction_activity_live",
            pricing_data.get("auction_attractiveness"),
        )
    )
    confirmed_value = _number(pricing_data.get("confirmed_value_score"))

    advice_points = []

    if valuation["recommendation"] == "good_deal":
        summary = "Лот недооценён рынком, есть потенциал роста цены."
        risk_level = "low"
        advice_points.append("Текущая цена ниже базовой рыночной оценки.")
    elif valuation["recommendation"] == "overpriced":
        summary = "Текущая цена выше ожидаемой финальной, есть риск переплаты."
        risk_level = "high"
        advice_points.append("Не повышайте ставку выше личного лимита ценности.")
    elif valuation["recommendation"] == "risky":
        summary = "Цена близка к ожидаемой финальной, запас выгоды небольшой."
        risk_level = "medium"
        advice_points.append("Ставка оправдана только если вещь имеет личную ценность.")
    else:
        summary = "Лот находится в нейтральной зоне оценки."
        risk_level = "medium"
        advice_points.append("Ориентируйтесь на рекомендованную ставку и личный лимит.")

    if strategy["strategy"] == "aggressive":
        advice_points.append(
            "Аукцион с высокой конкуренцией, рекомендуется агрессивная стратегия."
        )
    elif strategy["strategy"] == "balanced":
        advice_points.append("Конкуренция умеренная, лучше повышать ставку постепенно.")
    else:
        advice_points.append("Спрос невысокий, рациональнее сохранять осторожную ставку.")

    if valuation["value_gap"] is not None and valuation["value_gap"] <= 0:
        risk_level = "high"
        advice_points.append("Текущая цена уже выше вашей личной оценки товара.")

    if confirmed_value >= 0.7 and attractiveness >= 0.4:
        advice_points.append("Качество признаков товара подтверждает интерес к лоту.")

    return {
        "summary": summary,
        "risk_level": risk_level,
        "advice_points": advice_points,
    }
