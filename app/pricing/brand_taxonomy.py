"""Shared fashion brand taxonomy for pricing and resale calibration."""

import unicodedata
from typing import Any, Dict


NO_NAME_SCORE = 0.05
UNKNOWN_BRAND_SCORE = 0.35


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _normalize_raw(brand: Any) -> str:
    normalized = _strip_accents(_text(brand)).lower()
    normalized = normalized.replace("`", "'").replace("’", "'").replace("‘", "'")
    normalized = normalized.replace("&", " and ")
    for char in "-_/.,:;()[]{}":
        normalized = normalized.replace(char, " ")
    return " ".join(normalized.split())


RAW_ALIASES = {
    "saint laurent paris": "saint laurent",
    "yves saint laurent": "saint laurent",
    "ysl": "saint laurent",
    "ysl yves saint laurent": "saint laurent",
    "ysl saint laurent": "saint laurent",
    "lv": "louis vuitton",
    "d and g": "dolce gabbana",
    "dolce and gabbana": "dolce gabbana",
    "cdg": "comme des garcons",
    "comme des garcons homme": "comme des garcons",
    "isabel marant etoile": "isabel marant",
    "rl": "ralph lauren",
    "polo ralph lauren": "ralph lauren",
    "levis": "levi's",
    "levi strauss": "levi's",
    "tnf": "the north face",
    "north face": "the north face",
    "jordan": "air jordan",
    "nike jordan": "air jordan",
    "ck": "calvin klein",
    "tommy": "tommy hilfiger",
    "armani exchange": "a x armani exchange",
    "a x": "a x armani exchange",
    "hm": "h and m",
    "h m": "h and m",
    "pull bear": "pull and bear",
    "c a": "c and a",
    "no brand": "no name",
    "unbranded": "no name",
    "noname": "no name",
    "no name brand": "no name",
    "без бренда": "no name",
    "нет бренда": "no name",
    "ноунейм": "no name",
    "неизвестно": "unknown",
    "не указан": "not specified",
    "не указано": "not specified",
}

BRAND_ALIASES = {
    _normalize_raw(source): _normalize_raw(target)
    for source, target in RAW_ALIASES.items()
}


def normalize_brand_name(brand: Any) -> str:
    """Normalize brand spelling and collapse common aliases to one key."""
    raw = _normalize_raw(brand)
    return BRAND_ALIASES.get(raw, raw)


RAW_BRAND_GROUPS = [
    (
        "luxury",
        0.96,
        [
            "hermes",
            "chanel",
            "louis vuitton",
            "bottega veneta",
            "the row",
            "loro piana",
            "brunello cucinelli",
        ],
    ),
    (
        "luxury",
        0.94,
        [
            "saint laurent",
            "gucci",
            "prada",
            "dior",
            "fendi",
            "celine",
            "loewe",
            "valentino",
            "balenciaga",
        ],
    ),
    (
        "luxury",
        0.90,
        [
            "burberry",
            "givenchy",
            "versace",
            "dolce gabbana",
            "alexander mcqueen",
            "moncler",
            "miu miu",
            "maison margiela",
            "jil sander",
            "jacquemus",
            "vivienne westwood",
            "giorgio armani",
        ],
    ),
    (
        "premium",
        0.86,
        [
            "stone island",
            "rick owens",
            "raf simons",
            "comme des garcons",
            "yohji yamamoto",
            "issey miyake",
            "jean paul gaultier",
            "dries van noten",
            "acne studios",
            "max mara",
            "marni",
            "off white",
            "kenzo",
            "moschino",
            "dsquared2",
            "stella mccartney",
            "isabel marant",
            "etro",
            "roberto cavalli",
        ],
    ),
    (
        "premium",
        0.80,
        [
            "coach",
            "marc jacobs",
            "michael kors",
            "furla",
            "tory burch",
            "kate spade",
            "longchamp",
            "ganni",
            "sandro",
            "maje",
            "ba and sh",
            "reformation",
            "apc",
            "ami paris",
            "emporio armani",
            "armani",
        ],
    ),
    (
        "vintage_premium",
        0.84,
        [
            "carhartt",
            "levi's",
            "diesel",
            "ralph lauren",
            "lacoste",
            "tommy hilfiger",
            "fred perry",
            "barbour",
            "dr martens",
            "martens",
            "wrangler",
            "lee",
            "guess",
            "g star",
            "true religion",
            "ed hardy",
        ],
    ),
    (
        "sports_mass",
        0.86,
        [
            "the north face",
            "patagonia",
            "arc'teryx",
            "salomon",
            "air jordan",
        ],
    ),
    (
        "sports_mass",
        0.82,
        [
            "nike",
            "adidas",
            "new balance",
            "asics",
            "puma",
            "reebok",
            "converse",
            "vans",
            "under armour",
            "fila",
            "umbro",
            "kappa",
            "champion",
        ],
    ),
    (
        "mid_market",
        0.64,
        [
            "cos",
            "arket",
            "and other stories",
            "massimo dutti",
            "12 storeez",
            "gant",
            "benetton",
            "calvin klein",
            "a x armani exchange",
            "hugo boss",
            "boss",
            "banana republic",
            "j crew",
            "allsaints",
            "all saints",
        ],
    ),
    (
        "mid_market",
        0.54,
        [
            "mango",
            "gap",
            "esprit",
            "marks and spencer",
            "next",
            "reserved",
            "lime",
            "love republic",
            "zarina",
        ],
    ),
    (
        "mass",
        0.42,
        [
            "uniqlo",
            "zara",
            "weekday",
            "monki",
            "stradivarius",
            "pull and bear",
            "bershka",
            "asos",
            "urban outfitters",
        ],
    ),
    (
        "mass",
        0.32,
        [
            "h and m",
            "forever 21",
            "c and a",
            "new yorker",
            "boohoo",
            "fashion nova",
            "cotton on",
            "primark",
            "shein",
            "befree",
            "gloria jeans",
            "ostin",
            "o'stin",
            "oodji",
            "sela",
            "incity",
            "zolla",
            "modis",
            "tvoe",
            "твое",
            "снежная королева",
        ],
    ),
]


BRAND_DATA: Dict[str, Dict[str, Any]] = {}
for segment, score, brands in RAW_BRAND_GROUPS:
    for brand in brands:
        BRAND_DATA[normalize_brand_name(brand)] = {
            "segment": segment,
            "score": score,
            "confidence": 0.95,
        }


NO_NAME_KEYS = {"", "unknown", "not specified", "no name", "generic"}


def get_brand_segment(brand: Any) -> str:
    normalized = normalize_brand_name(brand)
    if normalized in NO_NAME_KEYS:
        return "no_name"
    return BRAND_DATA.get(normalized, {}).get("segment", "other_brand")


def get_brand_score(brand: Any) -> float:
    normalized = normalize_brand_name(brand)
    if normalized in {"", "unknown", "not specified"}:
        return 0.0
    if normalized == "no name":
        return NO_NAME_SCORE
    if normalized == "generic":
        return 0.08
    return float(BRAND_DATA.get(normalized, {}).get("score", UNKNOWN_BRAND_SCORE))


def get_brand_confidence(brand: Any) -> float:
    normalized = normalize_brand_name(brand)
    if normalized in {"", "unknown", "not specified"}:
        return 0.0
    if normalized in {"no name", "generic"}:
        return 0.8
    if normalized in BRAND_DATA:
        return float(BRAND_DATA[normalized]["confidence"])
    return 0.45
