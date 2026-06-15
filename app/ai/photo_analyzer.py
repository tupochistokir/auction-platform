"""Photo evidence extraction for lot pricing.

The module can use Gemini vision models when GEMINI_API_KEY is configured.
Without a key it falls back to deterministic metadata parsing, so the pricing
pipeline remains available in demo and offline modes.
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from app.pricing.brand_taxonomy import BRAND_DATA, normalize_brand_name


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

ALLOWED_CATEGORIES = {
    "tops",
    "bottoms",
    "dresses",
    "shoes",
    "outerwear",
    "accessories",
    "other",
}

ALLOWED_SUBCATEGORIES = {
    "tshirt",
    "shirt",
    "hoodie",
    "sweater",
    "top",
    "blouse",
    "jeans",
    "pants",
    "shorts",
    "skirt",
    "dress",
    "suit",
    "jumpsuit",
    "sneakers",
    "boots",
    "loafers",
    "heels",
    "jacket",
    "bomber",
    "coat",
    "trench",
    "puffer",
    "bag",
    "cap",
    "belt",
    "scarf",
    "jewelry",
    "other",
}

SUBCATEGORY_TO_CATEGORY = {
    "tshirt": "tops",
    "shirt": "tops",
    "hoodie": "tops",
    "sweater": "tops",
    "top": "tops",
    "blouse": "tops",
    "jeans": "bottoms",
    "pants": "bottoms",
    "shorts": "bottoms",
    "skirt": "bottoms",
    "dress": "dresses",
    "suit": "dresses",
    "jumpsuit": "dresses",
    "sneakers": "shoes",
    "boots": "shoes",
    "loafers": "shoes",
    "heels": "shoes",
    "jacket": "outerwear",
    "bomber": "outerwear",
    "coat": "outerwear",
    "trench": "outerwear",
    "puffer": "outerwear",
    "bag": "accessories",
    "cap": "accessories",
    "belt": "accessories",
    "scarf": "accessories",
    "jewelry": "accessories",
    "other": "other",
}

FIELD_NAMES = (
    "brand",
    "category",
    "subcategory",
    "condition",
    "estimated_age",
    "has_tag",
    "colors",
    "material",
    "style",
    "defects",
)


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalized_text(value: Any) -> str:
    value = _text(value).lower()
    value = value.replace("ё", "е")
    for char in "_-/.,:;()[]{}":
        value = value.replace(char, " ")
    return " ".join(value.split())


def _clamp_confidence(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


def _field(
    value: Any,
    confidence: float,
    reason: str,
    source: str,
) -> Dict[str, Any]:
    return {
        "value": value,
        "confidence": round(_clamp_confidence(confidence), 3),
        "reason": reason,
        "source": source,
    }


def _empty_result(source: str) -> Dict[str, Any]:
    return {
        field: _field(None, 0.0, "not_detected", source)
        for field in FIELD_NAMES
    }


def _context_text(context: Dict[str, Any], images: List[Dict[str, Any]]) -> str:
    questionnaire = context.get("questionnaire") or {}
    pieces = [
        context.get("title"),
        context.get("description"),
        questionnaire.get("brand"),
        questionnaire.get("category"),
        questionnaire.get("subcategory"),
        questionnaire.get("material"),
        questionnaire.get("style"),
        questionnaire.get("defects"),
        questionnaire.get("seller_comment"),
    ]
    pieces.extend(image.get("filename") for image in images)
    return _normalized_text(" ".join(_text(piece) for piece in pieces if piece))


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(_normalized_text(keyword) in text for keyword in keywords)


def _detect_brand(text: str, questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    seller_brand = normalize_brand_name(questionnaire.get("brand"))
    if seller_brand and seller_brand not in {"unknown", "not specified", "no name"}:
        return _field(seller_brand, 0.74, "seller_context_contains_brand", "local_metadata_fallback")

    # Prefer longer names first, otherwise "boss" could match before "hugo boss".
    for brand in sorted(BRAND_DATA, key=len, reverse=True):
        pattern = rf"(^|\s){re.escape(brand)}($|\s)"
        if re.search(pattern, text):
            return _field(brand, 0.78, "brand_keyword_detected_in_text_or_filename", "local_metadata_fallback")

    simple_aliases = {
        "ysl": "saint laurent",
        "lv": "louis vuitton",
        "levis": "levi's",
        "north face": "the north face",
        "tnf": "the north face",
    }
    for alias, brand in simple_aliases.items():
        if re.search(rf"(^|\s){re.escape(alias)}($|\s)", text):
            return _field(brand, 0.72, "brand_alias_detected", "local_metadata_fallback")

    return _field(None, 0.0, "brand_not_detected", "local_metadata_fallback")


def _detect_category(text: str, questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    category = _normalized_text(questionnaire.get("category"))
    if category in ALLOWED_CATEGORIES and category != "other":
        return _field(category, 0.72, "seller_context_contains_category", "local_metadata_fallback")

    keyword_map = {
        "scarf": ["scarf", "шарф", "платок", "палантин"],
        "bag": ["bag", "сумка", "рюкзак", "клатч"],
        "belt": ["belt", "ремень"],
        "cap": ["cap", "hat", "кепка", "шапка"],
        "jewelry": ["jewelry", "ring", "necklace", "украш", "кольцо", "цепь"],
        "sneakers": ["sneakers", "кроссов", "кеды"],
        "boots": ["boots", "ботин", "сапог"],
        "loafers": ["loafers", "лофер"],
        "heels": ["heels", "туфли", "каблук"],
        "bomber": ["bomber", "бомбер"],
        "jacket": ["jacket", "куртка", "ветровка"],
        "coat": ["coat", "пальто", "парка"],
        "trench": ["trench", "тренч"],
        "puffer": ["puffer", "пуховик"],
        "hoodie": ["hoodie", "худи", "свитшот"],
        "sweater": ["sweater", "свитер", "кардиган"],
        "shirt": ["shirt", "рубашка", "лонгслив"],
        "tshirt": ["tshirt", "t shirt", "футболка"],
        "jeans": ["jeans", "джинс"],
        "pants": ["pants", "брюки", "штаны"],
        "shorts": ["shorts", "шорты"],
        "skirt": ["skirt", "юбка"],
        "dress": ["dress", "платье"],
        "suit": ["suit", "костюм"],
        "jumpsuit": ["jumpsuit", "комбинезон"],
    }

    for subcategory, keywords in keyword_map.items():
        if _contains_any(text, keywords):
            return _field(
                SUBCATEGORY_TO_CATEGORY.get(subcategory, "other"),
                0.76,
                f"subcategory_keyword_detected:{subcategory}",
                "local_metadata_fallback",
            )

    return _field("other", 0.42, "category_not_detected", "local_metadata_fallback")


def _detect_subcategory(text: str, questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    subcategory = _normalized_text(questionnaire.get("subcategory"))
    if subcategory in ALLOWED_SUBCATEGORIES and subcategory != "other":
        return _field(subcategory, 0.72, "seller_context_contains_subcategory", "local_metadata_fallback")

    category_result = _detect_category(text, questionnaire)
    reason = _text(category_result.get("reason"))
    if reason.startswith("subcategory_keyword_detected:"):
        return _field(reason.split(":", 1)[1], 0.76, reason, "local_metadata_fallback")

    return _field("other", 0.42, "subcategory_not_detected", "local_metadata_fallback")


def _detect_condition(text: str, questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    condition = _normalized_text(questionnaire.get("condition"))
    if condition in {"excellent", "good", "normal", "bad"}:
        return _field(condition, 0.65, "seller_context_contains_condition", "local_metadata_fallback")

    if _contains_any(text, ["new with tags", "new tag", "nwt", "deadstock", "новое", "с биркой"]):
        return _field("excellent", 0.72, "new_or_deadstock_keyword", "local_metadata_fallback")
    if _contains_any(text, ["defect", "stain", "hole", "repair", "пятно", "дыр", "дефект"]):
        return _field("bad", 0.74, "defect_keyword", "local_metadata_fallback")
    if _contains_any(text, ["good", "excellent", "отлич", "хорош"]):
        return _field("good", 0.64, "condition_keyword", "local_metadata_fallback")

    return _field(None, 0.0, "condition_not_detected", "local_metadata_fallback")


def _detect_age(text: str, questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    try:
        seller_age = int(float(questionnaire.get("estimated_age") or 0))
    except (TypeError, ValueError):
        seller_age = 0
    if seller_age > 0:
        return _field(seller_age, 0.68, "seller_context_contains_age", "local_metadata_fallback")

    current_year = datetime.utcnow().year
    year_match = re.search(r"\b(19[6-9]\d|20[0-1]\d)\b", text)
    if year_match:
        return _field(max(0, current_year - int(year_match.group(1))), 0.72, "year_keyword_detected", "local_metadata_fallback")

    decade_map = {
        "70s": 50,
        "80s": 40,
        "90s": 30,
        "00s": 20,
        "нулев": 20,
        "девяност": 30,
    }
    for keyword, age in decade_map.items():
        if keyword in text:
            return _field(age, 0.66, f"decade_keyword:{keyword}", "local_metadata_fallback")

    if _contains_any(text, ["vintage", "archive", "винтаж", "архив"]):
        return _field(15, 0.60, "vintage_or_archive_keyword", "local_metadata_fallback")

    return _field(None, 0.0, "age_not_detected", "local_metadata_fallback")


def _detect_has_tag(text: str, questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    if questionnaire.get("has_tag") is True:
        return _field(True, 0.70, "seller_context_has_tag", "local_metadata_fallback")
    if _contains_any(text, ["без бирки", "no tag", "without tag"]):
        return _field(False, 0.72, "negative_tag_keyword", "local_metadata_fallback")
    if _contains_any(text, ["tag", "tags", "бирка", "этикетка", "nwt", "deadstock"]):
        return _field(True, 0.74, "tag_keyword", "local_metadata_fallback")
    return _field(None, 0.0, "tag_not_detected", "local_metadata_fallback")


def _detect_colors(text: str, questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    seller_colors = questionnaire.get("colors")
    if isinstance(seller_colors, list) and seller_colors:
        return _field(seller_colors[:4], 0.68, "seller_context_contains_colors", "local_metadata_fallback")

    color_map = {
        "black": ["black", "черн"],
        "white": ["white", "бел"],
        "red": ["red", "красн", "бордо"],
        "blue": ["blue", "син", "голуб"],
        "green": ["green", "зелен"],
        "brown": ["brown", "коричн"],
        "beige": ["beige", "беж"],
        "gray": ["gray", "grey", "сер"],
        "pink": ["pink", "роз"],
        "yellow": ["yellow", "желт"],
        "purple": ["purple", "фиолет"],
    }
    colors = [color for color, keywords in color_map.items() if _contains_any(text, keywords)]
    if colors:
        return _field(colors[:4], 0.64, "color_keyword_detected", "local_metadata_fallback")
    return _field([], 0.0, "colors_not_detected", "local_metadata_fallback")


def _detect_material(text: str, questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    seller_material = _text(questionnaire.get("material"))
    if seller_material:
        return _field(seller_material, 0.66, "seller_context_contains_material", "local_metadata_fallback")

    material_map = {
        "silk": ["silk", "шелк", "шёлк"],
        "leather": ["leather", "кожа", "кожан"],
        "denim": ["denim", "джинс"],
        "wool": ["wool", "шерсть", "шерст"],
        "cotton": ["cotton", "хлопок"],
        "cashmere": ["cashmere", "кашемир"],
        "linen": ["linen", "лен", "лён"],
        "suede": ["suede", "замша"],
        "nylon": ["nylon", "нейлон"],
        "polyester": ["polyester", "полиэстер"],
    }
    for material, keywords in material_map.items():
        if _contains_any(text, keywords):
            return _field(material, 0.70, "material_keyword_detected", "local_metadata_fallback")
    return _field(None, 0.0, "material_not_detected", "local_metadata_fallback")


def _detect_style(text: str, questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    seller_style = _text(questionnaire.get("style"))
    if seller_style:
        return _field(seller_style, 0.64, "seller_context_contains_style", "local_metadata_fallback")
    for style in ["vintage", "archive", "streetwear", "minimal", "classic", "sport"]:
        if style in text:
            return _field(style, 0.62, "style_keyword_detected", "local_metadata_fallback")
    if _contains_any(text, ["винтаж", "архив"]):
        return _field("vintage", 0.62, "style_keyword_detected", "local_metadata_fallback")
    return _field(None, 0.0, "style_not_detected", "local_metadata_fallback")


def _detect_defects(text: str, questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    seller_defects = _text(questionnaire.get("defects"))
    if seller_defects:
        return _field(seller_defects, 0.70, "seller_context_contains_defects", "local_metadata_fallback")
    if _contains_any(text, ["stain", "hole", "scratch", "repair", "пятно", "дыр", "царап", "ремонт"]):
        return _field("visible or declared defects", 0.62, "defect_keyword_detected", "local_metadata_fallback")
    return _field(None, 0.0, "defects_not_detected", "local_metadata_fallback")


def _local_metadata_fallback(
    images: List[Dict[str, Any]],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    questionnaire = context.get("questionnaire") or {}
    text = _context_text(context, images)
    result = _empty_result("local_metadata_fallback")
    result["brand"] = _detect_brand(text, questionnaire)
    result["category"] = _detect_category(text, questionnaire)
    result["subcategory"] = _detect_subcategory(text, questionnaire)
    result["condition"] = _detect_condition(text, questionnaire)
    result["estimated_age"] = _detect_age(text, questionnaire)
    result["has_tag"] = _detect_has_tag(text, questionnaire)
    result["colors"] = _detect_colors(text, questionnaire)
    result["material"] = _detect_material(text, questionnaire)
    result["style"] = _detect_style(text, questionnaire)
    result["defects"] = _detect_defects(text, questionnaire)
    return result


def _gemini_prompt(context: Dict[str, Any]) -> str:
    title = _text(context.get("title"))
    description = _text(context.get("description"))
    questionnaire = context.get("questionnaire") or {}
    return f"""
