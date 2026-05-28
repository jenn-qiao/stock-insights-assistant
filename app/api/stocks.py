import asyncio

from fastapi import APIRouter

from app.models.schemas import CompanyProfileResponse, InsightResponse, StockQuoteResponse
from app.services.finnhub import finnhub_service
from app.services.openai import openai_service

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/quote", response_model=StockQuoteResponse)
async def get_stock_quote(symbol: str) -> StockQuoteResponse:
    return await finnhub_service.get_quote(symbol)


@router.get("/profile", response_model=CompanyProfileResponse)
async def get_company_profile(symbol: str) -> CompanyProfileResponse:
    return await finnhub_service.get_company_profile(symbol)


@router.get("/insight", response_model=InsightResponse)
async def get_stock_insight(question: str) -> InsightResponse:
    symbols = await openai_service.extract_tickers(question)
    quotes = await asyncio.gather(*[finnhub_service.get_quote(s) for s in symbols])
    return await openai_service.get_insight(symbols, list(quotes), question=question)
