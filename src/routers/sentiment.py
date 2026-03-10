"""Sentiment analysis API endpoints."""

from fastapi import APIRouter

from src.services.sentiment import get_symbol_sentiment

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])


@router.get("/{symbol}")
def symbol_sentiment(symbol: str):
    """Return NLP sentiment analysis for a symbol's recent news."""
    return get_symbol_sentiment(symbol.upper())
