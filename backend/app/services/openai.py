import logging

from openai import AsyncOpenAI

from app.config import settings
from app.models.schemas import InsightResponse
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
                            "You are a stock ticker resolver. Given a user question, identify every publicly traded company mentioned and return their official NYSE/NASDAQ ticker symbols.\n\n"
                            "Rules:\n"
                            "1. The user may use a company name, brand, product, subsidiary, or a misspelling — always resolve to the parent listed entity's ticker.\n"
                            "2. Be typo-tolerant: 'appple', 'aPle', 'Appl', 'amazn', 'gogle', 'teslla' etc. should all be resolved to their correct ticker. Use phonetic and fuzzy matching.\n"
                            "3. Ticker symbols are case-insensitive. If the user types 'aapl', 'AAPL', or 'Aapl', treat them all as the ticker AAPL. Resolve directly without asking.\n"
                            "4. If the input looks like a ticker (1–5 letters, no spaces) but could also be a word or company name, prefer interpreting it as a ticker first. Only use SUGGEST if it genuinely could be either and you are not confident.\n"
                            "2. Known mappings (non-exhaustive):\n"
                            "   Stocks: Apple->AAPL, Google/Alphabet->GOOGL, Microsoft->MSFT, Amazon->AMZN, Tesla->TSLA, Meta/Facebook->META, Nvidia->NVDA, Netflix->NFLX, Spotify->SPOT, Ford->F, AMD->AMD, Palantir->PLTR, IonQ->IONQ, Uber->UBER, Airbnb->ABNB, Coinbase->COIN, Square/Block->XYZ, Shopify->SHOP, Visa->V, Mastercard->MA, JPMorgan->JPM, Goldman Sachs->GS, Disney->DIS, Nike->NKE, Starbucks->SBUX, Salesforce->CRM, Oracle->ORCL, Intel->INTC, Qualcomm->QCOM, PayPal->PYPL, Snap->SNAP, Twitter/X->X, Robinhood->HOOD, DoorDash->DASH, Lyft->LYFT, Rivian->RIVN, Lucid->LCID.\n"
                            "   ETFs/Indices: S&P 500/SPDR/SPY->SPY, Nasdaq/QQQ->QQQ, Dow Jones/DIA->DIA, Russell 2000/IWM->IWM, VIX/volatility index->VIX, Total market/VTI->VTI, Emerging markets/EEM->EEM, Gold/GLD->GLD, Oil/USO->USO, ARK Innovation/ARKK->ARKK.\n"
                            "5. If confident (including after fuzzy/typo matching), return a comma-separated list of tickers in uppercase (e.g. AAPL,MSFT).\n"
                            "6. If you think you know the company but want to confirm due to an unusual spelling, return: SUGGEST:<TICKER>:<company name as the user wrote it>  (e.g. SUGGEST:AAPL:appple)\n"
                            "7. Only return UNKNOWN if you genuinely have no idea what company the user is referring to."
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                max_tokens=60,
                temperature=0,
            )
            raw = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Ticker extraction failed: %s", e)
            raise ExternalAPIError("Could not extract stock tickers from question") from e

        upper = raw.upper()

        if not upper or upper == "UNKNOWN":
            raise ExternalAPIError(
                "Could not identify any stocks from the question. "
                "Try using a ticker symbol directly (e.g. SPOT for Spotify, AAPL for Apple)."
            )

        if upper.startswith("SUGGEST:"):
            parts = raw.split(":", 2)
            ticker = parts[1].strip().upper() if len(parts) > 1 else ""
            name = parts[2].strip() if len(parts) > 2 else ticker
            if ticker:
                raise ExternalAPIError(
                    f"Did you mean **{name}** ({ticker})? "
                    f"Try asking: \"How is {ticker} doing today?\""
                )
            raise ExternalAPIError(
                "Could not identify any stocks from the question. "
                "Try using a ticker symbol directly (e.g. AAPL for Apple)."
            )

        return [t.strip().upper() for t in raw.split(",") if t.strip()]

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



openai_service = OpenAIService(api_key=settings.openai_api_key)