You analyze fashion resale / second-hand lot photos for an explainable pricing engine.
Use the images first. Use seller text only as additional context. Do not invent a brand if the logo, label, text, or seller context is not enough.

Seller context:
title: {title}
description: {description}
questionnaire: {json.dumps(questionnaire, ensure_ascii=False)}

Return only valid JSON with this exact structure:
{{
  "brand": {{"value": string|null, "confidence": number, "reason": string}},
  "category": {{"value": "tops|bottoms|dresses|shoes|outerwear|accessories|other", "confidence": number, "reason": string}},
  "subcategory": {{"value": "tshirt|shirt|hoodie|sweater|top|blouse|jeans|pants|shorts|skirt|dress|suit|jumpsuit|sneakers|boots|loafers|heels|jacket|bomber|coat|trench|puffer|bag|cap|belt|scarf|jewelry|other", "confidence": number, "reason": string}},
  "condition": {{"value": "excellent|good|normal|bad|unknown", "confidence": number, "reason": string}},
  "estimated_age": {{"value": integer|null, "confidence": number, "reason": string}},
  "has_tag": {{"value": boolean|null, "confidence": number, "reason": string}},
  "colors": {{"value": array, "confidence": number, "reason": string}},
  "material": {{"value": string|null, "confidence": number, "reason": string}},
  "style": {{"value": string|null, "confidence": number, "reason": string}},
  "defects": {{"value": string|null, "confidence": number, "reason": string}}
}}

