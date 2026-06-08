"""
Interpretable pricing core for the auction platform.

The module keeps the thesis model in one place: every API route that needs
pricing should call calculate_full_pricing() instead of duplicating formulas.
"""

from math import sqrt
from typing import Any, Dict, Optional

try:
    from ml.inference import predict_base_price, predict_final_price
except Exception:
    predict_base_price = None
    predict_final_price = None

try:
    from app.pricing.demand_model import calculate_market_signals
except Exception:
    calculate_market_signals = None

try:
    from app.pricing.evidence_fusion import fuse_questionnaire_evidence
except Exception:
    fuse_questionnaire_evidence = None

try:
    from app.pricing.resale_calibration import apply_resale_calibration
except Exception:
    apply_resale_calibration = None

try:
    from app.pricing.auction_behavior import calculate_buyer_behavior_adjustment
except Exception:
    calculate_buyer_behavior_adjustment = None


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


def _normalize_brand(brand: Optional[str]) -> str:
    normalized = _text(brand).lower().replace("`", "'").replace("_", " ")
    return " ".join(normalized.split())


def normalize_score(value: float, min_value: float, max_value: float) -> float:
    """Normalize a numeric value to [0; 1] using min-max normalization."""
    if max_value == min_value:
        return 0.5
    return _score((value - min_value) / (max_value - min_value))


def calculate_brand_score(brand: Optional[str]) -> float:
    """Return brand reputation coefficient Q_b in the range [0; 1].

    Missing brand and explicit no-name are different cases. If the seller does
    not provide a brand, the platform has no positive evidence of brand value,
    so Q_b equals 0. A declared no-name item receives a very small non-zero
    score because the brand status is known, but it does not create premium.
    """
    normalized = _normalize_brand(brand)

    brand_scores = {
        "": 0.0,
        "unknown": 0.0,
        "not specified": 0.0,
        "не указан": 0.0,
        "no name": 0.05,
        "no-name": 0.05,
        "noname": 0.05,
        "generic": 0.08,
        "stone island": 0.95,
        "gucci": 0.94,
        "prada": 0.93,
        "burberry": 0.9,
        "the north face": 0.88,
        "carhartt": 0.88,
        "alpha industries": 0.86,
        "levi's": 0.84,
        "levis": 0.84,
        "nike": 0.83,
        "adidas": 0.82,
        "ralph lauren": 0.8,
        "tommy hilfiger": 0.76,
        "diesel": 0.74,
        "lacoste": 0.7,
        "armani": 0.7,
        "calvin klein": 0.68,
        "uniqlo": 0.42,
        "zara": 0.36,
        "h&m": 0.3,
    }

    return brand_scores.get(normalized, 0.35)


def calculate_brand_confidence(brand: Optional[str]) -> float:
    """Estimate confidence of the brand signal source."""
    normalized = _normalize_brand(brand)
    if normalized in {"", "unknown", "not specified", "не указан"}:
        return 0.0
    if normalized in {"no name", "no-name", "noname", "generic"}:
        return 0.8
    known_brands = {
        "stone island",
        "gucci",
        "prada",
        "burberry",
        "the north face",
        "carhartt",
        "alpha industries",
        "levi's",
        "levis",
        "nike",
        "adidas",
        "ralph lauren",
        "tommy hilfiger",
        "diesel",
        "lacoste",
        "armani",
        "calvin klein",
        "uniqlo",
        "zara",
        "h&m",
    }
    return 0.95 if normalized in known_brands else 0.45


def calculate_condition_score(condition: Optional[str]) -> float:
    """Convert product condition into quality coefficient Q_c."""
    condition_scores = {
        "new": 1.0,
        "excellent": 1.0,
        "новое": 1.0,
        "good": 0.75,
        "хорошее": 0.75,
        "normal": 0.55,
        "нормальное": 0.55,
        "bad": 0.3,
        "defective": 0.3,
        "с дефектами": 0.3,
        "unknown": 0.55,
        "": 0.55,
    }
    return condition_scores.get(_text(condition, "normal").lower(), 0.55)


