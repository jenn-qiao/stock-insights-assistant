# StockNotFoundError is raised when a ticker exists but Finnhub doesn't recognise it
# ExternalAPIError is raised when a request to Finnhub or OpenAI fails
# Keeping them separate means the frontend can show different messages for each case

class StockNotFoundError(Exception):
    def __init__(self, symbol: str):
        self.symbol = symbol
        super().__init__(f"Stock '{symbol}' not found")


class ExternalAPIError(Exception):
    def __init__(self, message: str = "External API error"):
        super().__init__(message)
