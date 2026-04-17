from typing import Optional, List
from pydantic import BaseModel


class LotQuestionnaire(BaseModel):
    brand: Optional[str] = "unknown"
    category: Optional[str] = "other"
    subcategory: Optional[str] = ""
    size: Optional[str] = "unknown"
    color: Optional[str] = "unknown"
    colors: Optional[List[str]] = []
    material: Optional[str] = "unknown"
    style: Optional[str] = ""
    condition: Optional[str] = "good"
    has_tag: Optional[bool] = False
    estimated_age: Optional[int] = 0
    defects: Optional[str] = ""
    seller_comment: Optional[str] = ""