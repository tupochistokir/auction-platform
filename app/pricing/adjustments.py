def get_condition_multiplier(condition: str) -> float:
    condition = (condition or "good").lower()

    if condition == "excellent":
        return 1.15
    elif condition == "good":
        return 1.0
    elif condition == "bad":
        return 0.75
    elif condition == "unknown":
        return 0.95

    return 1.0


def get_age_multiplier(estimated_age: int, brand: str) -> float:
    estimated_age = estimated_age or 0
    brand = (brand or "unknown").lower()

    strong_brands = ["alpha industries", "nike", "adidas", "carhartt", "levi's"]

    if estimated_age >= 15 and brand in strong_brands:
        return 1.2
    elif estimated_age >= 15 and brand == "no name":
        return 0.85
    elif estimated_age >= 15 and brand == "unknown":
        return 0.95
    elif estimated_age >= 5:
        return 1.05

    return 1.0


def get_tag_multiplier(has_tag: bool) -> float:
    return 1.1 if has_tag else 1.0