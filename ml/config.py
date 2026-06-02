from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "clothes_dataset.csv"
EXTERNAL_DATA_DIR = DATA_DIR / "external"
MERCARI_DATA_DIR = EXTERNAL_DATA_DIR / "mercari"
MERCARI_TRAIN_TSV_PATH = MERCARI_DATA_DIR / "train.tsv"
MERCARI_TRAIN_ZIP_PATH = MERCARI_DATA_DIR / "train.tsv.zip"
MERCARI_TEST_TSV_PATH = MERCARI_DATA_DIR / "test.tsv"
ONLINE_AUCTIONS_DATA_DIR = EXTERNAL_DATA_DIR / "online_auctions"
ONLINE_AUCTIONS_CSV_PATH = ONLINE_AUCTIONS_DATA_DIR / "auction.csv"
TRAIN_DATA_PATH = DATA_DIR / "processed" / "train.csv"
AUCTION_BID_HISTORY_PATH = DATA_DIR / "processed" / "auction_bid_history.csv"
AUCTION_LOT_DYNAMICS_PATH = DATA_DIR / "processed" / "auction_lot_dynamics.csv"
DATASET_METADATA_PATH = DATA_DIR / "processed" / "dataset_metadata.json"

MODELS_DIR = PROJECT_ROOT / "ml" / "models"
REPORTS_DIR = PROJECT_ROOT / "ml" / "reports"

BASE_PRICE_MODEL_PATH = MODELS_DIR / "base_price_model.pkl"
FINAL_PRICE_MODEL_PATH = MODELS_DIR / "final_price_model.pkl"

BASE_PRICE_METRICS_PATH = REPORTS_DIR / "base_price_metrics.json"
BASE_PRICE_FEATURES_PATH = REPORTS_DIR / "base_price_features.json"
FINAL_PRICE_METRICS_PATH = REPORTS_DIR / "final_price_metrics.json"
AUCTION_BID_DATASET_SUMMARY_PATH = REPORTS_DIR / "auction_bid_dataset_summary.json"
AUCTION_BEHAVIOR_MODEL_PATH = REPORTS_DIR / "auction_behavior_model.json"

BASE_PRICE_TARGET = "price"
FINAL_PRICE_TARGET = "final_price"

BASE_CATEGORICAL_FEATURES = [
    "brand",
    "category",
    "condition",
    "material",
    "size",
    "has_tag",
]
BASE_NUMERIC_FEATURES = ["age"]
BASE_MODEL_FEATURES = BASE_CATEGORICAL_FEATURES + BASE_NUMERIC_FEATURES

FINAL_CATEGORICAL_FEATURES = [
    "brand",
    "category",
    "condition",
    "has_tag",
]
FINAL_NUMERIC_FEATURES = [
    "price",
    "start_price",
    "age",
    "views_count",
    "likes_count",
    "favorites_count",
    "bids_count",
]
FINAL_MODEL_FEATURES = FINAL_CATEGORICAL_FEATURES + FINAL_NUMERIC_FEATURES

RANDOM_STATE = 42
TEST_SIZE = 0.2

# Mercari prices are in USD. The platform works in RUB, so the import step
# converts labels once and stores all processed training targets in RUB.
USD_TO_RUB = 90.0

# Marketplace sale prices can train P_base, but a final auction-price model
# needs real auction rows with bid/view dynamics.
MIN_AUCTION_ROWS_FOR_FINAL_MODEL = 80
MAX_RANDOM_FOREST_TRAIN_ROWS = 50000
MAX_METRIC_ROWS = 100000
