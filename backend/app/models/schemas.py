from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class StockQuoteResponse(BaseModel):
    """Maps Finnhub's single-letter quote fields to readable names.

    Finnhub returns abbreviated keys (c, h, l, o, pc, d, dp) — the aliases
    here let Pydantic parse them directly into human-readable field names.
    """

    symbol: str
    current_price: float = Field(alias="c")
    high: float = Field(alias="h")
    low: float = Field(alias="l")
    open: float = Field(alias="o")
    previous_close: float = Field(alias="pc")
    change: float = Field(alias="d")       # dollar change from previous close
    percent_change: float = Field(alias="dp")  # percentage change from previous close

    model_config = {"populate_by_name": True}


class CompanyProfileResponse(BaseModel):
    """Maps Finnhub's camelCase profile fields to readable names."""

    name: str
    ticker: str
    exchange: str
    industry: str = Field(alias="finnhubIndustry")
    market_cap: float = Field(alias="marketCapitalization")  # in millions USD

    model_config = {"populate_by_name": True}


class CandleResponse(BaseModel):
    """Historical daily price data for a symbol over a date range.

    Only the fields we actually use are stored:
    - closes: used to calculate start/end price and % change over the period
    - highs/lows: used to show the period's price range
    """

    symbol: str
    closes: list[float]
    highs: list[float]
    lows: list[float]


class InsightResponse(BaseModel):
    """The final response returned to the frontend."""

    symbols: list[str]  # tickers that were analysed
    summary: str        # AI-generated plain-English summary


