def get_condition_multiplier(condition: str) -> float:
    condition = (condition or "good").lower()

    condition_multipliers = {
        "new": 1.0,
        "excellent": 1.0,
        "новое": 1.0,
        "good": 0.75,
        "хорошее": 0.75,
        "normal": 0.55,
        "нормальное": 0.55,
        "bad": 0.3,
        "defective": 0.3,
        "с дефектами": 0.3,
        "unknown": 0.55,
        "": 0.55,
    }

    return condition_multipliers.get(condition, 0.55)


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
