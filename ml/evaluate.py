import json
from datetime import datetime, timezone
from typing import Any, Dict

import pandas as pd

from config import (
    AUCTION_BEHAVIOR_MODEL_PATH,
    AUCTION_BID_DATASET_SUMMARY_PATH,
    BASE_PRICE_METRICS_PATH,
    DATASET_METADATA_PATH,
    FINAL_PRICE_METRICS_PATH,
    REPORTS_DIR,
    TRAIN_DATA_PATH,
)

DATASET_SUMMARY_PATH = REPORTS_DIR / "dataset_summary.json"
ML_SUMMARY_PATH = REPORTS_DIR / "ml_summary.json"


def load_report(path) -> Dict[str, Any]:
    """Load a JSON report if it exists."""
    if not path.exists():
        return {"available": False, "error": f"Report not found: {path}"}
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        report["available"] = True
        return report
    except json.JSONDecodeError as exc:
        return {"available": False, "error": f"Invalid JSON in {path}: {exc}"}


def numeric_summary(series: pd.Series) -> Dict[str, Any]:
    """Return compact descriptive statistics for a numeric target."""
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if numeric.empty:
        return {"available": False}

    return {
        "available": True,
        "count": int(numeric.count()),
        "mean": round(float(numeric.mean()), 2),
        "median": round(float(numeric.median()), 2),
        "min": round(float(numeric.min()), 2),
        "max": round(float(numeric.max()), 2),
        "std": round(float(numeric.std(ddof=0)), 2),
        "p25": round(float(numeric.quantile(0.25)), 2),
        "p75": round(float(numeric.quantile(0.75)), 2),
    }


def make_dataset_summary() -> Dict[str, Any]:
    """Build and save a dataset report for the diploma data section."""
    if not TRAIN_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {TRAIN_DATA_PATH}. Run python ml/prepare_dataset.py"
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(TRAIN_DATA_PATH)
    metadata = load_report(DATASET_METADATA_PATH)

    summary = {
        "dataset_path": str(TRAIN_DATA_PATH),
        "rows": int(dataset.shape[0]),
        "columns": int(dataset.shape[1]),
        "features": dataset.columns.tolist(),
        "metadata": metadata,
        "rows_before_filtering": metadata.get("rows_before_filtering"),
        "rows_after_filtering": metadata.get("rows_after_filtering"),
        "removed_new_items_count": metadata.get("removed_new_items_count"),
        "filtering_note": metadata.get("filtering_note"),
        "price": numeric_summary(dataset["price"]) if "price" in dataset else {"available": False},
        "final_price": (
            numeric_summary(dataset["final_price"])
            if "final_price" in dataset
            else {"available": False}
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    DATASET_SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def make_ml_summary(dataset_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Combine dataset and model metrics into one report."""
    summary = {
        "dataset_rows": dataset_summary["rows"],
        "dataset_columns": dataset_summary["columns"],
        "auction_bid_dataset": load_report(AUCTION_BID_DATASET_SUMMARY_PATH),
        "auction_behavior_model": load_report(AUCTION_BEHAVIOR_MODEL_PATH),
        "base_price_model_metrics": load_report(BASE_PRICE_METRICS_PATH),
        "final_price_model_metrics": load_report(FINAL_PRICE_METRICS_PATH),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    ML_SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def evaluate() -> Dict[str, Any]:
    dataset_summary = make_dataset_summary()
    ml_summary = make_ml_summary(dataset_summary)
    return {
        "dataset_summary": dataset_summary,
        "ml_summary": ml_summary,
        "saved_files": {
            "dataset_summary": str(DATASET_SUMMARY_PATH),
            "ml_summary": str(ML_SUMMARY_PATH),
        },
    }


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
