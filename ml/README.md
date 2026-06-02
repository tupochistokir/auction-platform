# ML data pipeline

The main real dataset for base market price is Mercari Price Suggestion
Challenge. It contains marketplace item names, categories, brand names,
condition ids, descriptions and sale prices.

1. Download the Kaggle competition data.
2. Extract or place `train.tsv` into:

```text
data/external/mercari/train.tsv
```

`train.tsv.zip` is also supported. If Kaggle gives `train.tsv.7z`, extract it
with 7-Zip first.

Then run:

```powershell
pip install pandas scikit-learn joblib
python ml/prepare_dataset.py
python ml/train_base_price_model.py
python ml/train_final_price_model.py
python ml/evaluate.py
```

Important: Mercari is valid for `P_base` because it has real sale prices. It is
not valid for training auction closing price because it has no bid history.
`train_final_price_model.py` skips training until the platform has enough real
auction rows.

## Auction behavior dataset

The second dataset is stored in:

```text
data/external/online_auctions/auction.csv
data/processed/auction_bid_history.csv
data/processed/auction_lot_dynamics.csv
ml/reports/auction_behavior_model.json
```

It is not used as a direct price source for clothing. It is used only to model
buyer behavior in auctions. The current implementation transfers robust median
`final_price / start_price` ratios by bid-count bucket into the resale fashion
domain with a limited transfer factor:

```text
1 bid     -> 1.00
2-3 bids  -> 1.0417
4-6 bids  -> 1.193
7-12 bids -> 1.6667
13+ bids  -> 5.6357
```

For fashion resale the transferred uplift is:

```text
auction_uplift = 1 + (median_ratio - 1) * fashion_transfer_factor
```

Default `fashion_transfer_factor` is `0.30`; it prevents electronics/watch
auction dynamics from being copied into clothing prices too aggressively.

TODO: replace the transfer factor with calibration from real platform clothing
auctions after enough completed lots are collected.
