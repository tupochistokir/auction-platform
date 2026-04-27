"""
Interpretable pricing core for the auction platform.

The module keeps the thesis model in one place: every API route that needs
pricing should call calculate_full_pricing() instead of duplicating formulas.
"""

from math import sqrt
from typing import Any, Dict, Optional


def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def _money(value: float) -> float:
    return round(max(0.0, value), 2)


def _score(value: float) -> float:
    return round(_clamp(value), 4)


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "да"}
    return bool(value)


def _item_type(questionnaire: Dict[str, Any]) -> str:
    subcategory = _text(questionnaire.get("subcategory")).lower()
    category = _text(questionnaire.get("category"), "other").lower()
    return subcategory or category or "other"


def normalize_score(value: float, min_value: float, max_value: float) -> float:
    """Normalize a numeric value to [0; 1] using min-max normalization."""
    if max_value == min_value:
        return 0.5
    return _score((value - min_value) / (max_value - min_value))


def calculate_brand_score(brand: Optional[str]) -> float:
    """Return brand reputation coefficient Q_b in the range [0; 1]."""
    normalized = _text(brand, "unknown").lower().replace("`", "'")
    normalized = " ".join(normalized.split())

    brand_scores = {
        "stone island": 0.95,
        "the north face": 0.88,
        "carhartt": 0.88,
        "alpha industries": 0.86,
        "levi's": 0.84,
        "levis": 0.84,
        "nike": 0.83,
        "adidas": 0.82,
        "ralph lauren": 0.8,
        "tommy hilfiger": 0.76,
        "calvin klein": 0.68,
        "no name": 0.2,
        "unknown": 0.2,
        "generic": 0.2,
        "": 0.2,
    }

    return brand_scores.get(normalized, 0.55)


def calculate_condition_score(condition: Optional[str]) -> float:
    """Convert product condition into quality coefficient Q_c."""
    condition_scores = {
        "excellent": 1.0,
        "good": 0.75,
        "normal": 0.55,
        "bad": 0.3,
        "unknown": 0.5,
        "": 0.5,
    }
    return condition_scores.get(_text(condition, "unknown").lower(), 0.5)


def calculate_vintage_score(age: int, brand_score: float) -> float:
    """
    Calculate vintage coefficient Q_v.

    Thesis logic: age creates value only when it is supported by brand strength.
    An old no-name item is treated as risk, not as automatic vintage premium.
    """
    if age < 10:
        return 0.5

    age_factor = normalize_score(age, 10, 35)

    if brand_score >= 0.8:
        return _score(0.58 + 0.37 * age_factor)
    if brand_score <= 0.35:
        return _score(0.5 - 0.22 * age_factor)

    return _score(0.48 + 0.18 * age_factor)


def calculate_rarity_score(
    brand_score: float,
    age: int,
    has_tag: bool,
    seller_comment: Optional[str],
) -> float:
    """Calculate rarity coefficient Q_r from scarcity and authenticity signals."""
    comment = _text(seller_comment).lower()
    rarity_keywords = (
        "rare",
        "limited",
        "archive",
        "vintage",
        "made in usa",
        "made in japan",
        "deadstock",
        "лимит",
        "архив",
        "винтаж",
        "редк",
    )

    keyword_matches = sum(1 for keyword in rarity_keywords if keyword in comment)
    keyword_score = min(1.0, keyword_matches / 3)
    age_factor = normalize_score(age, 0, 35)
    tag_score = 1.0 if has_tag else 0.35

    rarity = (
        0.38 * brand_score
        + 0.25 * age_factor
        + 0.17 * tag_score
        + 0.20 * keyword_score
    )

    if age >= 10 and brand_score <= 0.35 and keyword_score < 0.34:
        rarity -= 0.12

    return _score(rarity)


def calculate_confirmed_value_score(
    brand_score: float,
    condition_score: float,
    vintage_score: float,
    rarity_score: float,
) -> float:
    """Calculate confirmed value coefficient Q."""
    return _score(
        0.30 * brand_score
        + 0.25 * condition_score
        + 0.25 * rarity_score
        + 0.20 * vintage_score
    )


def calculate_auction_attractiveness(
    demand_score: float,
    uncertainty_score: float,
    interest_score: float,
    confirmed_value_score: float,
) -> float:
    """Calculate auction attractiveness coefficient A."""
    return _score(
        0.25 * demand_score
        + 0.20 * uncertainty_score
        + 0.25 * interest_score
        + 0.30 * confirmed_value_score
    )


def _calculate_demand_score(item_type: str, brand_score: float) -> float:
    category_demand = {
        "sneakers": 0.9,
        "boots": 0.72,
        "bomber": 0.86,
        "leather_jacket": 0.84,
        "denim_jacket": 0.75,
        "hoodie": 0.78,
        "jeans": 0.76,
        "bag": 0.74,
        "coat": 0.68,
        "tshirt": 0.62,
        "shirt": 0.58,
        "outerwear": 0.72,
        "tops": 0.64,
        "bottoms": 0.63,
        "shoes": 0.78,
        "accessories": 0.6,
        "other": 0.52,
    }
    return _score(0.55 * category_demand.get(item_type, 0.52) + 0.45 * brand_score)


