from typing import Any, Dict


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


def _brand_key(brand: Any) -> str:
    return " ".join(_text(brand).lower().replace("`", "'").replace("_", " ").split())


def _item_type(questionnaire: Dict[str, Any]) -> str:
    explicit = _text(
        questionnaire.get("subcategory") or questionnaire.get("type") or questionnaire.get("category"),
        "other",
    ).lower()
    text_blob = " ".join(
        _text(questionnaire.get(field)).lower()
        for field in ("title", "description", "seller_comment")
    )
    if explicit == "trench" or (
        explicit in {"outerwear", "coat", "jacket", "other"} and any(
            marker in text_blob for marker in {"trench", "тренч", "тренчкот", "тренч-кот"}
        )
    ):
        return "trench"
    return explicit


def get_brand_segment(brand: Any) -> str:
    """Classify brand into a resale segment used by the calibration layer."""
    brand_key = _brand_key(brand)
    luxury = {"gucci", "prada", "burberry", "stone island"}
    vintage_premium = {"carhartt", "levi's", "levis", "ralph lauren", "diesel"}
    sports_mass = {"adidas", "nike", "puma", "reebok", "new balance", "vans", "converse"}
    mass = {"zara", "h&m", "uniqlo", "bershka", "pull&bear", "mango"}
    no_name = {"", "unknown", "not specified", "не указан", "no name", "no-name", "no_name", "noname", "generic"}

    if brand_key in luxury:
        return "luxury"
    if brand_key in vintage_premium:
        return "vintage_premium"
    if brand_key in sports_mass:
        return "sports_mass"
    if brand_key in mass:
        return "mass"
    if brand_key in no_name:
        return "no_name"
    return "other_brand"


def calculate_resale_ceiling(questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estimate a conservative second-hand ceiling for common non-vintage goods.

    This is not a replacement for ML. It is a calibration layer that prevents
    common used tops from being priced like premium archive items. The ceiling
    depends on category anchor, brand segment, condition, age and tag evidence.
    """
    item_type = _item_type(questionnaire)
    age = _number(questionnaire.get("estimated_age", questionnaire.get("age")), 0)
    has_tag = _bool(questionnaire.get("has_tag"))
    condition = _text(questionnaire.get("condition"), "normal").lower()
    segment = get_brand_segment(questionnaire.get("brand"))

    category_anchors = {
        "tshirt": 2200,
        "top": 2300,
        "longsleeve": 2600,
        "shirt": 2800,
        "tops": 2500,
        "blouse": 3000,
        "hoodie": 4300,
        "sweater": 4200,
        "jeans": 4200,
        "pants": 3800,
        "bottoms": 3600,
        "shorts": 2600,
        "skirt": 2800,
        "dress": 5200,
        "dresses": 5200,
        "cap": 1900,
        "belt": 2600,
        "scarf": 3400,
        "jewelry": 4500,
        "bag": 5200,
        "accessories": 4200,
        "sneakers": 6200,
        "boots": 6800,
        "loafers": 6500,
        "shoes": 6200,
        "jacket": 6200,
        "leather_jacket": 9800,
        "denim_jacket": 5800,
        "windbreaker": 5200,
        "puffer": 7600,
        "sheepskin": 12500,
        "bomber": 7200,
        "coat": 7600,
        "trench": 14500,
        "outerwear": 7600,
        "other": 3000,
    }
    brand_multipliers = {
        "luxury": 2.4,
        "vintage_premium": 1.35,
        "sports_mass": 1.05,
        "mass": 0.82,
        "other_brand": 0.9,
        "no_name": 0.62,
    }
    condition_multipliers = {
        "excellent": 1.0,
        "good": 0.84,
        "normal": 0.64,
        "bad": 0.4,
        "unknown": 0.7,
        "": 0.7,
    }

    if age <= 1:
        age_multiplier = 1.0
    elif age <= 3:
        age_multiplier = 0.9
    elif age <= 6:
        age_multiplier = 0.82
    elif age <= 9:
        age_multiplier = 0.68
    elif segment in {"luxury", "vintage_premium"}:
        age_multiplier = 1.05
    else:
        age_multiplier = 0.52

    tag_multiplier = 1.08 if has_tag else 0.9
    anchor = category_anchors.get(item_type, category_anchors["other"])
    brand_multiplier = brand_multipliers.get(segment, brand_multipliers["other_brand"])
    condition_multiplier = condition_multipliers.get(condition, condition_multipliers["unknown"])

    ceiling = anchor * brand_multiplier * condition_multiplier * age_multiplier * tag_multiplier
    floor_ratios = {
        "luxury": 0.48,
        "vintage_premium": 0.36,
        "sports_mass": 0.30,
        "mass": 0.24,
        "other_brand": 0.28,
        "no_name": 0.16,
    }
    floor_price = anchor * brand_multiplier * floor_ratios.get(segment, 0.24) * condition_multiplier
    return {
        "ceiling_price": round(max(300.0, ceiling), 2),
        "floor_price": round(max(300.0, floor_price), 2),
        "category_anchor": anchor,
        "brand_segment": segment,
        "brand_multiplier": brand_multiplier,
        "condition_multiplier": condition_multiplier,
        "age_multiplier": round(age_multiplier, 4),
        "tag_multiplier": tag_multiplier,
        "applies_to": "common_resale_calibration",
        "formula": "ceiling = category_anchor * brand_segment * condition * age * tag",
    }


def apply_resale_calibration(questionnaire: Dict[str, Any], base_price: float) -> Dict[str, Any]:
    """Return calibrated base price and a transparent explanation."""
    ceiling = calculate_resale_ceiling(questionnaire)
    raw_price = float(base_price)
    calibrated = min(raw_price, ceiling["ceiling_price"])
    calibrated = max(calibrated, ceiling["floor_price"])
    capped = calibrated < raw_price
    raised = calibrated > raw_price
    applied = capped or raised

    return {
        "base_price_before_calibration": round(raw_price, 2),
        "base_price_after_calibration": round(calibrated, 2),
        "calibration_applied": applied,
        "ceiling": ceiling,
        "reason": (
            "ML price was above conservative second-hand resale ceiling"
            if capped
            else (
                "ML price was below conservative second-hand resale floor for this brand/category"
                if raised
                else "ML price is within conservative second-hand resale interval"
            )
        ),
    }
