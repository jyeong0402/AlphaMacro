"""AI sentiment analysis schemas."""
from datetime import date
from pydantic import BaseModel

class SentimentResponse(BaseModel):
    ticker: str
    sentiment_score: float
    sentiment_label: str
    summary: list[str]
    model_status: str
    analyzed_count: int = 0
