"""Pydantic schemas for sentiment endpoints."""

from pydantic import BaseModel


class SentimentArticle(BaseModel):
    title: str
    publisher: str
    published: int
    link: str
    sentiment_score: float
    sentiment_label: str


class SentimentResponse(BaseModel):
    symbol: str
    overall_score: float
    overall_label: str
    article_count: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    articles: list[SentimentArticle]
    updated_at: int
