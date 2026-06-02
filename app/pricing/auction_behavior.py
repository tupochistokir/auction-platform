"""Auction behavior calibration for live bidding forecasts.

Mercari-like resale data answers how much a clothing item costs before an
auction starts. The Online Auctions Dataset answers a different question: how
the final price changes when bidders actually compete. This module transfers
only the behavioral part of that dataset into the fashion resale domain.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BEHAVIOR_REPORT_PATH = PROJECT_ROOT / "ml" / "reports" / "auction_behavior_model.json"

ONLINE_AUCTIONS_DATASET_NAME = "Online Auctions Dataset"
FASHION_TRANSFER_FACTOR = 0.30
ACCESSORY_TRANSFER_FACTOR = 0.40
MAX_FASHION_UPLIFT = 2.15
MAX_ACCESSORY_UPLIFT = 2.45

BID_BUCKET_MEDIAN_RATIOS = {
    "0": 1.0,
    "1": 1.0,
    "2-3": 1.0417,
    "4-6": 1.193,
    "7-12": 1.6667,
    "13+": 5.6357,
}

_BEHAVIOR_REPORT: Optional[Dict[str, Any]] = None


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip().lower()


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _money(value: float) -> float:
    return round(max(0.0, float(value or 0.0)), 2)


def _load_report() -> Dict[str, Any]:
    global _BEHAVIOR_REPORT
    if _BEHAVIOR_REPORT is not None:
        return _BEHAVIOR_REPORT

    if BEHAVIOR_REPORT_PATH.exists():
        try:
            _BEHAVIOR_REPORT = json.loads(BEHAVIOR_REPORT_PATH.read_text(encoding="utf-8"))
            return _BEHAVIOR_REPORT
        except Exception:
            pass

    _BEHAVIOR_REPORT = {
        "dataset_name": ONLINE_AUCTIONS_DATASET_NAME,
        "dataset_rows": 0,
        "bid_bucket_lift_medians": BID_BUCKET_MEDIAN_RATIOS,
        "domain_transfer": {
            "clothing_category_weight": FASHION_TRANSFER_FACTOR,
            "matched_category_weight": ACCESSORY_TRANSFER_FACTOR,
            "reason": (
                "Fallback constants reproduce the robust median final/start "
                "ratios used in the project report."
            ),
        },
    }
    return _BEHAVIOR_REPORT


def _bid_bucket(bids_count: float) -> str:
    bids = int(max(0, bids_count))
    if bids <= 0:
        return "0"
    if bids == 1:
        return "1"
    if bids <= 3:
        return "2-3"
    if bids <= 6:
        return "4-6"
    if bids <= 12:
        return "7-12"
    return "13+"


def _next_bucket(bucket: str) -> str:
    order = ["0", "1", "2-3", "4-6", "7-12", "13+"]
    try:
        index = order.index(bucket)
    except ValueError:
        return "2-3"
    return order[min(index + 1, len(order) - 1)]


def _transfer_factor(category: str, report: Dict[str, Any]) -> float:
    transfer = report.get("domain_transfer", {}) or {}
    matched = set(transfer.get("matched_categories", ["accessories", "bag", "cap", "scarf"]))
    if category in matched:
        return _clamp(
            float(transfer.get("matched_category_weight", ACCESSORY_TRANSFER_FACTOR)),
            0.25,
            ACCESSORY_TRANSFER_FACTOR,
        )
    return _clamp(
        float(transfer.get("clothing_category_weight", FASHION_TRANSFER_FACTOR)),
        0.25,
        FASHION_TRANSFER_FACTOR,
    )


def _auction_uplift(median_ratio: float, transfer_factor: float, category: str) -> float:
    raw_uplift = 1.0 + max(0.0, median_ratio - 1.0) * transfer_factor
    max_uplift = MAX_ACCESSORY_UPLIFT if category in {"accessories", "bag", "cap", "scarf"} else MAX_FASHION_UPLIFT
    return round(_clamp(raw_uplift, 1.0, max_uplift), 4)


def _confidence(
    bids_count: float,
    bidders_count: float,
    views_count: float,
    offers_count: float,
    status: str,
) -> float:
    if status == "finished":
        return 1.0
    score = (
        0.45 * min(1.0, bids_count / 8.0)
        + 0.25 * min(1.0, bidders_count / 5.0)
        + 0.15 * min(1.0, offers_count / 4.0)
        + 0.15 * min(1.0, views_count / 300.0)
    )
    return round(_clamp(score, 0.15 if bids_count <= 0 else 0.25, 0.92), 4)


def _range_for_draft(
    base_price: float,
    current: float,
    auction_potential: float,
    confirmed_value: float,
    baseline: float,
    seller_overpriced: bool,
) -> Dict[str, float]:
    if seller_overpriced:
        conservative = current
        expected = max(current, min(baseline, current * (1.01 + 0.015 * auction_potential)))
        optimistic = max(expected, current * (1.04 + 0.05 * auction_potential))
    else:
        conservative = max(current * 1.03, base_price * (1.02 + 0.02 * auction_potential))
        expected = max(
            conservative,
            base_price * (1.08 + 0.10 * auction_potential + 0.05 * confirmed_value),
        )
        optimistic = max(
            expected,
            base_price * (1.18 + 0.18 * auction_potential + 0.08 * confirmed_value),
        )
    return {
        "conservative_final_price": _money(conservative),
        "expected_final_price": _money(expected),
        "optimistic_final_price": _money(optimistic),
    }


def _range_for_interest_only(
    base_price: float,
    current: float,
    interest_pressure: float,
    attractiveness: float,
    confirmed_value: float,
    baseline: float,
) -> Dict[str, float]:
    conservative = max(current, current * (1.01 + 0.03 * interest_pressure))
    expected = max(
        conservative,
        min(
            baseline,
            max(current * (1.03 + 0.07 * interest_pressure), base_price * (0.98 + 0.08 * attractiveness)),
        ),
    )
    optimistic = max(
        expected,
        min(
            max(baseline, base_price * (1.08 + 0.12 * attractiveness + 0.05 * confirmed_value)),
            current * (1.08 + 0.12 * interest_pressure + 0.05 * attractiveness),
        ),
    )
    return {
        "conservative_final_price": _money(conservative),
        "expected_final_price": _money(expected),
        "optimistic_final_price": _money(optimistic),
    }


def _range_for_live_bids(
    current: float,
    auction_uplift: float,
    next_uplift: float,
    behavior_score: float,
    attractiveness: float,
    category: str,
) -> Dict[str, float]:
    conservative = current * (1.0 + max(0.015, (auction_uplift - 1.0) * 0.45))
    max_growth = MAX_ACCESSORY_UPLIFT if category in {"accessories", "bag", "cap", "scarf"} else MAX_FASHION_UPLIFT
    expected = min(
        current * max_growth,
        current * auction_uplift * (1.0 + 0.025 * behavior_score + 0.015 * attractiveness),
    )
    optimistic = min(
        current * max_growth,
        max(expected, current * next_uplift * (1.0 + 0.08 * behavior_score + 0.04 * attractiveness)),
    )
    return {
        "conservative_final_price": _money(conservative),
        "expected_final_price": _money(expected),
        "optimistic_final_price": _money(optimistic),
    }


def calculate_buyer_behavior_adjustment(
    features: Dict[str, Any],
    baseline_expected_price: float,
    start_price: float,
    current_price: float,
) -> Dict[str, Any]:
    """Return final-price forecast calibrated by empirical bid behavior.

    The calculation does not use the external auction dataset as a clothing
    price list. It uses the dataset only for the median final/start uplift by
    bid-count bucket, then transfers a limited share of that uplift into the
    fashion resale domain.
    """
    report = _load_report()
    status = _text(features.get("status"), "active")
    final_price = _number(features.get("final_price"), 0.0)
    start = max(1.0, float(start_price or 0))
    current = max(float(current_price or 0), start)
    baseline = max(float(baseline_expected_price or 0), current)
    bids_count = _number(features.get("bids_count"), 0.0)
    offers_count = _number(features.get("offers_count"), 0.0)
    views_count = _number(features.get("views_count"), 0.0)
    likes_count = _number(features.get("likes_count"), 0.0)
    favorites_count = _number(features.get("favorites_count"), 0.0)
    bidders_count = _number(features.get("bidders_count"), 0.0)
    late_activity = _clamp(_number(features.get("last_bid_time_fraction"), 0.0), 0.0, 1.0)
    category = _text(features.get("subcategory") or features.get("category"), "other")
    bucket = _bid_bucket(bids_count)
    medians = {
        **BID_BUCKET_MEDIAN_RATIOS,
        **(report.get("bid_bucket_lift_medians", {}) or {}),
    }
    median_ratio = float(medians.get(bucket, BID_BUCKET_MEDIAN_RATIOS[bucket]) or 1.0)
    next_ratio = float(medians.get(_next_bucket(bucket), median_ratio) or median_ratio)
    transfer_factor = _transfer_factor(category, report)
    uplift = _auction_uplift(median_ratio, transfer_factor, category)
    next_uplift = _auction_uplift(next_ratio, transfer_factor, category)
    current_growth = max(0.0, current / start - 1.0)
    behavior_score = _clamp(
        0.45 * min(1.0, bids_count / 10.0)
        + 0.25 * min(1.0, bidders_count / 6.0)
        + 0.15 * late_activity
        + 0.15 * min(1.0, current_growth / 0.35),
        0.0,
        1.0,
    )
    confidence = _confidence(bids_count, bidders_count, views_count, offers_count, status)

    if status == "finished" and final_price > 0:
        expected_range = {
            "conservative_final_price": _money(max(final_price, current)),
            "expected_final_price": _money(max(final_price, current)),
            "optimistic_final_price": _money(max(final_price, current)),
        }
        reason = "Лот завершён, поэтому прогноз заменён фактической финальной ценой."
        source = "finished_auction_fact"
        live_activity_detected = True
    else:
        no_observed_engagement = (
            bids_count <= 0
            and offers_count <= 0
            and views_count <= 0
            and likes_count <= 0
            and favorites_count <= 0
        )
        auction_potential = _clamp(_number(features.get("auction_potential_pre"), 0.0), 0.0, 1.0)
        attractiveness = _clamp(
            _number(features.get("auction_activity_live", features.get("auction_attractiveness")), 0.0),
            0.0,
            1.0,
        )
        confirmed_value = _clamp(_number(features.get("confirmed_value_score"), 0.0), 0.0, 1.0)
        base_price = max(1.0, _number(features.get("base_price"), baseline))
        live_activity_detected = bids_count > 0 or offers_count > 0

        if bids_count <= 0 and (status in {"draft", "prelaunch", "preview"} or no_observed_engagement):
            seller_overpriced = current > base_price * 1.12
            expected_range = _range_for_draft(
                base_price=base_price,
                current=current,
                auction_potential=auction_potential,
                confirmed_value=confirmed_value,
                baseline=baseline,
                seller_overpriced=seller_overpriced,
            )
            source = "auction_behavior_prelaunch"
            reason = (
                "До появления ставок прогноз строится осторожно: базовая resale-оценка "
                "задаёт центр диапазона, а A_pre и Q дают только умеренную премию."
            )
        elif bids_count <= 0:
            interest_pressure = _clamp(
                0.40 * min(1.0, views_count / 500.0)
                + 0.30 * min(1.0, likes_count / 50.0)
                + 0.30 * min(1.0, favorites_count / 40.0),
                0.0,
                1.0,
            )
            expected_range = _range_for_interest_only(
                base_price=base_price,
                current=current,
                interest_pressure=interest_pressure,
                attractiveness=attractiveness,
                confirmed_value=confirmed_value,
                baseline=baseline,
            )
            source = "auction_behavior_interest_only"
            reason = (
                "Просмотры и сохранения повышают прогноз слабо: это интерес, но не "
                "подтверждённая готовность платить. Сильный рост начинается только со ставок."
            )
        else:
            expected_range = _range_for_live_bids(
                current=current,
                auction_uplift=uplift,
                next_uplift=next_uplift,
                behavior_score=behavior_score,
                attractiveness=attractiveness,
                category=category,
            )
            source = "auction_bid_dataset"
            reason = (
                "При наличии ставок прогноз строится от текущей цены и медианного "
                "final/start-роста по bucket ставок из Online Auctions Dataset."
            )

    expected = expected_range["expected_final_price"]
    return {
        **expected_range,
        "expected_final_price_before_behavior": round(float(baseline_expected_price or 0), 2),
        "buyer_behavior_score": round(behavior_score, 4),
        "auction_behavior_multiplier": round(expected / current, 4) if current > 0 else 1.0,
        "bid_bucket": bucket,
        "bids_bucket": bucket,
        "bids_count": int(bids_count),
        "bidders_count": int(bidders_count),
        "late_activity": round(late_activity, 4),
        "empirical_lift": round(median_ratio, 4),
        "median_final_start_ratio": round(median_ratio, 4),
        "fashion_transfer_factor": round(transfer_factor, 4),
        "auction_uplift": round(uplift, 4),
        "transferred_lift": round(uplift, 4),
        "domain_weight": round(transfer_factor, 4),
        "pricing_confidence": confidence,
        "live_activity_detected": live_activity_detected,
        "forecast_ceiling": expected_range["optimistic_final_price"],
        "dataset_rows": int(report.get("dataset_rows", 0) or 0),
        "auction_behavior_source": ONLINE_AUCTIONS_DATASET_NAME,
        "source": source,
        "explanation": reason,
    }
