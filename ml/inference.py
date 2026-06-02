import json
from pathlib import Path
from typing import Any, Dict

import joblib
import pandas as pd

try:
    from ml.config import (
        BASE_MODEL_FEATURES,
        BASE_PRICE_METRICS_PATH,
        BASE_PRICE_MODEL_PATH,
        FINAL_MODEL_FEATURES,
        FINAL_PRICE_METRICS_PATH,
        FINAL_PRICE_MODEL_PATH,
    )
except ImportError:
    from config import (
        BASE_MODEL_FEATURES,
        BASE_PRICE_METRICS_PATH,
        BASE_PRICE_MODEL_PATH,
        FINAL_MODEL_FEATURES,
        FINAL_PRICE_METRICS_PATH,
        FINAL_PRICE_MODEL_PATH,
    )


_BASE_PRICE_MODEL = None
_FINAL_PRICE_MODEL = None

# The current external bid dataset contains auction mechanics for watches and
# electronics. It is useful as empirical bid dynamics, but direct ML inference
# should be limited to categories represented in that auction dataset.
AUCTION_FINAL_MODEL_CATEGORIES = {"pda", "console", "watch", "wristwatch"}


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


def _bool_as_model_value(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return "true" if _text(value).lower() in {"1", "true", "yes", "y", "да"} else "false"


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _base_model_metadata() -> Dict[str, Any]:
    report = _load_json(Path(BASE_PRICE_METRICS_PATH))
    best_model = report.get("best_model")
    metrics = (report.get("metrics") or {}).get(best_model, {}) if best_model else {}
    return {
        "model_name": best_model,
        "metrics": metrics,
        "target_transform": report.get("target_transform"),
        "train_rows": report.get("train_rows"),
        "test_rows": report.get("test_rows"),
        "dataset": report.get("dataset") or {},
    }


def _final_model_is_enabled() -> bool:
    report = _load_json(Path(FINAL_PRICE_METRICS_PATH))
    if not report:
        return True
    return bool(report.get("trained", True))


def _normalized_base_features(questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    category = _text(
        questionnaire.get("subcategory") or questionnaire.get("category"),
        "other",
    ).lower()

    return {
        "brand": _text(questionnaire.get("brand"), "unknown").lower(),
        "category": category or "other",
        "condition": _text(questionnaire.get("condition"), "normal").lower(),
        "age": _number(questionnaire.get("age", questionnaire.get("estimated_age")), 0),
        "material": _text(questionnaire.get("material"), "mixed").lower(),
        "size": _text(questionnaire.get("size"), "OS").upper(),
        "has_tag": _bool_as_model_value(questionnaire.get("has_tag", False)),
    }


def _normalized_final_features(features: Dict[str, Any]) -> Dict[str, Any]:
    base_features = _normalized_base_features(features)
    return {
        "price": _number(features.get("price", features.get("base_price")), 0),
        "start_price": _number(features.get("start_price"), 0),
        "brand": base_features["brand"],
        "category": base_features["category"],
        "condition": base_features["condition"],
        "age": base_features["age"],
        "views_count": _number(features.get("views_count"), 0),
        "likes_count": _number(features.get("likes_count"), 0),
        "favorites_count": _number(features.get("favorites_count"), 0),
        "bids_count": _number(features.get("bids_count"), 0),
        "has_tag": base_features["has_tag"],
    }


def load_base_price_model():
    """Load and cache the trained base price model, returning None when it is unavailable."""
    global _BASE_PRICE_MODEL

    if _BASE_PRICE_MODEL is not None:
        return _BASE_PRICE_MODEL

    model_path = Path(BASE_PRICE_MODEL_PATH)
    if not model_path.exists():
        return None

    try:
        _BASE_PRICE_MODEL = joblib.load(model_path)
        return _BASE_PRICE_MODEL
    except Exception:
        _BASE_PRICE_MODEL = None
        return None


def load_final_price_model():
    """Load and cache the trained final auction price model, returning None if unavailable."""
    global _FINAL_PRICE_MODEL

    if _FINAL_PRICE_MODEL is not None:
        return _FINAL_PRICE_MODEL

    if not _final_model_is_enabled():
        return None

    model_path = Path(FINAL_PRICE_MODEL_PATH)
    if not model_path.exists():
        return None

    try:
        _FINAL_PRICE_MODEL = joblib.load(model_path)
        return _FINAL_PRICE_MODEL
    except Exception:
        _FINAL_PRICE_MODEL = None
        return None


def fallback_base_price(questionnaire: Dict[str, Any]) -> float:
    """Estimate base price with a deterministic reserve formula when ML is unavailable."""
    item = _normalized_base_features(questionnaire)
    brand = item["brand"].replace("`", "'")
    category = item["category"]
    condition = item["condition"]
    age = _number(item["age"], 0)

    category_base_prices = {
        "jacket": 4500,
        "bomber": 5500,
        "hoodie": 3500,
        "jeans": 3000,
        "sneakers": 5000,
        "coat": 7000,
        "tshirt": 1500,
        "shirt": 2000,
        "bag": 4000,
        "cap": 1200,
        "other": 2500,
    }
    brand_multipliers = {
        "stone island": 2.2,
        "levi's": 1.6,
        "levis": 1.6,
        "carhartt": 1.5,
        "nike": 1.4,
        "adidas": 1.3,
        "ralph lauren": 1.4,
        "tommy hilfiger": 1.3,
        "zara": 0.8,
        "h&m": 0.7,
        "unknown": 0.6,
        "no_name": 0.5,
        "no name": 0.5,
    }
    condition_multipliers = {
        "excellent": 1.15,
        "good": 1.0,
        "normal": 0.8,
        "bad": 0.55,
    }

    base_price = category_base_prices.get(category, category_base_prices["other"])
    brand_multiplier = brand_multipliers.get(brand, 0.75)
    condition_multiplier = condition_multipliers.get(condition, 0.8)

    strong_brands = {
        "stone island",
        "levi's",
        "levis",
        "carhartt",
        "nike",
        "adidas",
        "ralph lauren",
        "tommy hilfiger",
    }
    weak_brands = {"unknown", "no_name", "no name"}

    age_multiplier = 1.0
    if age >= 10 and brand in strong_brands:
        age_multiplier += min(0.25, 0.10 + (age - 10) * 0.01)
    elif age >= 10 and brand in weak_brands:
        age_multiplier -= min(0.20, 0.10 + (age - 10) * 0.008)

    price = base_price * brand_multiplier * condition_multiplier * age_multiplier
    return round(max(300.0, price), 2)


def predict_base_price(questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict base market price from questionnaire fields.

    Returns model metadata so backend and diploma formulas can show whether
    the value came from the trained ML model or from the reserve formula.
    """
    model = load_base_price_model()
    model_available = model is not None

    if model_available:
        try:
            item = _normalized_base_features(questionnaire)
            row = {feature: item.get(feature) for feature in BASE_MODEL_FEATURES}
            prediction = model.predict(pd.DataFrame([row]))[0]
            return {
                "base_price": round(max(300.0, float(prediction)), 2),
                "source": "ml_model",
                "model_available": True,
                "model_metadata": _base_model_metadata(),
            }
        except Exception:
            pass

    return {
        "base_price": fallback_base_price(questionnaire),
        "source": "fallback_formula",
        "model_available": model_available,
        "model_metadata": _base_model_metadata(),
    }


def _fallback_final_price(features: Dict[str, Any]) -> float:
    base_price = _number(features.get("base_price", features.get("price")), 0)
    if base_price <= 0:
        base_price = fallback_base_price(features)

    auction_attractiveness = _number(
        features.get("auction_activity_live", features.get("auction_attractiveness")),
        0,
    )
    confirmed_value_score = _number(features.get("confirmed_value_score"), 0)
    expected_final_price = base_price * (
        1 + 0.35 * auction_attractiveness + 0.25 * confirmed_value_score
    )
    return round(max(300.0, expected_final_price), 2)


def predict_final_price(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Predict expected final auction price from price, start price and demand features.

    If the trained model is unavailable or fails, the function returns a
    deterministic formula based on auction attractiveness and confirmed value.
    """
    model = load_final_price_model()
    model_available = model is not None

    if model_available:
        try:
            item = _normalized_final_features(features)
            if item["category"] not in AUCTION_FINAL_MODEL_CATEGORIES:
                return {
                    "expected_final_price": _fallback_final_price(features),
                    "source": "fallback_formula",
                    "model_available": True,
                    "domain_reason": (
                        "final_price_model is trained on external auction data "
                        "outside this product category"
                    ),
                }
            row = {feature: item.get(feature) for feature in FINAL_MODEL_FEATURES}
            prediction = model.predict(pd.DataFrame([row]))[0]
            return {
                "expected_final_price": round(max(300.0, float(prediction)), 2),
                "source": "ml_model",
                "model_available": True,
            }
        except Exception:
            pass

    return {
        "expected_final_price": _fallback_final_price(features),
        "source": "fallback_formula",
        "model_available": model_available,
    }


if __name__ == "__main__":
    sample = {
        "brand": "levi's",
        "category": "jeans",
        "condition": "good",
        "age": 12,
        "material": "denim",
        "size": "M",
        "has_tag": True,
        "price": 7000,
        "start_price": 5200,
        "views_count": 180,
        "likes_count": 24,
        "favorites_count": 12,
        "bids_count": 5,
        "auction_attractiveness": 0.5,
        "confirmed_value_score": 0.72,
    }
    print(predict_base_price(sample))
    print(predict_final_price(sample))
