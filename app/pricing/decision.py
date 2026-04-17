def seller_decision(offer, expected_price):
    risk = expected_price * 0.2

    utility_wait = expected_price - risk

    if offer >= utility_wait:
        return "accept"
    else:
        return "wait"