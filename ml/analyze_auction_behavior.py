import json
from datetime import datetime, timezone

import pandas as pd

from config import (
    AUCTION_BEHAVIOR_MODEL_PATH,
    AUCTION_LOT_DYNAMICS_PATH,
    REPORTS_DIR,
)


MIN_START_PRICE_RUB = 300.0
BID_BUCKETS = [
    (0, 0, "0"),
    (1, 1, "1"),
    (2, 3, "2-3"),
    (4, 6, "4-6"),
    (7, 12, "7-12"),
    (13, 10**9, "13+"),
]


def _bucket_for_bids(count: float) -> str:
    count = int(count or 0)
    for left, right, label in BID_BUCKETS:
        if left <= count <= right:
            return label
    return "13+"


def analyze_auction_behavior() -> dict:
    """Extract robust buyer-behavior statistics from the auction bid dataset."""
    if not AUCTION_LOT_DYNAMICS_PATH.exists():
        raise FileNotFoundError(
            f"Auction lot dynamics dataset not found: {AUCTION_LOT_DYNAMICS_PATH}"
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(AUCTION_LOT_DYNAMICS_PATH)
    required_columns = [
        "start_price",
        "final_price",
        "bids_count",
        "bidders_count",
        "last_bid_time_fraction",
    ]
    missing = sorted(set(required_columns) - set(data.columns))
    if missing:
        raise ValueError(f"Missing columns for auction behavior analysis: {missing}")

    data = data.copy()
    for column in required_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0)

    raw_rows = int(len(data))
    data = data[
        (data["start_price"] >= MIN_START_PRICE_RUB)
        & (data["final_price"] > 0)
    ].copy()
    if len(data) < 10:
        raise ValueError("Not enough auction rows to analyze buyer behavior")

    data["final_to_start_ratio"] = data["final_price"] / data["start_price"]
    data["bid_bucket"] = data["bids_count"].map(_bucket_for_bids)
    bucket_stats = (
        data.groupby("bid_bucket", observed=True)["final_to_start_ratio"]
        .agg(["count", "median"])
        .reindex([bucket[2] for bucket in BID_BUCKETS])
        .fillna({"count": 0, "median": 1.0})
    )
    bucket_medians = {
        str(index): round(float(row["median"]), 4)
        for index, row in bucket_stats.iterrows()
    }
    bucket_counts = {
        str(index): int(row["count"])
        for index, row in bucket_stats.iterrows()
    }

    quantiles = {
        "final_to_start_p10": float(data["final_to_start_ratio"].quantile(0.10)),
        "final_to_start_p25": float(data["final_to_start_ratio"].quantile(0.25)),
        "final_to_start_p50": float(data["final_to_start_ratio"].quantile(0.50)),
        "final_to_start_p75": float(data["final_to_start_ratio"].quantile(0.75)),
        "final_to_start_p90": float(data["final_to_start_ratio"].quantile(0.90)),
        "bids_count_p50": float(data["bids_count"].quantile(0.50)),
        "bids_count_p90": float(data["bids_count"].quantile(0.90)),
        "bidders_count_p50": float(data["bidders_count"].quantile(0.50)),
        "bidders_count_p90": float(data["bidders_count"].quantile(0.90)),
        "last_bid_time_fraction_p50": float(data["last_bid_time_fraction"].quantile(0.50)),
    }

    result = {
        "dataset_name": "Online Auctions buyer behavior dataset",
        "raw_rows": raw_rows,
        "dataset_rows": int(len(data)),
        "filter": {
            "min_start_price_rub": MIN_START_PRICE_RUB,
            "reason": (
                "Rows with near-zero opening bids are excluded from percentage "
                "uplift estimation because they create non-representative ratios."
            ),
        },
        "target": "final_price / start_price",
        "features": [
            "bids_count",
            "bidders_count",
            "last_bid_time_fraction",
            "current_price / start_price",
        ],
        "quantiles": {key: round(value, 6) for key, value in quantiles.items()},
        "bid_bucket_lift_medians": bucket_medians,
        "bid_bucket_counts": bucket_counts,
        "domain_transfer": {
            "matched_categories": ["accessories", "other"],
            "matched_category_weight": 0.70,
            "clothing_category_weight": 0.35,
            "reason": (
                "The dataset contains PDA, game console and wristwatch auctions. "
                "For clothing it is used as buyer-behavior evidence, not as a "
                "direct clothing price model."
            ),
        },
        "interpretation": (
            "The platform uses robust median final/start ratios by bid-count bucket. "
            "This keeps the forecast tied to actual buyer behavior while avoiding "
            "mean-based distortion from near-zero opening bids."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    AUCTION_BEHAVIOR_MODEL_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


if __name__ == "__main__":
    print(json.dumps(analyze_auction_behavior(), ensure_ascii=False, indent=2))
