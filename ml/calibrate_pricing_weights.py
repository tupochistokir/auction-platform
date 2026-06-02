import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, Tuple, Union

import numpy as np
import pandas as pd

from config import (
    DATA_DIR,
    MAX_METRIC_ROWS,
    RANDOM_STATE,
    REPORTS_DIR,
    TRAIN_DATA_PATH,
)

OUTPUT_PATH = REPORTS_DIR / "calibrated_weights.json"

DEFAULT_BRAND_SCORES = {
    "stone island": 0.96,
    "gucci": 0.94,
    "prada": 0.93,
    "burberry": 0.90,
    "the north face": 0.88,
    "levi's": 0.88,
    "levis": 0.88,
    "carhartt": 0.86,
    "nike": 0.82,
    "adidas": 0.76,
    "ralph lauren": 0.80,
    "tommy hilfiger": 0.74,
    "uniqlo": 0.46,
    "zara": 0.48,
    "h&m": 0.38,
    "unknown": 0.20,
    "no_name": 0.12,
    "no name": 0.12,
}

CONDITION_SCORES = {
    "excellent": 1.0,
    "good": 0.75,
    "normal": 0.55,
    "bad": 0.30,
}


def clamp(value: Union[pd.Series, np.ndarray, float], min_value: float = 0.0, max_value: float = 1.0):
    return np.clip(value, min_value, max_value)


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower().replace("`", "'")


def load_reference_brand_scores() -> Dict[str, float]:
    """Load brand scores from references/brands.csv and merge with fallback scores."""
    scores = dict(DEFAULT_BRAND_SCORES)
    path = DATA_DIR / "references" / "brands.csv"
    if not path.exists():
        return scores

    try:
        refs = pd.read_csv(path)
        for _, row in refs.iterrows():
            brand = normalize_text(row.get("brand"))
            if not brand:
                continue
            scores[brand] = float(row.get("brand_score"))
    except Exception:
        return scores

    return scores


def build_scores(dataset: pd.DataFrame) -> pd.DataFrame:
    """Create Q components when the processed dataset does not already contain them."""
    scored = dataset.copy()

    brand_scores = load_reference_brand_scores()
    if "brand_score" not in scored:
        scored["brand_score"] = (
            scored.get("brand", "unknown")
            .map(lambda value: brand_scores.get(normalize_text(value), 0.35))
            .astype(float)
        )

    if "condition_score" not in scored:
        if "condition" in scored:
            scored["condition_score"] = (
                scored["condition"]
                .map(lambda value: CONDITION_SCORES.get(normalize_text(value), 0.55))
                .astype(float)
            )
        elif "wear_percent" in scored:
            wear = pd.to_numeric(scored["wear_percent"], errors="coerce").fillna(50)
            scored["condition_score"] = clamp(1 - wear / 100)
        else:
            scored["condition_score"] = 0.55

    age = pd.to_numeric(scored.get("age", 0), errors="coerce").fillna(0)
    if "has_tag" in scored:
        has_tag = (
            scored["has_tag"]
            .astype(str)
            .str.lower()
            .isin({"true", "1", "yes", "y"})
            .astype(float)
        )
    else:
        has_tag = pd.Series(0.0, index=scored.index)

    if "vintage_score" not in scored:
        age_factor = clamp((age - 10) / 25)
        strong_brand = scored["brand_score"] >= 0.80
        weak_brand = scored["brand_score"] <= 0.35
        scored["vintage_score"] = np.where(
            age < 10,
            0.0,
            np.where(
                strong_brand,
                0.55 + 0.40 * age_factor,
                np.where(weak_brand, np.maximum(0.0, 0.12 - 0.12 * age_factor), 0.18 + 0.24 * age_factor),
            ),
        )

    if "rarity_score" not in scored:
        age_factor = clamp(age / 35)
        rarity = 0.48 * scored["brand_score"] + 0.30 * age_factor + 0.22 * has_tag
        rarity = np.where((age >= 10) & (scored["brand_score"] <= 0.35), rarity - 0.10, rarity)
        scored["rarity_score"] = clamp(rarity)

    for column in ["brand_score", "condition_score", "rarity_score", "vintage_score"]:
        scored[column] = pd.to_numeric(scored[column], errors="coerce").fillna(0.0)
        scored[column] = clamp(scored[column].to_numpy())

    return scored


def choose_target(dataset: pd.DataFrame) -> Tuple[str, pd.Series]:
    """Prefer final_price only when real auction rows exist, otherwise use marketplace price."""
    if "is_auction_data" in dataset:
        auction_mask = dataset["is_auction_data"].astype(str).str.lower() == "true"
        if auction_mask.any() and "final_price" in dataset:
            return "final_price", pd.to_numeric(dataset.loc[auction_mask, "final_price"], errors="coerce")

    if "price" in dataset:
        return "price", pd.to_numeric(dataset["price"], errors="coerce")
    if "final_price" in dataset:
        return "final_price", pd.to_numeric(dataset["final_price"], errors="coerce")
    raise ValueError("train.csv must contain price or final_price")


def choose_base_price(dataset: pd.DataFrame, target_name: str) -> Tuple[str, pd.Series]:
    """Choose a base anchor that does not leak the target directly."""
    if "base_price" in dataset:
        return "base_price_column", pd.to_numeric(dataset["base_price"], errors="coerce")

    if target_name == "final_price" and "start_price" in dataset:
        return "start_price", pd.to_numeric(dataset["start_price"], errors="coerce")

    if "category" in dataset and target_name in dataset:
        target = pd.to_numeric(dataset[target_name], errors="coerce")
        category_medians = dataset.assign(_target=target).groupby("category")["_target"].median()
        return "category_median_price", dataset["category"].map(category_medians)

    if "start_price" in dataset:
        return "start_price", pd.to_numeric(dataset["start_price"], errors="coerce")

    raise ValueError("Cannot build base price anchor: no base_price, category or start_price")


