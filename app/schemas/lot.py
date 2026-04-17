from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.questionnaire import LotQuestionnaire


class LotCreate(BaseModel):
    title: str
    start_price: float
    description: str
    image_url: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
    questionnaire: LotQuestionnaire