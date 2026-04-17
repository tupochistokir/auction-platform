def calculate_bid_step(base_price: float, value_score: float) -> float:
    if base_price < 3000:
        step_percent = 0.03
    elif base_price < 7000:
        step_percent = 0.05
    else:
        step_percent = 0.07

    value_adjustment = 1 + (value_score - 0.5) * 0.4

    bid_step = base_price * step_percent * value_adjustment

    return round(max(bid_step, 50), 2)