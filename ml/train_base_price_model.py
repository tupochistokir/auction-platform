import json
import math
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import (
    BASE_CATEGORICAL_FEATURES,
    BASE_MODEL_FEATURES,
    BASE_NUMERIC_FEATURES,
    BASE_PRICE_FEATURES_PATH,
    BASE_PRICE_METRICS_PATH,
    BASE_PRICE_MODEL_PATH,
    BASE_PRICE_TARGET,
    DATASET_METADATA_PATH,
    MAX_METRIC_ROWS,
    MAX_RANDOM_FOREST_TRAIN_ROWS,
    MODELS_DIR,
    RANDOM_STATE,
    REPORTS_DIR,
    TEST_SIZE,
    TRAIN_DATA_PATH,
)


def make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=True)


def build_pipeline(model: Any) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("categorical", make_one_hot_encoder(), BASE_CATEGORICAL_FEATURES),
            ("numeric", StandardScaler(), BASE_NUMERIC_FEATURES),
        ]
    )
    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )


def with_log_target(model: Any) -> TransformedTargetRegressor:
    return TransformedTargetRegressor(
        regressor=build_pipeline(model),
        func=np.log1p,
        inverse_func=np.expm1,
    )


def calculate_metrics(y_true, y_pred) -> Dict[str, float]:
    mse = mean_squared_error(y_true, y_pred)
    return {
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "RMSE": round(float(math.sqrt(mse)), 4),
        "R2": round(float(r2_score(y_true, y_pred)), 4),
    }


def get_feature_report(pipeline: Pipeline) -> Dict[str, Any]:
    if hasattr(pipeline, "regressor_"):
        pipeline = pipeline.regressor_

    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]

    try:
        transformed_features = preprocessor.get_feature_names_out().tolist()
    except AttributeError:
        transformed_features = BASE_MODEL_FEATURES

    report: Dict[str, Any] = {
        "input_features": BASE_MODEL_FEATURES,
        "categorical_features": BASE_CATEGORICAL_FEATURES,
        "numeric_features": BASE_NUMERIC_FEATURES,
        "transformed_features": transformed_features,
    }

    if hasattr(model, "feature_importances_"):
        importances = [
            {
                "feature": feature,
                "importance": round(float(importance), 6),
            }
            for feature, importance in zip(transformed_features, model.feature_importances_)
        ]
        report["feature_importances"] = sorted(
            importances,
            key=lambda item: item["importance"],
            reverse=True,
        )

    return report


def load_dataset_metadata() -> Dict[str, Any]:
    if not DATASET_METADATA_PATH.exists():
        return {"source_type": "unknown", "is_synthetic": None}
    try:
        return json.loads(DATASET_METADATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"source_type": "unknown", "is_synthetic": None}


def train() -> Dict[str, Any]:
    if not TRAIN_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {TRAIN_DATA_PATH}. Run python ml/prepare_dataset.py"
        )

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    dataset = pd.read_csv(TRAIN_DATA_PATH)
    dataset_metadata = load_dataset_metadata()
    missing_columns = [
        column
        for column in BASE_MODEL_FEATURES + [BASE_PRICE_TARGET]
        if column not in dataset.columns
    ]
    if missing_columns:
        raise ValueError(f"Missing columns in train.csv: {', '.join(missing_columns)}")

    dataset["has_tag"] = dataset["has_tag"].astype(str).str.lower()
    dataset[BASE_PRICE_TARGET] = pd.to_numeric(dataset[BASE_PRICE_TARGET], errors="coerce")
    dataset = dataset[dataset[BASE_PRICE_TARGET].notna() & (dataset[BASE_PRICE_TARGET] > 0)]
    X = dataset[BASE_MODEL_FEATURES]
    y = dataset[BASE_PRICE_TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
    )

    candidates = {
        "linear_regression_log_target": with_log_target(LinearRegression()),
        "random_forest_log_target": with_log_target(
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

    X_metric = X_test
    y_metric = y_test
    if len(X_metric) > MAX_METRIC_ROWS:
        X_metric = X_metric.sample(n=MAX_METRIC_ROWS, random_state=RANDOM_STATE)
        y_metric = y_test.loc[X_metric.index]

    for name, pipeline in candidates.items():
        X_fit = X_train
        y_fit = y_train
        if name.startswith("random_forest") and len(X_fit) > MAX_RANDOM_FOREST_TRAIN_ROWS:
            X_fit = X_fit.sample(n=MAX_RANDOM_FOREST_TRAIN_ROWS, random_state=RANDOM_STATE)
            y_fit = y_train.loc[X_fit.index]

        pipeline.fit(X_fit, y_fit)
        predictions = pipeline.predict(X_metric)
        metrics[name] = calculate_metrics(y_metric, predictions)
        trained_models[name] = pipeline

    best_model_name = min(
        metrics,
        key=lambda model_name: (metrics[model_name]["MAE"], -metrics[model_name]["R2"]),
    )
    best_model = trained_models[best_model_name]

    joblib.dump(best_model, BASE_PRICE_MODEL_PATH)

    metrics_report = {
        "target": BASE_PRICE_TARGET,
        "best_model": best_model_name,
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "metric_rows": int(len(X_metric)),
        "dataset": dataset_metadata,
        "target_transform": "log1p/expm1",
        "random_forest_train_cap": MAX_RANDOM_FOREST_TRAIN_ROWS,
        "metrics": metrics,
    }

    BASE_PRICE_METRICS_PATH.write_text(
        json.dumps(metrics_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    BASE_PRICE_FEATURES_PATH.write_text(
        json.dumps(get_feature_report(best_model), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return metrics_report


if __name__ == "__main__":
    result = train()
    print(json.dumps(result, ensure_ascii=False, indent=2))
