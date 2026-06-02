import csv
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pandas as pd

from config import (
    DATASET_METADATA_PATH,
    MERCARI_TEST_TSV_PATH,
    MERCARI_TRAIN_TSV_PATH,
    MERCARI_TRAIN_ZIP_PATH,
    TRAIN_DATA_PATH,
    USD_TO_RUB,
)


OUTPUT_COLUMNS = [
    "id",
    "brand",
    "category",
    "condition",
    "age",
    "material",
    "size",
    "color",
    "has_tag",
    "views_count",
    "likes_count",
    "favorites_count",
    "bids_count",
    "start_price",
    "final_price",
    "price",
    "is_auction_data",
    "source_dataset",
]

SIZE_PATTERN = re.compile(r"\b(XXS|XS|S|M|L|XL|XXL|XXXL|2XL|3XL|4XL)\b", re.IGNORECASE)

MATERIAL_KEYWORDS = {
    "leather": ("leather", "genuine leather", "suede"),
    "denim": ("denim", "jean", "jeans"),
    "wool": ("wool", "cashmere", "merino"),
    "cotton": ("cotton",),
    "nylon": ("nylon",),
    "polyester": ("polyester",),
}

COLOR_KEYWORDS = (
    "black",
    "white",
    "blue",
    "navy",
    "red",
    "green",
    "brown",
    "beige",
    "gray",
    "grey",
    "pink",
    "yellow",
    "purple",
    "orange",
)


def has_mercari_source() -> bool:
    """Return True when the user placed the Mercari file into data/external."""
    return MERCARI_TRAIN_TSV_PATH.exists() or MERCARI_TRAIN_ZIP_PATH.exists()


def has_mercari_test_only() -> bool:
    """Return True when only Kaggle test data is present.

    The competition test file has no price column, so it cannot train the model.
    """
    return MERCARI_TEST_TSV_PATH.exists() and not has_mercari_source()


def _text(value: Any, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value).strip()


def _lower_blob(*values: Any) -> str:
    return " ".join(_text(value).lower() for value in values if _text(value))


def _condition(item_condition_id: Any) -> str:
    try:
        value = int(float(item_condition_id))
    except (TypeError, ValueError):
        return "normal"

    mapping = {
        1: "excellent",  # new
        2: "excellent",  # like new
        3: "good",
        4: "normal",
        5: "bad",
    }
    return mapping.get(value, "normal")


def _category(category_name: str, name: str, description: str) -> Optional[str]:
    blob = _lower_blob(category_name, name, description)
    category = _text(category_name).lower()

    if not category and not blob:
        return None

    clothing_context = (
        "women",
        "men",
        "kids",
        "apparel",
        "shoes",
        "bags",
        "handbag",
        "jacket",
        "shirt",
        "jeans",
        "hoodie",
        "sneaker",
        "coat",
        "dress",
        "skirt",
        "hat",
        "cap",
    )
    if not any(word in category or word in blob for word in clothing_context):
        return None

    if any(word in blob for word in ("bomber", "varsity jacket")):
        return "bomber"
    if any(word in blob for word in ("coat", "trench", "parka")):
        return "coat"
    if any(word in blob for word in ("jacket", "outerwear", "windbreaker")):
        return "jacket"
    if any(word in blob for word in ("hoodie", "sweatshirt", "sweater")):
        return "hoodie"
    if "jeans" in blob or "denim pants" in blob:
        return "jeans"
    if any(word in blob for word in ("sneaker", "shoes", "shoe", "boots")):
        return "sneakers"
    if any(word in blob for word in ("tshirt", "t-shirt", "tee shirt", "tee")):
        return "tshirt"
    if any(word in blob for word in ("shirt", "blouse", "top")):
        return "shirt"
    if any(word in blob for word in ("bag", "purse", "handbag", "backpack")):
        return "bag"
    if any(word in blob for word in ("cap", "hat", "beanie")):
        return "cap"

    return "other"


def _material(name: str, description: str, category_name: str) -> str:
    blob = _lower_blob(name, description, category_name)
    for material, keywords in MATERIAL_KEYWORDS.items():
        if any(keyword in blob for keyword in keywords):
            return material
    return "mixed"


def _size(name: str, description: str) -> str:
    blob = _lower_blob(name, description)
    match = SIZE_PATTERN.search(blob.upper())
    return match.group(1).upper() if match else "OS"


def _color(name: str, description: str) -> str:
    blob = _lower_blob(name, description)
    for color in COLOR_KEYWORDS:
        if color in blob:
            return "gray" if color == "grey" else color
    return "unknown"


def _has_tag(item_condition_id: Any, name: str, description: str) -> bool:
    blob = _lower_blob(name, description)
    if "new without tags" in blob or "nwot" in blob:
        return False
    tag_signals = ("new with tags", "nwt", "tags attached", "with tag")
    return any(signal in blob for signal in tag_signals) or str(item_condition_id) == "1"


