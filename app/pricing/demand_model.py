from typing import Any, Dict


def normalize(value: float, max_value: float) -> float:
    """Normalize a non-negative metric to the interval [0, 1]."""
    if max_value <= 0:
        return 0.0
    return round(max(0.0, min(1.0, float(value) / max_value)), 4)


def calculate_demand_score(
    bids_count: int,
    offers_count: int = 0,
    bid_velocity: float = 0.0,
    current_price: float = 0.0,
    start_price: float = 0.0,
    views_count: int = 0,
    favorites_count: int = 0,
    likes_count: int = 0,
) -> float:
    """
    Calculate demand score D from actual trading actions.

    D answers whether users are ready to pay money for the lot. Views, likes and
    favorites are accepted only as legacy arguments and do not affect demand.
    """
    bids_norm = normalize(bids_count, 50)
    offers_norm = normalize(offers_count, 20)
    velocity_norm = normalize(bid_velocity, 10)

    if start_price and start_price > 0 and current_price and current_price > 0:
        price_growth = max(0.0, float(current_price) / float(start_price) - 1.0)
    else:
        price_growth = 0.0
    price_pressure_norm = normalize(price_growth, 0.75)

    demand = (
        0.42 * bids_norm
        + 0.28 * offers_norm
        + 0.18 * velocity_norm
        + 0.12 * price_pressure_norm
    )
    return round(max(0.0, min(1.0, demand)), 4)


def calculate_interest_score(
    views_count: int,
    likes_count: int,
    favorites_count: int,
    bids_count: int = 0,
    offers_count: int = 0,
) -> float:
    """
    Calculate user interest score I from pre-purchase engagement.

    I answers whether users noticed the lot before they necessarily start
    bidding. Bids and offers are accepted only for backward compatibility and
    do not affect the score.
    """
    likes_norm = normalize(likes_count, 300)
    favorites_norm = normalize(favorites_count, 200)
    views_norm = normalize(views_count, 1000)

    interest = (
        0.45 * views_norm
        + 0.30 * favorites_norm
        + 0.25 * likes_norm
    )
    return round(max(0.0, min(1.0, interest)), 4)


def calculate_uncertainty_score(
    price_std: float,
    base_price: float,
    rarity_score: float,
) -> float:
    """Calculate uncertainty score V from price dispersion and rarity."""
    if base_price <= 0:
        relative_std = 0.0
    else:
        relative_std = max(0.0, float(price_std) / float(base_price))

    uncertainty = 0.60 * relative_std + 0.40 * max(0.0, min(1.0, float(rarity_score)))
    return round(max(0.0, min(1.0, uncertainty)), 4)


def _get(source: Any, field: str, default: float = 0.0) -> float:
    if isinstance(source, dict):
        value = source.get(field, default)
    else:
        value = getattr(source, field, default)

    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_market_signals(auction_or_dict: Any) -> Dict[str, float]:
    """Return demand, interest and uncertainty scores from an auction object or dict."""
    views_count = int(_get(auction_or_dict, "views_count", 0))
    likes_count = int(_get(auction_or_dict, "likes_count", 0))
    favorites_count = int(_get(auction_or_dict, "favorites_count", 0))
    bids_count = int(_get(auction_or_dict, "bids_count", 0))
    offers_count = int(_get(auction_or_dict, "offers_count", 0))
    bid_velocity = _get(auction_or_dict, "bid_velocity", 0)
    current_price = _get(auction_or_dict, "current_price", 0)
    start_price = _get(auction_or_dict, "start_price", 0)
    price_std = _get(auction_or_dict, "price_std", 0)
    base_price = _get(auction_or_dict, "base_price", 0)
    rarity_score = _get(auction_or_dict, "rarity_score", 0)
    no_live_activity = (
        bids_count <= 0
        and offers_count <= 0
        and views_count <= 0
        and likes_count <= 0
        and favorites_count <= 0
    )
    if start_price and start_price > 0 and current_price and current_price > 0:
        price_growth = max(0.0, float(current_price) / float(start_price) - 1.0)
    else:
        price_growth = 0.0

    return {
        "demand_score": calculate_demand_score(
            bids_count=bids_count,
            offers_count=offers_count,
            bid_velocity=bid_velocity,
            current_price=current_price,
            start_price=start_price,
        ),
        "interest_score": calculate_interest_score(
            views_count=views_count,
            likes_count=likes_count,
            favorites_count=favorites_count,
        ),
        "uncertainty_score": calculate_uncertainty_score(
            price_std=price_std,
            base_price=base_price,
            rarity_score=rarity_score,
        ),
        "price_pressure_score": normalize(price_growth, 0.75),
        "no_live_activity": no_live_activity,
    }
