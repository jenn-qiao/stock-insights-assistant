class StockNotFoundError(Exception):
    def __init__(self, symbol: str):
        self.symbol = symbol
        super().__init__(f"Stock '{symbol}' not found")


class ExternalAPIError(Exception):
    def __init__(self, message: str = "External API error"):
        super().__init__(message)
