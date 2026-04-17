def calculate_expected_final_price(
    base_price: float,
    attractiveness: float,
    value_score: float
) -> float:
    growth_factor = 1 + 0.08 + 0.22 * attractiveness + 0.12 * value_score
    expected_final_price = base_price * growth_factor
    return round(expected_final_price, 2)


def calculate_auction_gain(expected_final_price: float, reserve_price: float) -> float:
    gain = expected_final_price - reserve_price
    return round(gain, 2)


def calculate_expected_seller_profit(
    expected_final_price: float,
    cost_price: float
) -> float:
    profit = expected_final_price - cost_price
    return round(profit, 2)


def calculate_platform_fee(
    expected_final_price: float,
    fee_rate: float = 0.05
) -> float:
    fee = expected_final_price * fee_rate
    return round(fee, 2)