def _calculate_uncertainty_score(vintage_score: float, rarity_score: float, has_defects: bool) -> float:
    defect_discount = 0.1 if has_defects else 0.0
    return _score(0.32 + 0.35 * rarity_score + 0.23 * abs(vintage_score - 0.5) - defect_discount)


def _calculate_interest_score(
    brand_score: float,
    condition_score: float,
    rarity_score: float,
    has_tag: bool,
) -> float:
    tag_bonus = 0.08 if has_tag else 0.0
    return _score(0.35 * brand_score + 0.27 * condition_score + 0.30 * rarity_score + tag_bonus)


def estimate_base_price(questionnaire: Dict[str, Any]) -> float:
    """
    Estimate base market price P_base.

    P_base is deterministic and combines category price, brand multiplier,
    condition multiplier, material multiplier and age/vintage correction.
    """
    item_type = _item_type(questionnaire)
    base_prices = {
        "bomber": 8500,
        "leather_jacket": 12500,
        "denim_jacket": 6200,
        "windbreaker": 5200,
        "puffer": 9800,
        "sheepskin": 14000,
        "coat": 9500,
        "trench": 8700,
        "hoodie": 4300,
        "tshirt": 2500,
        "shirt": 3500,
        "sweater": 4600,
        "longsleeve": 2900,
        "jeans": 5200,
        "pants": 4200,
        "shorts": 2600,
        "skirt": 3300,
        "sneakers": 7600,
        "boots": 8300,
        "loafers": 7000,
        "bag": 5800,
        "cap": 2100,
        "belt": 2300,
        "scarf": 2400,
        "outerwear": 7200,
        "tops": 3600,
        "bottoms": 4300,
        "shoes": 7300,
        "accessories": 3200,
        "other": 3000,
    }

    base_price = base_prices.get(item_type, base_prices["other"])
    brand_score = calculate_brand_score(questionnaire.get("brand"))
    condition_score = calculate_condition_score(questionnaire.get("condition"))
    age = int(_number(questionnaire.get("estimated_age", questionnaire.get("age")), 0))
    vintage_score = calculate_vintage_score(age, brand_score)

    brand_multiplier = 0.62 + 0.82 * brand_score
    condition_multiplier = 0.62 + 0.55 * condition_score

    material = _text(questionnaire.get("material")).lower()
    material_multipliers = {
        "leather": 1.28,
        "кожа": 1.28,
        "suede": 1.2,
        "замша": 1.2,
        "wool": 1.18,
        "шерсть": 1.18,
        "denim": 1.08,
        "деним": 1.08,
        "cotton": 1.0,
        "хлопок": 1.0,
        "nylon": 0.96,
        "нейлон": 0.96,
        "mixed": 0.94,
        "смесовый": 0.94,
        "polyester": 0.86,
        "полиэстер": 0.86,
        "synthetic": 0.78,
    }
    material_multiplier = material_multipliers.get(material, 1.0)

    if vintage_score > 0.5:
        age_multiplier = 1.0 + (vintage_score - 0.5) * 0.45
    else:
        age_multiplier = max(0.68, 1.0 - 0.018 * age)

    defects = _text(questionnaire.get("defects")).lower()
    has_defects = defects not in {"", "нет", "no", "none", "без дефектов"}
    defect_multiplier = 0.88 if has_defects else 1.0

    return _money(
        base_price
        * brand_multiplier
        * condition_multiplier
        * material_multiplier
        * age_multiplier
        * defect_multiplier
    )


def calculate_start_price(base_price: float, attractiveness: float) -> float:
    """Calculate recommended auction start price P_start."""
    alpha = 0.25
    start_price = base_price * (1 - alpha * attractiveness)
    return _money(max(start_price, base_price * 0.55))


def calculate_bid_step(base_price: float, attractiveness: float) -> float:
    """Calculate bid step in the 3-8 percent interval of P_base."""
    return _money(max(50.0, base_price * (0.03 + 0.05 * attractiveness)))


def calculate_expected_final_price(
    base_price: float,
    attractiveness: float,
    confirmed_value_score: float,
) -> float:
    """Forecast expected final price E[P_final]."""
    return _money(base_price * (1 + 0.35 * attractiveness + 0.25 * confirmed_value_score))