def _is_fully_new_item(row: Dict[str, Any]) -> bool:
    """Detect items that should not train the resale base-price model."""
    condition_id = str(row.get("item_condition_id", "")).strip()
    blob = _lower_blob(row.get("name"), row.get("item_description"))
    new_signals = (
        "new with tags",
        "nwt",
        "brand new",
        "never worn",
        "tags attached",
    )
    return condition_id == "1" or any(signal in blob for signal in new_signals)


def _open_mercari_zip() -> Iterable[pd.DataFrame]:
    with zipfile.ZipFile(MERCARI_TRAIN_ZIP_PATH) as archive:
        candidates = [name for name in archive.namelist() if name.lower().endswith(".tsv")]
        if not candidates:
            raise FileNotFoundError("train.tsv was not found inside train.tsv.zip")
        with archive.open(candidates[0]) as file:
            yield from pd.read_csv(file, sep="\t", chunksize=50000)


def _read_mercari_chunks() -> Iterable[pd.DataFrame]:
    if MERCARI_TRAIN_TSV_PATH.exists():
        yield from pd.read_csv(MERCARI_TRAIN_TSV_PATH, sep="\t", chunksize=50000)
        return

    if MERCARI_TRAIN_ZIP_PATH.exists():
        yield from _open_mercari_zip()
        return

    raise FileNotFoundError(
        "Mercari source file is missing. Put train.tsv or train.tsv.zip into "
        f"{MERCARI_TRAIN_TSV_PATH.parent}"
    )


def _convert_row(row: Dict[str, Any], row_id: int) -> Optional[Dict[str, Any]]:
    price_usd = pd.to_numeric(row.get("price"), errors="coerce")
    if pd.isna(price_usd) or float(price_usd) <= 0 or float(price_usd) > 500:
        return None

    name = _text(row.get("name"))
    category_name = _text(row.get("category_name"))
    description = _text(row.get("item_description"))
    category = _category(category_name, name, description)
    if category is None:
        return None

    price_rub = round(float(price_usd) * USD_TO_RUB, 2)
    condition = _condition(row.get("item_condition_id"))
    brand = _text(row.get("brand_name"), "unknown").lower() or "unknown"

    return {
        "id": row_id,
        "brand": brand,
        "category": category,
        "condition": condition,
        "age": 0,
        "material": _material(name, description, category_name),
        "size": _size(name, description),
        "color": _color(name, description),
        "has_tag": str(_has_tag(row.get("item_condition_id"), name, description)).lower(),
        "views_count": 0,
        "likes_count": 0,
        "favorites_count": 0,
        "bids_count": 0,
        "start_price": price_rub,
        "final_price": price_rub,
        "price": price_rub,
        "is_auction_data": "false",
        "source_dataset": "mercari_price_suggestion",
    }


def prepare_mercari_dataset(max_rows: Optional[int] = None) -> Path:
    """
    Convert Mercari marketplace data into the platform training schema.

    Mercari has sale prices, brand, category, condition, title and description.
    It does not have auction bid history, so the output is valid for the base
    market price model, not for the final auction closing price model.
    """
    TRAIN_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATASET_METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    source_rows = 0
    removed_new_items = 0
    category_counts: Dict[str, int] = {}

    with TRAIN_DATA_PATH.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        for chunk in _read_mercari_chunks():
            source_rows += len(chunk)
            for row in chunk.to_dict("records"):
                if _is_fully_new_item(row):
                    removed_new_items += 1
                    continue
                converted = _convert_row(row, written + 1)
                if converted is None:
                    continue

                writer.writerow(converted)
                category_counts[converted["category"]] = (
                    category_counts.get(converted["category"], 0) + 1
                )
                written += 1

                if max_rows is not None and written >= max_rows:
                    break
            if max_rows is not None and written >= max_rows:
                break

    if written < 1000:
        raise ValueError(
            f"Mercari import produced only {written} usable rows. Check the source file."
        )

    metadata = {
        "source_type": "real_marketplace_dataset",
        "dataset_name": "Mercari Price Suggestion Challenge",
        "source_file": str(
            MERCARI_TRAIN_TSV_PATH if MERCARI_TRAIN_TSV_PATH.exists() else MERCARI_TRAIN_ZIP_PATH
        ),
        "processed_path": str(TRAIN_DATA_PATH),
        "raw_rows_scanned": source_rows,
        "rows_before_filtering": source_rows,
        "rows_after_filtering": written,
        "removed_new_items_count": removed_new_items,
        "filtering_note": (
            "Fully new / new-with-tags Mercari items are excluded from the base "
            "resale training dataset. The model is trained on used resale items; "
            "has_tag remains a seller-side feature for original store tag evidence."
        ),
        "processed_rows": written,
        "currency": "RUB",
        "original_currency": "USD",
        "usd_to_rub": USD_TO_RUB,
        "auction_dynamics_available": False,
        "is_synthetic": False,
        "category_counts": dict(sorted(category_counts.items())),
        "notes": [
            "Mercari contains marketplace sale prices, not auction bid history.",
            "Age is unavailable in the source and is stored as 0.",
            "Views, likes, favorites and bids are unavailable and are stored as 0.",
        ],
    }
    DATASET_METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return TRAIN_DATA_PATH
