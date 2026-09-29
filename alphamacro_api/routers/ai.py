"""AI sentiment endpoints under /api/v1/ai."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import FinancialNews
from ..schemas.ai import SentimentResponse
from ..services.ai_engine import SentimentEngine
from ..services.collector import fetch_sec_filings
from ..core.config import settings
router = APIRouter()
engine = SentimentEngine(settings.finbert_model, settings.finbert_enabled)

@router.get("/sentiment/{ticker}", response_model=SentimentResponse)
def sentiment(ticker: str, db: Session = Depends(get_db)):
    news = db.scalars(select(FinancialNews).where(FinancialNews.ticker == ticker.upper()).order_by(FinancialNews.published_at.desc())).all()
    texts = [f"{n.title} {n.summary or ''}" for n in news]
    score, label, summary = engine.analyze(texts)
    return SentimentResponse(ticker=ticker.upper(), sentiment_score=score, sentiment_label=label,
                             summary=summary, model_status=engine.status, analyzed_count=len(texts))

@router.get("/news/{ticker}")
def news(ticker: str, limit: int = Query(default=8, ge=1, le=50), db: Session = Depends(get_db)):
    articles = db.scalars(
        select(FinancialNews)
        .where(FinancialNews.ticker == ticker.upper())
        .order_by(FinancialNews.published_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "title": article.title,
            "source": article.source,
            "url": article.url,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "sentiment_score": article.sentiment_score,
            "summary": article.summary,
        }
        for article in articles
    ]


@router.get("/sec/{ticker}")
async def sec_filings(ticker: str, start: str = Query(...), end: str = Query(...),
                      limit: int = Query(default=20, ge=1, le=50)):
    try:
        from datetime import date
        filings = await fetch_sec_filings(settings.sec_user_agent, ticker, date.fromisoformat(start),
                                          date.fromisoformat(end), limit)
        texts = [f"{item['title']} {item['form']}" for item in filings]
        score, label, summary = engine.analyze(texts)
        return {"ticker": ticker.upper(), "filings": filings, "sentiment_score": score,
                "sentiment_label": label, "summary": summary, "model_status": engine.status}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
