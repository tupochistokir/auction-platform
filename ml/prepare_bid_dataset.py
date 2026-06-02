import json
import re
from datetime import datetime, timezone
from typing import Dict

import pandas as pd

from config import (
    AUCTION_BID_DATASET_SUMMARY_PATH,
    AUCTION_BID_HISTORY_PATH,
    AUCTION_LOT_DYNAMICS_PATH,
    ONLINE_AUCTIONS_CSV_PATH,
    REPORTS_DIR,
    USD_TO_RUB,
)


ITEM_METADATA: Dict[str, Dict[str, str]] = {
    "cartier wristwatch": {
        "brand": "cartier",
        "category": "accessories",
        "condition": "good",
        "material": "mixed",
        "size": "OS",
        "has_tag": "false",
    },
    "palm pilot m515 pda": {
        "brand": "palm",
        "category": "other",
        "condition": "normal",
        "material": "mixed",
        "size": "OS",
        "has_tag": "false",
    },
    "xbox game console": {
        "brand": "microsoft",
        "category": "other",
        "condition": "good",
        "material": "mixed",
        "size": "OS",
        "has_tag": "false",
    },
}


def auction_duration_days(value: str) -> float:
    """Extract auction duration from labels such as '3 day auction'."""
    match = re.search(r"(\d+(?:\.\d+)?)", str(value or ""))
    if not match:
        return 7.0
    return max(1.0, float(match.group(1)))


def item_metadata(item: str) -> Dict[str, str]:
    return ITEM_METADATA.get(
        str(item or "").strip().lower(),
        {
            "brand": "unknown",
            "category": "other",
            "condition": "normal",
            "material": "mixed",
            "size": "OS",
            "has_tag": "false",
        },
    )


def prepare_bid_dataset() -> Dict[str, object]:
    """Prepare bid-level and auction-level datasets from Online Auctions data."""
    if not ONLINE_AUCTIONS_CSV_PATH.exists():
        raise FileNotFoundError(
            f"Online auctions dataset not found: {ONLINE_AUCTIONS_CSV_PATH}"
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    AUCTION_BID_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    source = pd.read_csv(ONLINE_AUCTIONS_CSV_PATH)
    required = {
        "auctionid",
        "bid",
        "bidtime",
        "bidder",
        "bidderrate",
        "openbid",
        "price",
        "item",
        "auction_type",
    }
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError(f"Missing columns in auction.csv: {', '.join(missing)}")

    data = source.copy()
    data["bid"] = pd.to_numeric(data["bid"], errors="coerce")
    data["bidtime"] = pd.to_numeric(data["bidtime"], errors="coerce")
    data["bidderrate"] = pd.to_numeric(data["bidderrate"], errors="coerce").fillna(0)
    data["openbid"] = pd.to_numeric(data["openbid"], errors="coerce")
    data["price"] = pd.to_numeric(data["price"], errors="coerce")
    data = data.dropna(subset=["auctionid", "bid", "bidtime", "openbid", "price"])
    data = data[(data["bid"] > 0) & (data["openbid"] > 0) & (data["price"] > 0)]

    data["auction_duration_days"] = data["auction_type"].map(auction_duration_days)
    data = data.sort_values(["auctionid", "bidtime", "bid"]).reset_index(drop=True)
    data["bid_index"] = data.groupby("auctionid").cumcount() + 1
    data["time_fraction"] = (data["bidtime"] / data["auction_duration_days"]).clip(0, 1)
    data["bid_amount_rub"] = (data["bid"] * USD_TO_RUB).round(2)
    data["start_price_rub"] = (data["openbid"] * USD_TO_RUB).round(2)
    data["final_price_rub"] = (data["price"] * USD_TO_RUB).round(2)
    data["price_growth_from_start"] = (
        (data["bid"] - data["openbid"]) / data["openbid"]
    ).round(4)
    data["price_to_final_ratio"] = (data["bid"] / data["price"]).round(4)

    bid_history = data[
        [
            "auctionid",
            "bid_index",
            "bidder",
            "bidderrate",
            "bidtime",
            "auction_duration_days",
            "time_fraction",
            "bid",
            "bid_amount_rub",
            "openbid",
            "start_price_rub",
            "price",
            "final_price_rub",
            "price_growth_from_start",
            "price_to_final_ratio",
            "item",
            "auction_type",
        ]
    ].rename(
        columns={
            "auctionid": "external_auction_id",
            "bidtime": "bid_time_days",
            "bid": "bid_amount_original",
            "openbid": "start_price_original",
            "price": "final_price_original",
        }
    )
    bid_history.to_csv(AUCTION_BID_HISTORY_PATH, index=False)

    grouped = data.groupby("auctionid")
    lots = grouped.agg(
        item=("item", "first"),
        auction_type=("auction_type", "first"),
        auction_duration_days=("auction_duration_days", "first"),
        start_price=("start_price_rub", "first"),
        final_price=("final_price_rub", "first"),
        bids_count=("bid", "count"),
        bidders_count=("bidder", "nunique"),
        max_bidder_rating=("bidderrate", "max"),
        mean_bidder_rating=("bidderrate", "mean"),
        first_bid_time_fraction=("time_fraction", "min"),
        last_bid_time_fraction=("time_fraction", "max"),
        median_bid_time_fraction=("time_fraction", "median"),
        price_growth=("price_growth_from_start", "max"),
    ).reset_index()

    lots["price"] = lots["start_price"]
    lots["views_count"] = 0
    lots["likes_count"] = 0
    lots["favorites_count"] = 0
    lots["age"] = 0
    lots["source_dataset"] = "online_auctions"
    lots["is_auction_data"] = True

    metadata = lots["item"].map(item_metadata)
    lots["brand"] = metadata.map(lambda item: item["brand"])
    lots["category"] = metadata.map(lambda item: item["category"])
    lots["condition"] = metadata.map(lambda item: item["condition"])
    lots["material"] = metadata.map(lambda item: item["material"])
    lots["size"] = metadata.map(lambda item: item["size"])
    lots["has_tag"] = metadata.map(lambda item: item["has_tag"])

    lot_columns = [
        "auctionid",
        "brand",
        "category",
        "condition",
        "age",
        "material",
        "size",
        "has_tag",
        "views_count",
        "likes_count",
        "favorites_count",
        "bids_count",
        "bidders_count",
        "start_price",
        "price",
        "final_price",
        "item",
        "auction_type",
        "auction_duration_days",
        "first_bid_time_fraction",
        "last_bid_time_fraction",
        "median_bid_time_fraction",
        "price_growth",
        "source_dataset",
        "is_auction_data",
    ]
    lots[lot_columns].rename(columns={"auctionid": "external_auction_id"}).to_csv(
        AUCTION_LOT_DYNAMICS_PATH,
        index=False,
    )

    summary = {
        "dataset_name": "Online Auctions Dataset",
        "source_path": str(ONLINE_AUCTIONS_CSV_PATH),
        "bid_rows": int(len(bid_history)),
        "auction_rows": int(len(lots)),
        "items": lots["item"].value_counts().to_dict(),
        "currency": "RUB",
        "original_currency": "USD",
        "usd_to_rub": USD_TO_RUB,
        "outputs": {
            "bid_history": str(AUCTION_BID_HISTORY_PATH),
            "lot_dynamics": str(AUCTION_LOT_DYNAMICS_PATH),
        },
        "usage": (
            "Bid-level rows support auction graphs and anti-sniping analysis; "
            "auction-level rows train the final price model."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    AUCTION_BID_DATASET_SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


if __name__ == "__main__":
    print(json.dumps(prepare_bid_dataset(), ensure_ascii=False, indent=2))
