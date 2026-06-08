import random

def estimate_base_price_ml(questionnaire):
    base = 2000

    brand = questionnaire.get("brand", "")
    if brand.lower() in ["nike", "adidas", "alpha industries"]:
        base *= 1.5

    condition = (questionnaire.get("condition") or "normal").lower()
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
    base *= condition_multipliers.get(condition, 0.55)

    age = questionnaire.get("estimated_age", 0)
    if age > 10:
        base *= 1.4

    noise = random.uniform(0.9, 1.1)

    return base * noise
