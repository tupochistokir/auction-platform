from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class LotQuestionnaire(BaseModel):
    brand: Optional[str] = "unknown"
    category: Optional[str] = "other"
    subcategory: Optional[str] = ""
    size: Optional[str] = "unknown"
    color: Optional[str] = "unknown"
    colors: Optional[List[str]] = []
    ai_analysis: Optional[Dict[str, Any]] = Field(default_factory=dict)
    material: Optional[str] = "unknown"
    style: Optional[str] = ""
    condition: Optional[str] = "good"
    has_tag: Optional[bool] = False
    estimated_age: Optional[int] = 0
    defects: Optional[str] = ""
    seller_comment: Optional[str] = ""
    views_count: Optional[int] = 0
    likes_count: Optional[int] = 0
    favorites_count: Optional[int] = 0
    bids_count: Optional[int] = 0
    offers_count: Optional[int] = 0
    bid_velocity: Optional[float] = 0.0
    start_price: Optional[float] = 0.0
    current_price: Optional[float] = 0.0
    status: Optional[str] = ""
    price_std: Optional[float] = 0.0
