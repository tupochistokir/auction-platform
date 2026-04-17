def analyze_lot(questionnaire: dict):
    brand = (questionnaire.get("brand") or "unknown").lower()
    age = questionnaire.get("estimated_age") or 0
    condition = (questionnaire.get("condition") or "good").lower()

    brand_score = 0.5
    if brand in ["alpha industries", "nike", "adidas", "carhartt", "levi's"]:
        brand_score = 0.9
    elif brand == "no name":
        brand_score = 0.3
    elif brand == "unknown":
        brand_score = 0.45

    vintage_score = min(age / 20, 1.0) if age > 0 else 0.2

    condition_score = 0.5
    if condition == "excellent":
        condition_score = 0.9
    elif condition == "good":
        condition_score = 0.7
    elif condition == "bad":
        condition_score = 0.3
    elif condition == "unknown":
        condition_score = 0.5

    value_score = (
        0.4 * brand_score +
        0.3 * vintage_score +
        0.3 * condition_score
    )

    return {
        "brand_score": round(brand_score, 2),
        "vintage_score": round(vintage_score, 2),
        "condition_score": round(condition_score, 2),
        "value_score": round(value_score, 2)
    }