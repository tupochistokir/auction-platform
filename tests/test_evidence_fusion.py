from app.pricing.evidence_fusion import fuse_questionnaire_evidence


def test_ai_photo_fields_fill_missing_pricing_features():
    result = fuse_questionnaire_evidence(
        {
            "category": "other",
            "subcategory": "other",
            "material": "",
            "ai_analysis": {
                "category": {"value": "accessories", "confidence": 0.91},
                "subcategory": {"value": "scarf", "confidence": 0.88},
                "material": {"value": "silk", "confidence": 0.90},
            },
        }
    )

    questionnaire = result["pricing_questionnaire"]

    assert questionnaire["category"] == "accessories"
    assert questionnaire["subcategory"] == "scarf"
    assert questionnaire["material"] == "silk"


def test_low_confidence_brand_does_not_override_seller_brand():
    result = fuse_questionnaire_evidence(
        {
            "brand": "nike",
            "ai_analysis": {"brand": {"value": "gucci", "confidence": 0.50}},
        }
    )

    assert result["pricing_questionnaire"]["brand"] == "nike"


def test_high_confidence_conflict_is_reported():
    result = fuse_questionnaire_evidence(
        {
            "material": "cotton",
            "ai_analysis": {"material": {"value": "silk", "confidence": 0.91}},
        }
    )

    assert result["pricing_questionnaire"]["material"] == "silk"
    assert result["evidence_report"]["conflicts"][0]["field"] == "material"
