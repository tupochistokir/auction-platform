import json
import math
import sys
from typing import Any, Dict

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import (
    AUCTION_LOT_DYNAMICS_PATH,
    FINAL_CATEGORICAL_FEATURES,
    FINAL_MODEL_FEATURES,
    FINAL_NUMERIC_FEATURES,
    FINAL_PRICE_METRICS_PATH,
    FINAL_PRICE_MODEL_PATH,
    FINAL_PRICE_TARGET,
    DATASET_METADATA_PATH,
    MIN_AUCTION_ROWS_FOR_FINAL_MODEL,
    MODELS_DIR,
    RANDOM_STATE,
    REPORTS_DIR,
    TEST_SIZE,
    TRAIN_DATA_PATH,
)


def make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_pipeline(model: Any) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", make_one_hot_encoder(), FINAL_CATEGORICAL_FEATURES),
            ("numeric", StandardScaler(), FINAL_NUMERIC_FEATURES),
        ]
    )
    return Pipeline([("preprocessor", preprocessor), ("model", model)])


def calculate_metrics(y_true, y_pred) -> Dict[str, float]:
    mse = mean_squared_error(y_true, y_pred)
    return {
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "RMSE": round(float(math.sqrt(mse)), 4),
        "R2": round(float(r2_score(y_true, y_pred)), 4),
    }


def load_dataset_metadata() -> Dict[str, Any]:
    if not DATASET_METADATA_PATH.exists():
        return {"source_type": "unknown", "auction_dynamics_available": False}
    try:
        return json.loads(DATASET_METADATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"source_type": "unknown", "auction_dynamics_available": False}


def write_skip_report(dataset_metadata: Dict[str, Any], reason: str) -> Dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if FINAL_PRICE_MODEL_PATH.exists():
        FINAL_PRICE_MODEL_PATH.unlink()

    report = {
        "target": FINAL_PRICE_TARGET,
        "trained": False,
        "reason": reason,
        "dataset": dataset_metadata,
        "features": FINAL_MODEL_FEATURES,
        "fallback": "E[P_final] = P_base * (1 + 0.35A + 0.25Q)",
    }
    FINAL_PRICE_METRICS_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Final price model skipped: {reason}")
    print(f"Saved report: {FINAL_PRICE_METRICS_PATH}")
    return report


def load_auction_training_rows(base_dataset: pd.DataFrame) -> pd.DataFrame:
    """Load real auction rows from platform train.csv and external bid dynamics."""
    required_columns = FINAL_MODEL_FEATURES + [FINAL_PRICE_TARGET]
    chunks = []

    if "is_auction_data" in base_dataset.columns:
        mask = base_dataset["is_auction_data"].astype(str).str.lower() == "true"
        platform_auction_rows = base_dataset.loc[mask].copy()
        if not platform_auction_rows.empty:
            missing = [
                column
                for column in required_columns
                if column not in platform_auction_rows.columns
            ]
            if not missing:
                chunks.append(platform_auction_rows[required_columns])

    if AUCTION_LOT_DYNAMICS_PATH.exists():
        external_auction_rows = pd.read_csv(AUCTION_LOT_DYNAMICS_PATH)
        missing = [
            column
            for column in required_columns
            if column not in external_auction_rows.columns
        ]
        if missing:
            raise ValueError(
                "Cannot use auction lot dynamics. Missing columns: "
                + ", ".join(missing)
            )
        chunks.append(external_auction_rows[required_columns])

    if not chunks:
        return pd.DataFrame(columns=required_columns)

    return pd.concat(chunks, ignore_index=True)


def train() -> Dict[str, Any]:
    if not TRAIN_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {TRAIN_DATA_PATH}. Run python ml/prepare_dataset.py"
        )

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    dataset = pd.read_csv(TRAIN_DATA_PATH)
    dataset_metadata = load_dataset_metadata()
    print(f"Loaded rows: {len(dataset)}")

    auction_dataset = load_auction_training_rows(dataset)
    if len(auction_dataset) < MIN_AUCTION_ROWS_FOR_FINAL_MODEL:
        return write_skip_report(
            dataset_metadata,
            f"Only {len(auction_dataset)} real auction rows found; at least "
            f"{MIN_AUCTION_ROWS_FOR_FINAL_MODEL} are required.",
        )

    dataset = auction_dataset.copy()
    print(f"Using auction rows: {len(dataset)}")
    dataset = dataset.dropna(subset=FINAL_MODEL_FEATURES + [FINAL_PRICE_TARGET])
    dataset = dataset[dataset[FINAL_PRICE_TARGET] > 0]
    dataset = dataset[dataset["start_price"] > 0]
    if len(dataset) < MIN_AUCTION_ROWS_FOR_FINAL_MODEL:
        return write_skip_report(
            dataset_metadata,
            f"Only {len(dataset)} clean auction rows found after preprocessing; at least "
            f"{MIN_AUCTION_ROWS_FOR_FINAL_MODEL} are required.",
        )

    dataset["has_tag"] = dataset["has_tag"].astype(str).str.lower()
    X = dataset[FINAL_MODEL_FEATURES]
    y = dataset[FINAL_PRICE_TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )

    candidates = {
        "linear_regression": build_pipeline(LinearRegression()),
        "random_forest": build_pipeline(
            RandomForestRegressor(
                n_estimators=240,
                max_depth=10,
                min_samples_leaf=2,
                random_state=RANDOM_STATE,
            )
        ),
    }

    metrics: Dict[str, Dict[str, float]] = {}
    trained_models: Dict[str, Pipeline] = {}

    for name, pipeline in candidates.items():
        print(f"Training model: {name}")
        pipeline.fit(X_train, y_train)
        predictions = pipeline.predict(X_test)
        metrics[name] = calculate_metrics(y_test, predictions)
        trained_models[name] = pipeline
        print(f"Metrics {name}: {metrics[name]}")

    best_model_name = min(
        metrics,
        key=lambda model_name: (metrics[model_name]["MAE"], -metrics[model_name]["R2"]),
    )
    print(f"Best model: {best_model_name}")

    joblib.dump(trained_models[best_model_name], FINAL_PRICE_MODEL_PATH)
    print(f"Saved model: {FINAL_PRICE_MODEL_PATH}")

    report = {
        "target": FINAL_PRICE_TARGET,
        "trained": True,
        "best_model": best_model_name,
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "dataset": {
            **dataset_metadata,
            "auction_rows_source": (
                str(AUCTION_LOT_DYNAMICS_PATH)
                if AUCTION_LOT_DYNAMICS_PATH.exists()
                else "data/processed/train.csv"
            ),
            "auction_rows_used": int(len(dataset)),
        },
        "features": FINAL_MODEL_FEATURES,
        "metrics": metrics,
    }
    FINAL_PRICE_METRICS_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved metrics: {FINAL_PRICE_METRICS_PATH}")
    return report


if __name__ == "__main__":
    try:
        result = train()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
