from fastapi import APIRouter

from app.models.schemas import InsightResponse, StockQuoteResponse
from app.services.finnhub import finnhub_service
from app.services.openai import openai_service

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/quote", response_model=StockQuoteResponse)
async def get_stock_quote(symbol: str) -> StockQuoteResponse:
    return await finnhub_service.get_quote(symbol)


@router.get("/insight", response_model=InsightResponse)
async def get_stock_insight(symbol: str) -> InsightResponse:
    quote = await finnhub_service.get_quote(symbol)
    return await openai_service.get_insight(symbol, quote)