Confidence must be from 0 to 1. If a feature is not visible or not supported by context, set value null and confidence below 0.5.
""".strip()


def _extract_response_text(payload: Dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = (candidates[0].get("content") or {}).get("parts") or []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            return part["text"]
    return ""


def _loads_json_response(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def _call_gemini(
    images: List[Dict[str, Any]],
    context: Dict[str, Any],
) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    model = os.getenv("GEMINI_VISION_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    timeout = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "25"))
    parts: List[Dict[str, Any]] = [{"text": _gemini_prompt(context)}]

    for image in images[:3]:
        data = image.get("data")
        if not data:
            continue
        parts.append(
            {
                "inline_data": {
                    "mime_type": image.get("content_type") or "image/jpeg",
                    "data": base64.b64encode(bytes(data)).decode("ascii"),
                }
            }
        )

    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0.05,
            "response_mime_type": "application/json",
        },
    }
    request = urllib.request.Request(
        GEMINI_API_URL.format(model=model),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API error {exc.code}: {error_body[:500]}") from exc

    response_text = _extract_response_text(response_payload)
    if not response_text:
        raise RuntimeError("Gemini API returned empty text")

    parsed = _loads_json_response(response_text)
    return {
        "model": model,
        "raw": parsed,
    }


def _normalize_condition(value: Any) -> Optional[str]:
    normalized = _normalized_text(value)
    if normalized in {"excellent", "new", "new with tags", "nwt", "like new"}:
        return "excellent"
    if normalized in {"good", "very good"}:
        return "good"
    if normalized in {"normal", "fair", "used", "satisfactory", "unknown"}:
        return "normal" if normalized != "unknown" else "unknown"
    if normalized in {"bad", "poor", "damaged", "defective"}:
        return "bad"
    return None


def _normalize_category(value: Any) -> str:
    normalized = _normalized_text(value)
    return normalized if normalized in ALLOWED_CATEGORIES else "other"


def _normalize_subcategory(value: Any) -> str:
    normalized = _normalized_text(value)
    return normalized if normalized in ALLOWED_SUBCATEGORIES else "other"


def _normalize_field(field: str, raw: Any, source: str) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return _field(None, 0.0, "invalid_field_format", source)

    value = raw.get("value")
    confidence = _clamp_confidence(raw.get("confidence"))
    reason = _text(raw.get("reason")) or "vision_evidence"

    if field == "brand":
        normalized = normalize_brand_name(value)
        value = normalized if normalized and normalized != "unknown" else None
    elif field == "category":
        value = _normalize_category(value)
    elif field == "subcategory":
        value = _normalize_subcategory(value)
    elif field == "condition":
        value = _normalize_condition(value)
    elif field == "estimated_age":
        try:
            value = max(0, min(120, int(float(value)))) if value is not None else None
        except (TypeError, ValueError):
            value = None
            confidence = 0.0
    elif field == "has_tag":
        value = value if isinstance(value, bool) else None
    elif field == "colors":
        if isinstance(value, list):
            value = [_normalized_text(item) for item in value if _text(item)][:5]
        elif _text(value):
            value = [_normalized_text(value)]
        else:
            value = []
    elif field in {"material", "style", "defects"}:
        value = _text(value) or None

    return _field(value, confidence, reason, source)


def _normalize_ai_analysis(raw: Dict[str, Any], source: str) -> Dict[str, Any]:
    normalized = _empty_result(source)
    for field in FIELD_NAMES:
        normalized[field] = _normalize_field(field, raw.get(field), source)

    subcategory = normalized["subcategory"]["value"]
    category = normalized["category"]["value"]
    inferred_category = SUBCATEGORY_TO_CATEGORY.get(subcategory)
    if inferred_category and inferred_category != "other" and (not category or category == "other"):
        normalized["category"] = _field(
            inferred_category,
            max(normalized["subcategory"]["confidence"], 0.68),
            "category_inferred_from_subcategory",
            source,
        )

    return normalized


def _summary(ai_analysis: Dict[str, Any]) -> List[str]:
    rows = []
    for field in FIELD_NAMES:
        data = ai_analysis.get(field) or {}
        value = data.get("value")
        confidence = _clamp_confidence(data.get("confidence"))
        if value not in (None, "", [], {}) and confidence >= 0.55:
            rows.append(f"{field}: {value} ({confidence:.2f})")
    return rows


def analyze_lot_photo_evidence(
    images: List[Dict[str, Any]],
    questionnaire: Optional[Dict[str, Any]] = None,
    title: str = "",
    description: str = "",
) -> Dict[str, Any]:
    """Extract structured visual evidence for the pricing pipeline."""
    context = {
        "title": title,
        "description": description,
        "questionnaire": questionnaire or {},
    }

    provider_error = None
    source = "gemini"
    model = os.getenv("GEMINI_VISION_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL

    try:
        gemini_result = _call_gemini(images, context)
        raw_analysis = gemini_result["raw"]
        model = gemini_result["model"]
    except Exception as exc:
        provider_error = str(exc)
        source = "local_metadata_fallback"
        model = "deterministic_metadata_fallback"
        raw_analysis = _local_metadata_fallback(images, context)

    ai_analysis = _normalize_ai_analysis(raw_analysis, source)
    return {
        "source": source,
        "model": model,
        "ai_analysis": ai_analysis,
        "summary": _summary(ai_analysis),
        "provider_error": provider_error,
    }
