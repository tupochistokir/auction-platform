from app.ai.photo_analyzer import analyze_lot_photo_evidence


def test_local_fallback_extracts_metadata_without_gemini(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    result = analyze_lot_photo_evidence(
        [{"filename": "gucci_silk_scarf.jpg", "content_type": "image/jpeg", "data": b"fake"}],
        {},
        title="Gucci silk scarf with tag",
        description="red vintage scarf",
    )
    ai = result["ai_analysis"]

    assert result["source"] == "local_metadata_fallback"
    assert ai["brand"]["value"] == "gucci"
    assert ai["category"]["value"] == "accessories"
    assert ai["subcategory"]["value"] == "scarf"
    assert ai["material"]["value"] == "silk"
