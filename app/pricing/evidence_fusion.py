"""Fusion of seller questionnaire and optional external vision evidence.

This module does not train or imitate a computer-vision model. It only consumes
structured output from an external image-recognition service when such output is
available. The pricing model remains explainable: final item attributes are
chosen by deterministic confidence rules, then passed to math_core.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, Optional


LOW_CONFIDENCE = 0.60
HIGH_CONFIDENCE = 0.85

OBJECTIVE_FIELDS = {"brand", "condition", "estimated_age", "has_tag", "color", "colors"}


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalized_text(value: Any) -> str:
    return " ".join(_text(value).lower().replace("_", " ").split())


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _confidence(value: Any) -> float:
    return max(0.0, min(1.0, _number(value, 0.0)))


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return _normalized_text(value) in {"", "unknown", "not specified", "не указан"}
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes)):
        return len(list(value)) == 0
    return False


def _extract_ai_field(ai_analysis: Dict[str, Any], field: str) -> Dict[str, Any]:
    raw = ai_analysis.get(field)
    if not isinstance(raw, dict):
        return {"value": None, "confidence": 0.0}

    return {
        "value": raw.get("value"),
        "confidence": _confidence(raw.get("confidence")),
        "raw": raw,
    }


def _values_match(left: Any, right: Any) -> bool:
    if isinstance(left, list) or isinstance(right, list):
        left_set = {_normalized_text(item) for item in (left if isinstance(left, list) else [left])}
        right_set = {_normalized_text(item) for item in (right if isinstance(right, list) else [right])}
        left_set.discard("")
        right_set.discard("")
        return bool(left_set and right_set and left_set.intersection(right_set))

    return _normalized_text(left) == _normalized_text(right)


def choose_attribute_value(
    field: str,
    seller_value: Any,
    ai_value: Any,
    ai_confidence: float,
) -> Dict[str, Any]:
    """Choose final attribute value from seller input and optional AI evidence.

    Confidence zones are intentionally simple:
    - below 0.60: external vision evidence is weak, so it cannot override seller
      input;
    - 0.60-0.85: evidence is useful for missing fields or agreement checks;
    - 0.85 and above: evidence is treated as strong for objective visual fields.

    This keeps the diploma explanation compact: AI is not a separate pricing
    model, it is only one more source of observable item features.
    """
    ai_confidence = _confidence(ai_confidence)
    seller_missing = _is_missing(seller_value)
    ai_missing = _is_missing(ai_value)
    matches = not seller_missing and not ai_missing and _values_match(seller_value, ai_value)

    if ai_missing or ai_confidence < LOW_CONFIDENCE:
        return {
            "value": None if seller_missing else seller_value,
            "source": "seller" if not seller_missing else "missing",
            "confidence": 0.95 if not seller_missing else 0.0,
            "conflict": False,
            "reason": "ai_not_available_or_low_confidence",
        }

    if seller_missing:
        return {
            "value": ai_value,
            "source": "external_ai",
            "confidence": ai_confidence,
            "conflict": False,
            "reason": "seller_missing_ai_used",
        }

    if matches:
        return {
            "value": seller_value,
            "source": "seller_ai_agree",
            "confidence": min(1.0, 0.5 * 0.95 + 0.5 * ai_confidence),
            "conflict": False,
            "reason": "seller_and_ai_match",
        }

    if field in OBJECTIVE_FIELDS and ai_confidence >= HIGH_CONFIDENCE:
        return {
            "value": ai_value,
            "source": "external_ai",
            "confidence": ai_confidence,
            "conflict": True,
            "reason": "high_confidence_ai_overrides_seller",
        }

    return {
        "value": seller_value,
        "source": "seller",
        "confidence": 0.95,
        "conflict": True,
        "reason": "seller_kept_ai_not_confident_enough",
    }


def fuse_questionnaire_evidence(questionnaire: Dict[str, Any]) -> Dict[str, Any]:
    """Return effective pricing inputs and an audit report.

    Expected optional AI format:
    {
      "brand": {"value": "adidas", "confidence": 0.90},
      "condition": {"value": "good", "confidence": 0.75},
      "estimated_age": {"value": 12, "confidence": 0.68},
      "has_tag": {"value": true, "confidence": 0.82},
      "colors": {"value": ["black"], "confidence": 0.91}
    }
    """
    seller_input = deepcopy(questionnaire or {})
    ai_analysis = seller_input.get("ai_analysis") or {}
    if not isinstance(ai_analysis, dict):
        ai_analysis = {}

    effective = deepcopy(seller_input)
    decisions: Dict[str, Any] = {}
    conflicts = []

    for field in sorted(OBJECTIVE_FIELDS):
        ai_field = _extract_ai_field(ai_analysis, field)
        decision = choose_attribute_value(
            field=field,
            seller_value=seller_input.get(field),
            ai_value=ai_field["value"],
            ai_confidence=ai_field["confidence"],
        )
        decisions[field] = decision

        if decision["value"] is not None:
            effective[field] = decision["value"]

        if decision["conflict"]:
            conflicts.append(
                {
                    "field": field,
                    "seller_value": seller_input.get(field),
                    "ai_value": ai_field["value"],
                    "ai_confidence": ai_field["confidence"],
                    "chosen_source": decision["source"],
                }
            )

    if "color" in effective and "colors" not in effective:
        effective["colors"] = [effective["color"]]

    return {
        "pricing_questionnaire": effective,
        "evidence_report": {
            "seller_input": seller_input,
            "ai_analysis": ai_analysis,
            "decisions": decisions,
            "conflicts": conflicts,
            "ai_used": bool(ai_analysis),
            "confidence_thresholds": {
                "low": LOW_CONFIDENCE,
                "high": HIGH_CONFIDENCE,
            },
        },
    }
