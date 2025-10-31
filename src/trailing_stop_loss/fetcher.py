"""Stock price fetching using yfinance."""

from dataclasses import dataclass
from datetime import datetime

import yfinance as yf


@dataclass
class StockPrice:
    """Stock price information."""

    ticker: str
    current_price: float
    currency: str
    timestamp: datetime
    previous_close: float | None = None


class PriceFetcher:
    """Fetch stock prices using yfinance."""

    def __init__(self) -> None:
        """Initialize the price fetcher."""
        self._cache: dict[str, StockPrice] = {}

    def fetch_price(self, ticker: str, use_cache: bool = False) -> StockPrice:
        """Fetch current price for a ticker symbol.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'GOOGL').
            use_cache: Whether to use cached price if available.

        Returns:
            StockPrice object with current price information.

        Raises:
            ValueError: If ticker is invalid or price cannot be fetched.
        """
        if use_cache and ticker in self._cache:
            return self._cache[ticker]

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Get current price from various possible fields
            current_price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )

            if current_price is None:
                raise ValueError(f"Could not fetch price for {ticker}")

            stock_price = StockPrice(
                ticker=ticker.upper(),
                current_price=float(current_price),
                currency=info.get("currency", "USD"),
                timestamp=datetime.now(),
                previous_close=info.get("previousClose"),
            )

            self._cache[ticker] = stock_price
            return stock_price

        except Exception as e:
            raise ValueError(f"Failed to fetch price for {ticker}: {e}") from e

    def fetch_multiple(
        self, tickers: list[str], skip_errors: bool = True
    ) -> dict[str, StockPrice | Exception]:
        """Fetch prices for multiple tickers.

        Args:
            tickers: List of ticker symbols.
            skip_errors: If True, continue on errors; if False, raise on first error.

        Returns:
            Dictionary mapping tickers to StockPrice objects or Exceptions.
        """
        results: dict[str, StockPrice | Exception] = {}

        for ticker in tickers:
            try:
                results[ticker] = self.fetch_price(ticker)
            except Exception as e:
                if skip_errors:
                    results[ticker] = e
                else:
                    raise

        return results

    def clear_cache(self) -> None:
        """Clear the price cache."""
        self._cache.clear()
