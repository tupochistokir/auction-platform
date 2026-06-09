from app.pricing.math_core import (
    calculate_brand_confidence,
    calculate_brand_score,
    calculate_condition_score,
)
from app.pricing.resale_calibration import calculate_resale_ceiling, get_brand_segment


def test_luxury_aliases_share_segment_and_score():
    for brand in ["Saint Laurent", "YSL", "Yves Saint Laurent", "Saint-Laurent"]:
        assert calculate_brand_score(brand) == 0.94
        assert calculate_brand_confidence(brand) == 0.95
        assert get_brand_segment(brand) == "luxury"


def test_core_brand_segments():
    cases = {
        "Chanel": ("luxury", 0.96),
        "Stone Island": ("premium", 0.86),
        "Ralph Lauren": ("vintage_premium", 0.84),
        "Nike": ("sports_mass", 0.82),
        "COS": ("mid_market", 0.64),
        "Zara": ("mass", 0.42),
        "No name": ("no_name", 0.05),
        "Some Local Brand": ("other_brand", 0.35),
    }
    for brand, (segment, score) in cases.items():
        assert get_brand_segment(brand) == segment
        assert calculate_brand_score(brand) == score


def test_russian_no_name_brand_aliases():
    no_name_aliases = [
        "\u0431\u0435\u0437 \u0431\u0440\u0435\u043d\u0434\u0430",
        "\u043d\u0435\u0442 \u0431\u0440\u0435\u043d\u0434\u0430",
        "\u043d\u043e\u0443\u043d\u0435\u0439\u043c",
    ]
    not_specified_aliases = [
        "\u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d",
        "\u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e",
    ]

    for brand in no_name_aliases:
        assert get_brand_segment(brand) == "no_name"
        assert calculate_brand_score(brand) == 0.05

    for brand in not_specified_aliases:
        assert get_brand_segment(brand) == "no_name"
        assert calculate_brand_score(brand) == 0.0


def test_condition_scores_match_diploma_categories():
    assert calculate_condition_score("excellent") == 1.0
    assert calculate_condition_score("good") == 0.75
    assert calculate_condition_score("normal") == 0.55
    assert calculate_condition_score("bad") == 0.3
    assert calculate_condition_score("\u043d\u043e\u0432\u043e\u0435") == 1.0
    assert calculate_condition_score("\u0445\u043e\u0440\u043e\u0448\u0435\u0435") == 0.75
    assert calculate_condition_score("\u043d\u043e\u0440\u043c\u0430\u043b\u044c\u043d\u043e\u0435") == 0.55
    assert calculate_condition_score("\u0441 \u0434\u0435\u0444\u0435\u043a\u0442\u0430\u043c\u0438") == 0.3


def test_luxury_vintage_tagged_dress_is_not_capped_as_other_brand():
    ceiling = calculate_resale_ceiling({
        "brand": "Saint Laurent",
        "category": "dresses",
        "subcategory": "dress",
        "condition": "excellent",
        "has_tag": True,
        "estimated_age": 20,
    })
    assert ceiling["brand_segment"] == "luxury"
    assert ceiling["ceiling_price"] > 10000
    assert ceiling["floor_price"] > 5000
