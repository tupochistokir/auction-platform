def calculate_attractiveness(
    value_score: float,
    brand: str,
    estimated_age: int,
    has_tag: bool
) -> float:
    brand = (brand or "unknown").lower()
    estimated_age = estimated_age or 0

    strong_brands = ["alpha industries", "nike", "adidas", "carhartt", "levi's"]

    brand_factor = 0.6
    if brand in strong_brands:
        brand_factor = 0.9
    elif brand == "no name":
        brand_factor = 0.3
    elif brand == "unknown":
        brand_factor = 0.5

    age_factor = min(estimated_age / 20, 1.0) if estimated_age > 0 else 0.2
    tag_factor = 1.0 if has_tag else 0.7

    attractiveness = (
        0.5 * value_score +
        0.25 * brand_factor +
        0.15 * age_factor +
        0.10 * tag_factor
    )

    return round(min(attractiveness, 1.0), 2)