def calculate_recommended_bid(
    current_price: float,
    user_value: float,
    bid_step: float,
) -> Dict[str, Any]:
    """Choose a bid by maximizing U(s) = P_win(s) * (user_value - s)."""
    min_bid = current_price + bid_step
    if user_value < min_bid:
        return {
            "recommended_bid": None,
            "win_probability": 0.0,
            "utility": 0.0,
            "reason": "user_value_below_minimum_bid",
        }

    candidates = []
    candidate = min_bid
    while candidate <= user_value and len(candidates) < 12:
        candidates.append(candidate)
        candidate += bid_step

    if candidates[-1] < user_value:
        candidates.append(user_value)

    best_bid = candidates[0]
    best_probability = 0.0
    best_utility = -1.0
    denominator = max(user_value - min_bid, bid_step)

    for candidate_bid in candidates:
        relative_strength = _clamp((candidate_bid - min_bid) / denominator)
        win_probability = _clamp(0.34 + 0.62 * sqrt(relative_strength))
        utility = win_probability * max(0.0, user_value - candidate_bid)

        if utility > best_utility:
            best_bid = candidate_bid
            best_probability = win_probability
            best_utility = utility

    return {
        "recommended_bid": _money(best_bid),
        "win_probability": round(best_probability, 4),
        "utility": _money(best_utility),
        "reason": "utility_maximization",
    }


def calculate_full_pricing(
    questionnaire: Dict[str, Any],
    current_price: Optional[float] = None,
    user_value: Optional[float] = None,
) -> Dict[str, Any]:
    """Run the full pricing pipeline and return all thesis coefficients."""
    age = int(_number(questionnaire.get("estimated_age", questionnaire.get("age")), 0))
    brand_score = calculate_brand_score(questionnaire.get("brand"))
    condition_score = calculate_condition_score(questionnaire.get("condition"))
    vintage_score = calculate_vintage_score(age, brand_score)
    has_tag = _bool(questionnaire.get("has_tag"))
    rarity_score = calculate_rarity_score(
        brand_score=brand_score,
        age=age,
        has_tag=has_tag,
        seller_comment=questionnaire.get("seller_comment"),
    )
    confirmed_value_score = calculate_confirmed_value_score(
        brand_score=brand_score,
        condition_score=condition_score,
        vintage_score=vintage_score,
        rarity_score=rarity_score,
    )

    item_type = _item_type(questionnaire)
    defects = _text(questionnaire.get("defects")).lower()
    has_defects = defects not in {"", "нет", "no", "none", "без дефектов"}
    demand_score = _calculate_demand_score(item_type, brand_score)
    uncertainty_score = _calculate_uncertainty_score(vintage_score, rarity_score, has_defects)
    interest_score = _calculate_interest_score(brand_score, condition_score, rarity_score, has_tag)

    auction_attractiveness = calculate_auction_attractiveness(
        demand_score=demand_score,
        uncertainty_score=uncertainty_score,
        interest_score=interest_score,
        confirmed_value_score=confirmed_value_score,
    )

    base_price = estimate_base_price(questionnaire)
    recommended_start_price = calculate_start_price(base_price, auction_attractiveness)
    recommended_bid_step = calculate_bid_step(base_price, auction_attractiveness)
    expected_final_price = calculate_expected_final_price(
        base_price=base_price,
        attractiveness=auction_attractiveness,
        confirmed_value_score=confirmed_value_score,
    )

    recommended_bid: Dict[str, Any] = {}
    if current_price is not None and user_value is not None:
        recommended_bid = calculate_recommended_bid(
            current_price=float(current_price),
            user_value=float(user_value),
            bid_step=recommended_bid_step,
        )

    formula_explanation = {
        "brand_score": "Q_b = f(brand_prestige), Q_b in [0;1]",
        "condition_score": "Q_c = {excellent:1.0, good:0.75, normal:0.55, bad:0.3, unknown:0.5}",
        "vintage_score": "Q_v = f(age, Q_b): old strong-brand items receive premium; old no-name items receive discount",
        "rarity_score": "Q_r = 0.38Q_b + 0.25Age + 0.17Tag + 0.20Keywords - penalty",
        "confirmed_value_score": "Q = 0.30Q_b + 0.25Q_c + 0.25Q_r + 0.20Q_v",
        "auction_attractiveness": "A = 0.25D + 0.20V + 0.25I + 0.30Q",
        "base_price": "P_base = P_category * M_brand * M_condition * M_material * M_age * M_defects",
        "start_price": "P_start = max(P_base * (1 - 0.25A), 0.55P_base)",
        "bid_step": "Step = P_base * (0.03 + 0.05A)",
        "expected_final_price": "E[P_final] = P_base * (1 + 0.35A + 0.25Q)",
        "recommended_bid": "s* = argmax U(s), U(s) = P_win(s) * (V_user - s)",
    }

    return {
        "model_name": "Interpretable auction pricing model",
        "item_type": item_type,
        "age": age,
        "base_price": base_price,
        "brand_score": brand_score,
        "condition_score": condition_score,
        "vintage_score": vintage_score,
        "rarity_score": rarity_score,
        "confirmed_value_score": confirmed_value_score,
        "value_score": confirmed_value_score,
        "demand_score": demand_score,
        "uncertainty_score": uncertainty_score,
        "interest_score": interest_score,
        "auction_attractiveness": auction_attractiveness,
        "recommended_start_price": recommended_start_price,
        "recommended_bid_step": recommended_bid_step,
        "expected_final_price": expected_final_price,
        "recommended_bid": recommended_bid,
        "formula_explanation": formula_explanation,
    }