def calculate_vintage_score(age: int, brand_score: float) -> float:
    """
    Calculate vintage coefficient Q_v.

    Market convention treats fashion vintage as roughly 20-99 years old, while
    younger past-season designer items are better described as archival or
    pre-vintage. The coefficient is therefore smooth: a 9-year-old item does
    not become "vintage", but it can receive a small archival signal if brand
    evidence supports it. Old no-name items are still capped because age alone
    is not a resale-value proof.
    """
    age = max(0, int(age or 0))
    brand_score = _clamp(brand_score)

    if age == 0:
        return 0.0

    if age < 5:
        age_signal = 0.02 * (age / 5)
    elif age < 20:
        age_signal = 0.02 + 0.28 * ((age - 5) / 15)
    elif age < 100:
        age_signal = 0.30 + 0.60 * ((age - 20) / 80) ** 0.65
    else:
        age_signal = 0.95

    brand_support = 0.25 + 0.75 * brand_score

    if brand_score <= 0.35:
        brand_support *= 0.45 if age < 20 else 0.65
    elif brand_score < 0.65:
        brand_support *= 0.75

    return _score(age_signal * brand_support)


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
    tag_score = 1.0 if has_tag else 0.0

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
    """Calculate legacy live auction attractiveness coefficient A.

    The public name is kept for old API consumers. In the current model this is
    equivalent to A_live without additional live-price pressure.
    """
    return _score(
        0.25 * demand_score
        + 0.20 * uncertainty_score
        + 0.25 * interest_score
        + 0.30 * confirmed_value_score
    )


def calculate_category_auction_suitability(item_type: str) -> float:
    """Estimate whether a category usually fits an auction format."""
    suitability = {
        "sneakers": 0.90,
        "boots": 0.72,
        "bomber": 0.84,
        "leather_jacket": 0.86,
        "denim_jacket": 0.75,
        "windbreaker": 0.65,
        "puffer": 0.72,
        "sheepskin": 0.78,
        "coat": 0.68,
        "trench": 0.76,
        "hoodie": 0.70,
        "sweater": 0.66,
        "longsleeve": 0.54,
        "tshirt": 0.50,
        "shirt": 0.56,
        "top": 0.44,
        "blouse": 0.52,
        "jeans": 0.68,
        "pants": 0.56,
        "shorts": 0.42,
        "skirt": 0.48,
        "dress": 0.58,
        "suit": 0.70,
        "jumpsuit": 0.54,
        "bag": 0.78,
        "cap": 0.46,
        "belt": 0.46,
        "scarf": 0.42,
        "jewelry": 0.64,
        "outerwear": 0.74,
        "tops": 0.54,
        "bottoms": 0.58,
        "shoes": 0.78,
        "accessories": 0.58,
        "dresses": 0.58,
        "other": 0.50,
    }
    return _score(suitability.get(item_type, suitability["other"]))


def calculate_auction_potential_pre(
    confirmed_value_score: float,
    rarity_score: float,
    vintage_score: float,
    brand_score: float,
    category_suitability: float,
) -> float:
    """Calculate A_pre before publication using stable lot properties only."""
    return _score(
        0.40 * confirmed_value_score
        + 0.22 * rarity_score
        + 0.14 * vintage_score
        + 0.14 * brand_score
        + 0.10 * category_suitability
    )


