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

    condition_scores = {
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
    condition_score = condition_scores.get(condition, 0.55)

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
