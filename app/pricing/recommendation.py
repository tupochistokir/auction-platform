def estimate_win_probability(current_price: float, user_bid: float, base_price: float) -> float:
    if user_bid <= current_price:
        return 0.05

    gap = user_bid - current_price
    pressure = current_price / max(base_price, 1)

    probability = 0.2 + (gap / max(base_price, 1)) * 2.5 - 0.3 * pressure

    probability = max(0.05, min(probability, 0.95))
    return round(probability, 2)


def calculate_recommended_bid(
    current_price: float,
    base_price: float,
    value_score: float,
    bid_step: float
) -> dict:
    user_value = base_price * (1 + 0.25 * value_score)

    candidate_bids = [
        current_price + bid_step,
        current_price + 2 * bid_step,
        current_price + 3 * bid_step
    ]

    best_bid = candidate_bids[0]
    best_utility = -1
    best_probability = 0.0

    for bid in candidate_bids:
        win_probability = estimate_win_probability(
            current_price=current_price,
            user_bid=bid,
            base_price=base_price
        )

        utility = win_probability * (user_value - bid)

        if utility > best_utility:
            best_utility = utility
            best_bid = bid
            best_probability = win_probability

    return {
        "recommended_bid": round(best_bid, 2),
        "estimated_user_value": round(user_value, 2),
        "win_probability": round(best_probability, 2),
        "expected_utility": round(best_utility, 2)
    }