def iter_weight_grid(step: float = 0.05):
    units = int(round(1 / step))
    for brand in range(units + 1):
        for condition in range(units - brand + 1):
            for rarity in range(units - brand - condition + 1):
                vintage = units - brand - condition - rarity
                yield (
                    round(brand * step, 2),
                    round(condition * step, 2),
                    round(rarity * step, 2),
                    round(vintage * step, 2),
                )


def calibrate() -> Dict[str, Any]:
    if not TRAIN_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {TRAIN_DATA_PATH}. Run python ml/prepare_dataset.py"
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(TRAIN_DATA_PATH)
    target_name, target = choose_target(dataset)

    if "is_auction_data" in dataset and target_name == "final_price":
        dataset = dataset[dataset["is_auction_data"].astype(str).str.lower() == "true"].copy()
        target = pd.to_numeric(dataset[target_name], errors="coerce")

    if len(dataset) > MAX_METRIC_ROWS:
        dataset = dataset.sample(n=MAX_METRIC_ROWS, random_state=RANDOM_STATE).copy()
        target = target.loc[dataset.index]

    dataset = build_scores(dataset)
    base_source, base_price = choose_base_price(dataset, target_name)

    calibration_frame = pd.DataFrame(
        {
            "target": target,
            "base_price": pd.to_numeric(base_price, errors="coerce"),
            "brand_score": dataset["brand_score"],
            "condition_score": dataset["condition_score"],
            "rarity_score": dataset["rarity_score"],
            "vintage_score": dataset["vintage_score"],
        }
    ).dropna()
    calibration_frame = calibration_frame[
        (calibration_frame["target"] > 0) & (calibration_frame["base_price"] > 0)
    ]

    if calibration_frame.empty:
        raise ValueError("No valid rows for calibration")

    target_values = calibration_frame["target"].to_numpy(dtype=float)
    base_values = calibration_frame["base_price"].to_numpy(dtype=float)
    brand = calibration_frame["brand_score"].to_numpy(dtype=float)
    condition = calibration_frame["condition_score"].to_numpy(dtype=float)
    rarity = calibration_frame["rarity_score"].to_numpy(dtype=float)
    vintage = calibration_frame["vintage_score"].to_numpy(dtype=float)

    best = {
        "mae": math.inf,
        "weights": None,
        "mean_q": None,
    }

    for weights in iter_weight_grid(step=0.05):
        w_brand, w_condition, w_rarity, w_vintage = weights
        q = (
            w_brand * brand
            + w_condition * condition
            + w_rarity * rarity
            + w_vintage * vintage
        )
        predicted = base_values * (1 + 0.25 * q)
        mae = float(np.mean(np.abs(predicted - target_values)))
        if mae < best["mae"]:
            best = {
                "mae": mae,
                "weights": weights,
                "mean_q": float(np.mean(q)),
            }

    w_brand, w_condition, w_rarity, w_vintage = best["weights"]
    feature_variance = {
        "brand": round(float(np.std(brand)), 6),
        "condition": round(float(np.std(condition)), 6),
        "rarity": round(float(np.std(rarity)), 6),
        "vintage": round(float(np.std(vintage)), 6),
    }
    degenerate_features = [
        name for name, std_value in feature_variance.items() if std_value < 0.01
    ]
    calibration_status = "data_supported"
    recommended_weights = {
        "brand": w_brand,
        "condition": w_condition,
        "rarity": w_rarity,
        "vintage": w_vintage,
    }
    limitations = []
    if degenerate_features or float(best["mean_q"]) < 0.05:
        calibration_status = "limited_not_applied"
        recommended_weights = {
            "brand": 0.30,
            "condition": 0.25,
            "rarity": 0.25,
            "vintage": 0.20,
        }
        limitations.append(
            "The current marketplace dataset does not contain enough independent "
            "variation for all Q components. In particular, Mercari preprocessing "
            "does not provide real item age, so vintage_score is not a reliable "
            "calibration signal."
        )

    result = {
        "formula": "Q = w_brand*brand_score + w_condition*condition_score + w_rarity*rarity_score + w_vintage*vintage_score",
        "price_formula": "predicted_price = base_price * (1 + 0.25 * Q)",
        "constraints": {
            "non_negative": True,
            "sum_weights": 1.0,
            "grid_step": 0.05,
        },
        "target": target_name,
        "base_price_source": base_source,
        "rows_used": int(len(calibration_frame)),
        "best_mae": round(float(best["mae"]), 4),
        "mean_q": round(float(best["mean_q"]), 4),
        "raw_grid_search_weights": {
            "brand": w_brand,
            "condition": w_condition,
            "rarity": w_rarity,
            "vintage": w_vintage,
        },
        "recommended_weights": recommended_weights,
        "calibration_status": calibration_status,
        "feature_variance": feature_variance,
        "degenerate_features": degenerate_features,
        "limitations": limitations,
        "current_expert_weights": {
            "brand": 0.30,
            "condition": 0.25,
            "rarity": 0.25,
            "vintage": 0.20,
        },
        "interpretation": (
            "The file does not automatically replace expert weights in math_core.py. "
            "When calibration_status is limited_not_applied, the grid-search result "
            "is treated as a diagnostic rather than a production replacement, because "
            "the current dataset cannot justify changing all expert weights."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    print(json.dumps(calibrate(), ensure_ascii=False, indent=2))