def calculate_auction_activity_live(
    demand_score: float,
    interest_score: float,
    uncertainty_score: float,
    confirmed_value_score: float,
    price_pressure_score: float = 0.0,
    auction_potential_pre: float = 0.0,
    no_live_activity: bool = False,
) -> float:
    """Calculate A_live after publication from real activity signals."""
    if no_live_activity:
        return _score(min(auction_potential_pre, 0.35) * 0.50)

    return _score(
        0.38 * demand_score
        + 0.22 * interest_score
        + 0.15 * uncertainty_score
        + 0.20 * confirmed_value_score
        + 0.05 * price_pressure_score
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


def _manual_estimate_base_price(questionnaire: Dict[str, Any]) -> float:
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
        "top": 1900,
        "blouse": 3300,
        "jeans": 5200,
        "pants": 4200,
        "shorts": 2600,
        "skirt": 3300,
        "dress": 4300,
        "suit": 6200,
        "jumpsuit": 4700,
        "sneakers": 7600,
        "boots": 8300,
        "loafers": 7000,
        "heels": 5200,
        "bag": 5800,
        "cap": 2100,
        "belt": 2300,
        "scarf": 2400,
        "jewelry": 2600,
        "outerwear": 7200,
        "tops": 3600,
        "bottoms": 4300,
        "shoes": 7300,
        "accessories": 3200,
        "dresses": 4800,
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


def _estimate_base_price_with_metadata(questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    def calibrated_result(raw_price: float, source: str, model_available: bool, metadata: Dict[str, Any]) -> Dict[str, Any]:
        calibration = {}
        base_price = _money(raw_price)
        if apply_resale_calibration is not None:
            try:
                calibration = apply_resale_calibration(questionnaire, raw_price)
                base_price = _money(float(calibration["base_price_after_calibration"]))
            except Exception:
                calibration = {}

        return {
            "base_price": base_price,
            "base_price_before_calibration": _money(raw_price),
            "source": source,
            "model_available": model_available,
            "model_metadata": metadata,
            "resale_calibration": calibration,
        }

    if predict_base_price is not None:
        try:
            ml_result = predict_base_price(questionnaire)
            if ml_result and ml_result.get("base_price") is not None:
                return calibrated_result(
                    raw_price=float(ml_result["base_price"]),
                    source=ml_result.get("source", "ml_model"),
                    model_available=bool(ml_result.get("model_available", False)),
                    metadata=ml_result.get("model_metadata", {}),
                )
        except Exception:
            pass

    return calibrated_result(
        raw_price=_manual_estimate_base_price(questionnaire),
        source="fallback_formula",
        model_available=False,
        metadata={},
    )


def _estimate_final_price_with_metadata(features: Dict[str, Any]) -> Dict[str, Any]:
    if predict_final_price is not None:
        try:
            ml_result = predict_final_price(features)
            if ml_result and ml_result.get("expected_final_price") is not None:
                return {
                    "expected_final_price": _money(float(ml_result["expected_final_price"])),
                    "source": ml_result.get("source", "ml_model"),
                    "model_available": bool(ml_result.get("model_available", False)),
                    "domain_reason": ml_result.get("domain_reason"),
                }
        except Exception:
            pass

    return {
        "expected_final_price": calculate_expected_final_price(
            base_price=float(features.get("base_price", features.get("price", 0)) or 0),
            attractiveness=float(features.get("auction_attractiveness", 0) or 0),
            confirmed_value_score=float(features.get("confirmed_value_score", 0) or 0),
        ),
        "source": "fallback_formula",
        "model_available": False,
    }


def estimate_base_price(questionnaire: Dict[str, Any]) -> float:
    """
    Estimate base market price P_base with ML first and deterministic fallback.

    The public function keeps the old float-returning contract, while the full
    pipeline exposes source metadata through calculate_full_pricing().
    """
    return _estimate_base_price_with_metadata(questionnaire)["base_price"]


def calculate_start_price(base_price: float, attractiveness: float) -> float:
    """Calculate recommended auction start price P_start.

    The auction format needs a small entry discount even when the current
    attractiveness score is low. Delta motivates the first bid; alpha controls
    the additional discount caused by auction attractiveness.
    """
    delta = 0.05
    alpha = 0.25
    start_price = base_price * (1 - delta - alpha * attractiveness)
    return _money(max(start_price, base_price * 0.55))


def calculate_bid_step(start_price: float, attractiveness: float) -> float:
    """Calculate bid step as 3-8 percent of the auction start price.

    The formula is intentionally tied to P_start, not P_base: bidders react to
    the visible auction entry price. A_pre is used for the initial step before
    publication, while A_live can be used later as an advisory dynamic step.
    """
    raw_step = start_price * (0.03 + 0.05 * _clamp(attractiveness))
    min_step = start_price * 0.02
    max_step = start_price * 0.08
    bounded = max(min_step, min(max_step, raw_step))
    if bounded <= 100:
        rounded = round(bounded / 50) * 50
    elif bounded <= 500:
        rounded = round(bounded / 100) * 100
    elif bounded <= 1500:
        rounded = round(bounded / 250) * 250
    else:
        rounded = round(bounded / 500) * 500
    return _money(max(50.0, rounded))


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
    if fuse_questionnaire_evidence is not None:
        fused = fuse_questionnaire_evidence(questionnaire)
        pricing_questionnaire = fused["pricing_questionnaire"]
        evidence_report = fused["evidence_report"]
    else:
        pricing_questionnaire = dict(questionnaire or {})
        evidence_report = {
            "seller_input": dict(questionnaire or {}),
            "ai_analysis": {},
            "decisions": {},
            "conflicts": [],
            "ai_used": False,
        }

    age = int(_number(pricing_questionnaire.get("estimated_age", pricing_questionnaire.get("age")), 0))
    normalized_brand = _normalize_brand(pricing_questionnaire.get("brand"))
    brand_score = calculate_brand_score(pricing_questionnaire.get("brand"))
    brand_confidence = calculate_brand_confidence(pricing_questionnaire.get("brand"))
    condition_score = calculate_condition_score(pricing_questionnaire.get("condition"))
    vintage_score = calculate_vintage_score(age, brand_score)
    has_tag = _bool(pricing_questionnaire.get("has_tag"))
    rarity_score = calculate_rarity_score(
        brand_score=brand_score,
        age=age,
        has_tag=has_tag,
        seller_comment=pricing_questionnaire.get("seller_comment"),
    )
    confirmed_value_score = calculate_confirmed_value_score(
        brand_score=brand_score,
        condition_score=condition_score,
        vintage_score=vintage_score,
        rarity_score=rarity_score,
    )

    item_type = _item_type(pricing_questionnaire)
    category_suitability = calculate_category_auction_suitability(item_type)
    base_price_result = _estimate_base_price_with_metadata(pricing_questionnaire)
    base_price = base_price_result["base_price"]

    if calculate_market_signals is not None:
        signal_input = {
            **pricing_questionnaire,
            "base_price": pricing_questionnaire.get("base_price", base_price),
            "rarity_score": pricing_questionnaire.get("rarity_score", rarity_score),
        }
        market_signals = calculate_market_signals(signal_input)
    else:
        market_signals = {
            "demand_score": 0.0,
            "interest_score": 0.0,
            "uncertainty_score": 0.0,
        }

    demand_score = _score(market_signals.get("demand_score", 0.0))
    interest_score = _score(market_signals.get("interest_score", 0.0))
    uncertainty_score = _score(market_signals.get("uncertainty_score", 0.0))
    price_pressure_score = _score(market_signals.get("price_pressure_score", 0.0))
    no_live_activity = bool(market_signals.get("no_live_activity", False))

    auction_potential_pre = calculate_auction_potential_pre(
        confirmed_value_score=confirmed_value_score,
        rarity_score=rarity_score,
        vintage_score=vintage_score,
        brand_score=brand_score,
        category_suitability=category_suitability,
    )
    auction_activity_live = calculate_auction_activity_live(
        demand_score=demand_score,
        interest_score=interest_score,
        uncertainty_score=uncertainty_score,
        confirmed_value_score=confirmed_value_score,
        price_pressure_score=price_pressure_score,
        auction_potential_pre=auction_potential_pre,
        no_live_activity=no_live_activity,
    )
    auction_attractiveness = auction_activity_live

    model_recommended_start_price = calculate_start_price(base_price, auction_potential_pre)
    initial_bid_step = calculate_bid_step(model_recommended_start_price, auction_potential_pre)
    bids_count = int(_number(pricing_questionnaire.get("bids_count"), 0))
    offers_count = int(_number(pricing_questionnaire.get("offers_count"), 0))
    existing_start_price = _number(pricing_questionnaire.get("start_price"), 0)
    current_price_from_questionnaire = _number(pricing_questionnaire.get("current_price"), 0)
    auction_status = _text(pricing_questionnaire.get("status")).lower()
    behavior_status = auction_status or (
        "active" if bids_count > 0 or offers_count > 0 or current_price_from_questionnaire > 0 else "draft"
    )
    is_published_lot = auction_status in {"active", "finished", "closed", "completed"}
    start_price_locked = (
        existing_start_price > 0
        and (is_published_lot or bids_count > 0 or offers_count > 0)
    )
    recommended_start_price = (
        _money(existing_start_price) if start_price_locked else model_recommended_start_price
    )
    recommended_bid_step = initial_bid_step
    actual_start_price_for_forecast = _number(
        pricing_questionnaire.get("start_price"),
        recommended_start_price,
    )
    live_recommended_bid_step = calculate_bid_step(
        actual_start_price_for_forecast,
        auction_activity_live,
    )
    final_price_result = _estimate_final_price_with_metadata(
        {
            **pricing_questionnaire,
            "brand": pricing_questionnaire.get("brand"),
            "category": item_type,
            "condition": pricing_questionnaire.get("condition"),
            "age": age,
            "has_tag": has_tag,
            "price": base_price,
            "base_price": base_price,
            "start_price": actual_start_price_for_forecast,
            "auction_attractiveness": auction_attractiveness,
            "auction_potential_pre": auction_potential_pre,
            "auction_activity_live": auction_activity_live,
            "confirmed_value_score": confirmed_value_score,
        }
    )
    expected_final_price_before_behavior = final_price_result["expected_final_price"]
    current_price_for_forecast = _number(
        current_price,
        _number(pricing_questionnaire.get("current_price"), recommended_start_price),
    )
    behavior_adjustment: Dict[str, Any] = {
        "expected_final_price": expected_final_price_before_behavior,
        "expected_final_price_before_behavior": expected_final_price_before_behavior,
        "buyer_behavior_score": 0.0,
        "auction_behavior_multiplier": 1.0,
        "source": "not_available",
        "explanation": "Датасет поведения ставок недоступен, используется базовый прогноз.",
    }
    if calculate_buyer_behavior_adjustment is not None:
        try:
            behavior_adjustment = calculate_buyer_behavior_adjustment(
                {
                    **pricing_questionnaire,
                    "category": item_type,
                    "status": behavior_status,
                    "base_price": base_price,
                    "auction_attractiveness": auction_activity_live,
                    "auction_potential_pre": auction_potential_pre,
                    "auction_activity_live": auction_activity_live,
                    "confirmed_value_score": confirmed_value_score,
                },
                baseline_expected_price=expected_final_price_before_behavior,
                start_price=actual_start_price_for_forecast,
                current_price=current_price_for_forecast,
            )
        except Exception:
            pass
    expected_final_price = _money(
        float(behavior_adjustment.get("expected_final_price", expected_final_price_before_behavior))
    )
    conservative_final_price = _money(
        float(
            behavior_adjustment.get(
                "conservative_final_price",
                max(current_price_for_forecast, expected_final_price * 0.94),
            )
        )
    )
    optimistic_final_price = _money(
        float(
            behavior_adjustment.get(
                "optimistic_final_price",
                max(expected_final_price, expected_final_price * 1.12),
            )
        )
    )

    recommended_bid: Dict[str, Any] = {}
    if current_price is not None and user_value is not None:
        recommended_bid = calculate_recommended_bid(
            current_price=float(current_price),
            user_value=float(user_value),
            bid_step=recommended_bid_step,
        )

    base_model_metadata = base_price_result.get("model_metadata", {}) or {}
    dataset_metadata = base_model_metadata.get("dataset", {}) or {}
    data_provenance = {
        "base_price_source": base_price_result["source"],
        "model_available": base_price_result["model_available"],
        "model_name": base_model_metadata.get("model_name"),
        "metrics": base_model_metadata.get("metrics", {}),
        "train_rows": base_model_metadata.get("train_rows"),
        "test_rows": base_model_metadata.get("test_rows"),
        "dataset_name": dataset_metadata.get("dataset_name"),
        "source_type": dataset_metadata.get("source_type", "unknown"),
        "processed_rows": dataset_metadata.get("processed_rows"),
        "currency": dataset_metadata.get("currency", "RUB"),
        "original_currency": dataset_metadata.get("original_currency"),
        "usd_to_rub": dataset_metadata.get("usd_to_rub"),
        "is_synthetic": dataset_metadata.get("is_synthetic"),
        "auction_dynamics_available": dataset_metadata.get("auction_dynamics_available"),
        "base_price_before_calibration": base_price_result.get("base_price_before_calibration"),
        "resale_calibration": base_price_result.get("resale_calibration", {}),
        "final_price_source": final_price_result["source"],
        "final_price_model_available": final_price_result["model_available"],
        "final_price_domain_reason": final_price_result.get("domain_reason"),
        "auction_behavior_source": behavior_adjustment.get("source"),
        "auction_behavior_dataset_rows": behavior_adjustment.get("dataset_rows"),
        "auction_behavior_dataset_name": behavior_adjustment.get(
            "auction_behavior_source",
            "Online Auctions Dataset",
        ),
        "bids_bucket": behavior_adjustment.get("bids_bucket", behavior_adjustment.get("bid_bucket")),
        "median_final_start_ratio": behavior_adjustment.get("median_final_start_ratio"),
        "fashion_transfer_factor": behavior_adjustment.get("fashion_transfer_factor"),
        "auction_uplift": behavior_adjustment.get("auction_uplift"),
    }
    calculation_trace = {
        "brand": normalized_brand or "unknown",
        "category": item_type,
        "condition": _text(pricing_questionnaire.get("condition"), "unknown").lower(),
        "age": age,
        "base_price": base_price,
        "base_price_before_calibration": base_price_result.get("base_price_before_calibration"),
        "resale_calibration": base_price_result.get("resale_calibration", {}),
        "brand_score": brand_score,
        "condition_score": condition_score,
        "vintage_score": vintage_score,
        "rarity_score": rarity_score,
        "category_suitability": category_suitability,
        "confirmed_value_score_formula": "Q = 0.30Q_b + 0.25Q_c + 0.25Q_r + 0.20Q_v",
        "confirmed_value_score": confirmed_value_score,
        "auction_potential_pre_formula": "A_pre = 0.40Q + 0.22Q_r + 0.14Q_v + 0.14Q_b + 0.10C_a",
        "auction_potential_pre": auction_potential_pre,
        "auction_activity_live_formula": "A_live = 0.38D + 0.22I + 0.15V + 0.20Q + 0.05P_ratio",
        "auction_activity_live": auction_activity_live,
        "auction_attractiveness_formula": "auction_attractiveness is deprecated; use A_live",
        "auction_attractiveness": auction_attractiveness,
        "start_price_formula": "P_start = max(P_base * (1 - 0.05 - 0.25A_pre), 0.55P_base)",
        "model_recommended_start_price": model_recommended_start_price,
        "recommended_start_price": recommended_start_price,
        "start_price_locked": start_price_locked,
        "actual_start_price_for_forecast": actual_start_price_for_forecast,
        "behavior_status": behavior_status,
        "bid_step_formula": "Step = P_start * (0.03 + 0.05A), where A=A_pre before publication and A=A_live for live advisory step",
        "initial_bid_step": initial_bid_step,
        "live_recommended_bid_step": live_recommended_bid_step,
        "recommended_bid_step": recommended_bid_step,
        "conservative_final_price": conservative_final_price,
        "expected_final_price": expected_final_price,
        "optimistic_final_price": optimistic_final_price,
        "expected_final_price_before_behavior": expected_final_price_before_behavior,
        "auction_behavior_formula": (
            "For draft/no-activity lots E is based on P_base, A_pre and Q with a conservative cap; "
            "after publication no-bid lots use early interest signals, and lots with bids use empirical "
            "median final/start lift by bid-count bucket"
        ),
        "auction_behavior": behavior_adjustment,
        "auction_behavior_source": behavior_adjustment.get("auction_behavior_source", "Online Auctions Dataset"),
        "bids_bucket": behavior_adjustment.get("bids_bucket", behavior_adjustment.get("bid_bucket")),
        "median_final_start_ratio": behavior_adjustment.get("median_final_start_ratio"),
        "fashion_transfer_factor": behavior_adjustment.get("fashion_transfer_factor"),
        "auction_uplift": behavior_adjustment.get("auction_uplift"),
        "pricing_confidence": behavior_adjustment.get("pricing_confidence"),
        "live_activity_detected": behavior_adjustment.get("live_activity_detected"),
    }

    missing_features = []
    if not normalized_brand or normalized_brand == "unknown":
        missing_features.append("brand")
    if _item_type(pricing_questionnaire) == "other":
        missing_features.append("category")
    if not _text(pricing_questionnaire.get("material")):
        missing_features.append("material")

    formula_explanation = {
        "brand_score": "Q_b = f(brand_prestige), Q_b in [0;1]. Если бренд не указан, Q_b = 0, потому что нет подтвержденного брендового признака.",
        "condition_score": "Q_c = {new/excellent:1.0, good:0.75, normal:0.55, bad:0.3}",
        "vintage_score": "Q_v = f(age, Q_b): формальный vintage-сигнал начинается примерно с 20 лет, но 5-19 лет дают слабый archival/pre-vintage сигнал для сильных брендов. Возраст без бренда и редкости не создает премию.",
        "rarity_score": "Q_r = 0.38Q_b + 0.25Age + 0.17Tag + 0.20Keywords - penalty. Отсутствие бирки не добавляет ценности.",
        "confirmed_value_score": "Q = 0.30Q_b + 0.25Q_c + 0.25Q_r + 0.20Q_v",
        "demand_score": "D отражает реальные торговые действия: ставки, офферы, скорость ставок и рост текущей цены относительно старта.",
        "interest_score": "I отражает пользовательскую вовлечённость до покупки: просмотры, лайки и добавления в избранное.",
        "uncertainty_score": "V отражает неопределенность цены через относительный разброс цены и редкость товара",
        "auction_potential_pre": "A_pre используется до публикации для стартовой цены и первого шага ставки: A_pre = 0.40Q + 0.22R + 0.14Q_v + 0.14Q_b + 0.10C_a.",
        "auction_activity_live": "A_live используется после публикации для прогноза и рекомендаций: A_live = 0.38D + 0.22I + 0.15V + 0.20Q + 0.05P_ratio.",
        "auction_attractiveness": "auction_attractiveness оставлен для совместимости и равен A_live.",
        "base_price": "Базовая цена рассчитывается ML-моделью на основе бренда, категории, состояния, возраста, материала и размера. Если модель недоступна, используется резервная формула.",
        "resale_calibration": "Для обычных second-hand вещей поверх ML применяется потолок перепродажи: category_anchor * brand_segment * condition * age * tag. Он не дает массовым товарам без бирки получать премиальную цену.",
        "start_price": "P_start = max(P_base * (1 - 0.05 - 0.25A_pre), 0.55P_base). После публикации лота стартовая цена не пересчитывается.",
        "bid_step": "Step = P_start * (0.03 + 0.05A). До публикации A = A_pre, для live-рекомендации A = A_live. Шаг ограничен диапазоном 2-8% и округляется до 50/100/250/500 рублей.",
        "auction_behavior": "B_bid берётся из датасета ставок: для каждого диапазона количества ставок используется медианный коэффициент final_price/start_price. Микростарты исключаются, чтобы выбросы не завышали прогноз.",
        "expected_final_price": "Сначала считается E0 по ML/формуле. До публикации прогноз строится от P_base, A_pre и Q: сильный лот получает умеренную премию, а завышенная стартовая цена не увеличивается без подтверждения спросом. После публикации лот без ставок учитывает ранний интерес, а при ставках прогноз опирается на медианный рост final/start из датасета ставок. Внешняя модель финальной цены не переносит напрямую цены электроники и часов на одежду.",
        "recommended_bid": "s* = argmax U(s), U(s) = P_win(s) * (V_user - s)",
    }

    return {
        "model_name": "Interpretable auction pricing model",
        "item_type": item_type,
        "age": age,
        "seller_questionnaire": dict(questionnaire or {}),
        "pricing_questionnaire": pricing_questionnaire,
        "evidence_report": evidence_report,
        "base_price": base_price,
        "base_price_source": base_price_result["source"],
        "model_available": base_price_result["model_available"],
        "base_price_before_calibration": base_price_result.get("base_price_before_calibration"),
        "base_price_model_metadata": base_model_metadata,
        "resale_calibration": base_price_result.get("resale_calibration", {}),
        "data_provenance": data_provenance,
        "calculation_trace": calculation_trace,
        "final_price_source": final_price_result["source"],
        "final_price_model_available": final_price_result["model_available"],
        "final_price_domain_reason": final_price_result.get("domain_reason"),
        "expected_final_price_before_behavior": expected_final_price_before_behavior,
        "auction_behavior": behavior_adjustment,
        "base_price_reasoning": (
            "P_base is the resale market estimate from the Mercari-trained model "
            "or the deterministic fallback if the model is unavailable."
        ),
        "auction_behavior_source": behavior_adjustment.get(
            "auction_behavior_source",
            "Online Auctions Dataset",
        ),
        "bids_bucket": behavior_adjustment.get("bids_bucket", behavior_adjustment.get("bid_bucket")),
        "median_final_start_ratio": behavior_adjustment.get("median_final_start_ratio"),
        "fashion_transfer_factor": behavior_adjustment.get("fashion_transfer_factor"),
        "auction_uplift": behavior_adjustment.get("auction_uplift"),
        "pricing_confidence": behavior_adjustment.get("pricing_confidence"),
        "live_activity_detected": behavior_adjustment.get("live_activity_detected"),
        "buyer_behavior_score": behavior_adjustment.get("buyer_behavior_score", 0.0),
        "auction_behavior_multiplier": behavior_adjustment.get("auction_behavior_multiplier", 1.0),
        "brand_score": brand_score,
        "brand_confidence": brand_confidence,
        "brand_normalized": normalized_brand or "unknown",
        "brand_source": evidence_report.get("decisions", {}).get("brand", {}).get(
            "source",
            "seller_questionnaire" if brand_confidence > 0 else "not_provided",
        ),
        "missing_features": missing_features,
        "condition_score": condition_score,
        "vintage_score": vintage_score,
        "rarity_score": rarity_score,
        "confirmed_value_score": confirmed_value_score,
        "value_score": confirmed_value_score,
        "demand_score": demand_score,
        "uncertainty_score": uncertainty_score,
        "interest_score": interest_score,
        "price_pressure_score": price_pressure_score,
        "category_auction_suitability": category_suitability,
        "market_signals": market_signals,
        "auction_potential_pre": auction_potential_pre,
        "auction_activity_live": auction_activity_live,
        "auction_attractiveness": auction_attractiveness,
        "auction_attractiveness_deprecated": True,
        "no_live_activity": no_live_activity,
        "start_price_locked": start_price_locked,
        "model_recommended_start_price": model_recommended_start_price,
        "recommended_start_price": recommended_start_price,
        "initial_bid_step": initial_bid_step,
        "live_recommended_bid_step": live_recommended_bid_step,
        "actual_start_price_for_forecast": actual_start_price_for_forecast,
        "recommended_bid_step": recommended_bid_step,
        "conservative_final_price": conservative_final_price,
        "expected_final_price": expected_final_price,
        "optimistic_final_price": optimistic_final_price,
        "recommended_bid": recommended_bid,
        "formula_explanation": {
            **formula_explanation,
            "demand_score": "D отражает реальные торговые действия: ставки, офферы, скорость ставок и рост текущей цены относительно старта. Просмотры и лайки сюда не входят.",
            "interest_score": "I отражает интерес без обязательной готовности платить: просмотры, лайки и добавления в избранное.",
            "auction_potential_pre": "A_pre используется только до публикации лота. Он показывает потенциал аукциона по устойчивым признакам товара: Q, редкости, винтажности, бренду и категории.",
            "auction_activity_live": "A_live используется после публикации. Он показывает текущую активность торгов по D, I, V, Q и росту цены относительно старта.",
            "auction_attractiveness": "Поле auction_attractiveness оставлено для совместимости старого фронта и равно A_live.",
            "base_price": "P_base — рыночная resale-оценка товара. Она рассчитывается ML-моделью на основе бренда, категории, состояния, возраста, материала и размера. Если модель недоступна, используется резервная формула.",
            "start_price": "P_start = max(P_base * (1 - 0.05 - 0.25A_pre), 0.55P_base). После публикации лота стартовая цена не пересчитывается.",
            "bid_step": "Step = P_start * (0.03 + 0.05A). Начальный шаг использует A_pre и фиксируется при публикации; live-рекомендация использует A_live как подсказку продавцу.",
            "expected_final_price": "E[P_final] возвращается как диапазон: conservative / expected / optimistic. P_base задаётся resale-моделью, а Online Auctions Dataset влияет только на аукционный uplift по bucket ставок: 1, 2-3, 4-6, 7-12, 13+.",
        },
    }
