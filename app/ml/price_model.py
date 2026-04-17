import random

def estimate_base_price_ml(questionnaire):
    base = 2000

    brand = questionnaire.get("brand", "")
    if brand.lower() in ["nike", "adidas", "alpha industries"]:
        base *= 1.5

    if questionnaire.get("condition") == "excellent":
        base *= 1.3

    age = questionnaire.get("estimated_age", 0)
    if age > 10:
        base *= 1.4

    noise = random.uniform(0.9, 1.1)

    return base * noise