import csv
import json
from pathlib import Path

from config import DATASET_METADATA_PATH, RAW_DATA_PATH, TRAIN_DATA_PATH
from mercari_adapter import has_mercari_source, has_mercari_test_only, prepare_mercari_dataset


REQUIRED_COLUMNS = [
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
]


def _is_fully_new_row(row: dict) -> bool:
    condition = str(row.get("condition", "")).strip().lower()
    item_condition_id = str(row.get("item_condition_id", "")).strip()
    new_conditions = {
        "new",
        "new_with_tags",
        "new with tags",
        "brand new",
        "fully new",
        "unused",
    }
    return item_condition_id == "1" or condition in new_conditions


def validate_csv(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Raw dataset not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        rows = list(reader)
        if len(rows) < 120:
            raise ValueError("Dataset must contain at least 120 rows")


def prepare_dataset() -> Path:
    if has_mercari_source():
        return prepare_mercari_dataset()

    if has_mercari_test_only():
        raise FileNotFoundError(
            "Found data/external/mercari/test.tsv, but Mercari test.tsv has no price column. "
            "Download and place train.tsv or train.tsv.zip into data/external/mercari."
        )

    validate_csv(RAW_DATA_PATH)
    TRAIN_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RAW_DATA_PATH.open("r", encoding="utf-8", newline="") as input_file:
        reader = csv.DictReader(input_file)
        fieldnames = reader.fieldnames or REQUIRED_COLUMNS
        raw_rows = list(reader)

    filtered_rows = [row for row in raw_rows if not _is_fully_new_row(row)]
    removed_new_items_count = len(raw_rows) - len(filtered_rows)

    with TRAIN_DATA_PATH.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_rows)

    rows_count = len(filtered_rows)
    DATASET_METADATA_PATH.write_text(
        json.dumps(
            {
                "source_type": "synthetic_demo_dataset",
                "dataset_name": "Local synthetic clothes dataset",
                "source_file": str(RAW_DATA_PATH),
                "processed_path": str(TRAIN_DATA_PATH),
                "rows_before_filtering": len(raw_rows),
                "rows_after_filtering": rows_count,
                "removed_new_items_count": removed_new_items_count,
                "filtering_note": (
                    "Fully new / new-with-tags rows are excluded from the resale "
                    "training dataset so the base-price model is not biased by "
                    "unused retail items."
                ),
                "processed_rows": rows_count,
                "currency": "RUB",
                "auction_dynamics_available": True,
                "is_synthetic": True,
                "notes": [
                    "This dataset is only a development fallback.",
                    "For diploma-grade market grounding use Mercari data in data/external/mercari.",
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return TRAIN_DATA_PATH


if __name__ == "__main__":
    output_path = prepare_dataset()
    print(f"Prepared dataset: {output_path}")
