from app.pricing.adjustments import (
    get_condition_multiplier,
    get_age_multiplier,
    get_tag_multiplier
)


def get_base_price(category: str, brand: str) -> float:
    category = category.lower()
    brand = brand.lower()

    base_prices = {
        "jacket": 5000,
        "coat": 6000,
        "hoodie": 3500,
        "tshirt": 2000,
        "shirt": 2500,
        "jeans": 3000,
        "sneakers": 7000
    }

    price = base_prices.get(category, 3000)

    if brand in ["alpha industries", "nike", "adidas", "carhartt", "levi's"]:
        price *= 1.3
    elif brand == "no name":
        price *= 0.8

    return round(price, 2)


def get_adjusted_base_price(
    category: str,
    brand: str,
    condition: str,
    estimated_age: int,
    has_tag: bool
) -> float:
    base_price = get_base_price(category=category, brand=brand)

    condition_multiplier = get_condition_multiplier(condition)
    age_multiplier = get_age_multiplier(estimated_age, brand)
    tag_multiplier = get_tag_multiplier(has_tag)

    adjusted_price = (
        base_price
        * condition_multiplier
        * age_multiplier
        * tag_multiplier
    )

    return round(adjusted_price, 2)


def calculate_reserve_price(base_price: float, attractiveness: float, alpha: float = 0.35) -> float:
    reserve_price = base_price * (1 - alpha * attractiveness)
    return round(reserve_price, 2)