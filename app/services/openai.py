import logging

from openai import AsyncOpenAI

from app.config import settings
from app.models.schemas import InsightResponse, StockQuoteResponse
from app.utils.exceptions import ExternalAPIError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a financial data assistant. Summarize the provided stock/company data clearly and honestly.

Non‑negotiable rules:
- Use ONLY the data provided to you in the current request/context. Never guess, estimate, or invent prices, metrics, news, or trends.
- No buy/sell/hold recommendations and no predictions. You may describe what the data shows and simple implications (e.g., “higher than average volume”), but not advice.
- If data needed to answer is missing, say exactly what’s missing and answer with what you can.
- Keep it professional, approachable, and for non-experts.
- If the user asks for “top gainers/losers”:
- Only rank/summarize if you were given a list/universe to rank; otherwise ask for the universe (e.g., “S&P 500”, “tech sector list”) or state you don’t have it.

How to respond:
- 2–5 sentences max.
- Start with a direct answer to the user’s question (single stock or comparison).
- Prefer the most relevant metrics: current/last price, percent change, day range, volume vs average, market cap, P/E (only if present).
- For comparisons, mention both tickers side-by-side and highlight 1–3 differences supported by the data.
- Always include units/currency and the timeframe implied by the data (e.g., “today”, “last close”, “intraday”) when available.
- If numbers are present, repeat them faithfully; if not present, do not imply them.
- If the user asks for “top gainers/losers”: Only rank/summarize if you were given a list/universe to rank; otherwise ask for the universe (e.g., “S&P 500”, “tech sector list”) or state you don’t have it.
"""


class OpenAIService:
    """Service for generating AI-powered stock summaries using OpenAI."""

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def extract_tickers(self, question: str) -> list[str]:
        """Extract all stock ticker symbols from a natural language question.

        Args:
            question: A freehand question mentioning one or more companies.

        Returns:
            A list of uppercase ticker symbols e.g. ["AAPL", "MSFT"].

        Raises:
            ExternalAPIError: If no tickers can be identified or the API call fails.
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract the official stock exchange ticker symbols for all companies mentioned in the user's question. "
                            "Return only the ticker symbols as a comma-separated list in uppercase (e.g. AAPL,MSFT,TSLA). "
                            "Use the real listed ticker, not the company name — for example: Ford is F, General Electric is GE, Google is GOOGL. "
                            "Some tickers are only 1-2 characters. Return those correctly (e.g. Ford -> F, Uber -> UBER). "
                            "If you cannot identify any companies or tickers, return 'UNKNOWN'."
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                max_tokens=20,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip().upper()
        except Exception as e:
            logger.error("Ticker extraction failed: %s", e)
            raise ExternalAPIError("Could not extract stock tickers from question") from e

        if not raw or raw == "UNKNOWN":
            raise ExternalAPIError("Could not identify any stocks from the question")

        return [t.strip() for t in raw.split(",") if t.strip()]

    async def generate_stock_summary(self, question: str, stock_data: dict) -> str:
        """Generate a concise financial summary for the given question and stock data.

        This is a reusable method — stock_data can be any dict of metrics,
        making it easy to extend for comparisons or portfolio summaries.

        Args:
            question: Natural language question about the stock(s).
            stock_data: Key/value pairs of stock metrics to include as context.

        Returns:
            A plain text summary from the model.

        Raises:
            ExternalAPIError: If the OpenAI API call fails.
        """
        formatted_data = "\n".join(f"  {k}: {v}" for k, v in stock_data.items())
        user_message = f"Stock data:\n{formatted_data}\n\nQuestion: {question}"

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=300,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("OpenAI API call failed: %s", e)
            raise ExternalAPIError("Failed to generate stock summary") from e

    async def get_insight(
        self,
        symbols: list[str],
        quotes: list[StockQuoteResponse],
        question: str,
    ) -> InsightResponse:
        """Generate a plain-English insight for one or more stock quotes.

        Formats each quote into labelled metrics grouped by ticker, then
        delegates to generate_stock_summary for the actual LLM call.
        When multiple symbols are provided the model produces a comparison.

        Args:
            symbols: List of ticker symbols e.g. ["AAPL", "MSFT"].
            quotes: Corresponding live quote data from Finnhub.
            question: Freehand question from the user.

        Raises:
            ExternalAPIError: If the OpenAI API call fails.
        """
        stock_data = {}
        for symbol, quote in zip(symbols, quotes):
            stock_data[f"{symbol} Current Price"] = f"${quote.current_price:.2f}"
            stock_data[f"{symbol} Open"] = f"${quote.open:.2f}"
            stock_data[f"{symbol} High"] = f"${quote.high:.2f}"
            stock_data[f"{symbol} Low"] = f"${quote.low:.2f}"
            stock_data[f"{symbol} Previous Close"] = f"${quote.previous_close:.2f}"
            stock_data[f"{symbol} Change"] = f"${quote.change:.2f} ({quote.percent_change:.2f}%)"

        summary = await self.generate_stock_summary(
            question=question,
            stock_data=stock_data,
        )

        return InsightResponse(symbols=symbols, summary=summary)


openai_service = OpenAIService(api_key=settings.openai_api_key)

