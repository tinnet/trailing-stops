"""Stock price fetching using yfinance."""

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

import pandas as pd
import yfinance as yf


@dataclass
class StockPrice:
    """Stock price information."""

    ticker: str
    current_price: float
    currency: str
    timestamp: datetime
    previous_close: float | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None
    entry_price: float | None = None  # User-provided entry price


class PriceFetcher:
    """Fetch stock prices using yfinance."""

    def __init__(self) -> None:
        """Initialize the price fetcher."""
        self._cache: dict[str, StockPrice] = {}

    def fetch_price(
        self, ticker: str, use_cache: bool = False, entry_price: float | None = None
    ) -> StockPrice:
        """Fetch current price for a ticker symbol.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'GOOGL').
            use_cache: Whether to use cached price if available.
            entry_price: Optional user-provided entry price.

        Returns:
            StockPrice object with current price information.

        Raises:
            ValueError: If ticker is invalid or price cannot be fetched.
        """
        if use_cache and ticker in self._cache:
            cached = self._cache[ticker]
            # Return a copy with updated entry price if provided
            if entry_price is not None:
                return replace(cached, entry_price=entry_price)
            return cached

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
                week_52_high=info.get("fiftyTwoWeekHigh"),
                week_52_low=info.get("fiftyTwoWeekLow"),
                entry_price=entry_price,
            )

            self._cache[ticker] = stock_price
            return stock_price

        except Exception as e:
            raise ValueError(f"Failed to fetch price for {ticker}: {e}") from e

    def fetch_multiple(
        self, tickers: list[str | tuple[str, float | None]], skip_errors: bool = True
    ) -> dict[str, StockPrice | Exception]:
        """Fetch prices for multiple tickers.

        Args:
            tickers: List of ticker symbols or (ticker, entry_price) tuples.
            skip_errors: If True, continue on errors; if False, raise on first error.

        Returns:
            Dictionary mapping tickers to StockPrice objects or Exceptions.
        """
        results: dict[str, StockPrice | Exception] = {}

        for item in tickers:
            # Handle both formats: "AAPL" or ("AAPL", 150.0)
            if isinstance(item, tuple):
                ticker, entry_price = item
            else:
                ticker = item
                entry_price = None

            try:
                results[ticker] = self.fetch_price(ticker, entry_price=entry_price)
            except Exception as e:
                if skip_errors:
                    results[ticker] = e
                else:
                    raise

        return results

    def clear_cache(self) -> None:
        """Clear the price cache."""
        self._cache.clear()

    def fetch_historical_data(
        self, ticker: str, start_date: date | str | None = None, end_date: date | str | None = None
    ) -> pd.DataFrame:
        """Fetch historical OHLC data for a ticker.

        Args:
            ticker: Stock ticker symbol.
            start_date: Start date for historical data. Defaults to 3 months ago.
            end_date: End date for historical data. Defaults to today.

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume and DatetimeIndex.

        Raises:
            ValueError: If ticker is invalid or data cannot be fetched.
        """
        try:
            stock = yf.Ticker(ticker)

            # Set default dates if not provided
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=90)).date()
            if end_date is None:
                end_date = datetime.now().date()

            # Convert to string format expected by yfinance
            start_str = start_date if isinstance(start_date, str) else start_date.strftime("%Y-%m-%d")
            end_str = end_date if isinstance(end_date, str) else end_date.strftime("%Y-%m-%d")

            # Fetch historical data
            history = stock.history(start=start_str, end=end_str)

            if history.empty:
                raise ValueError(f"No historical data available for {ticker}")

            return history

        except Exception as e:
            raise ValueError(f"Failed to fetch historical data for {ticker}: {e}") from e
