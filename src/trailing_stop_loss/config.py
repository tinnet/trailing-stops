"""Configuration loading for trailing stop loss."""

import tomllib
from pathlib import Path
from typing import Any


def parse_ticker_with_price(ticker_str: str) -> tuple[str, float | None]:
    """Parse ticker string in format 'TICKER' or 'TICKER:PRICE'.

    Args:
        ticker_str: Ticker symbol, optionally with entry price (e.g., "AAPL:150.50")

    Returns:
        Tuple of (ticker, entry_price) where entry_price is None if not provided

    Raises:
        ValueError: If format is invalid or price is not positive

    Examples:
        >>> parse_ticker_with_price("AAPL")
        ('AAPL', None)
        >>> parse_ticker_with_price("AAPL:150.50")
        ('AAPL', 150.5)
        >>> parse_ticker_with_price("SHOP.TO:200")
        ('SHOP.TO', 200.0)
    """
    ticker_str = ticker_str.strip()

    if not ticker_str:
        raise ValueError("Ticker string cannot be empty")

    if ":" not in ticker_str:
        return (ticker_str.upper(), None)

    parts = ticker_str.split(":", 1)
    ticker = parts[0].strip()
    price_str = parts[1].strip()

    if not ticker:
        raise ValueError(f"Empty ticker in: {ticker_str}")

    if not price_str:
        raise ValueError(f"Empty price in: {ticker_str}")

    try:
        price = float(price_str)
    except ValueError as e:
        raise ValueError(f"Invalid price in '{ticker_str}': {price_str}") from e

    if price <= 0:
        raise ValueError(f"Entry price must be positive, got {price} in '{ticker_str}'")

    return (ticker.upper(), price)


class Config:
    """Configuration for stop-loss calculations."""

    def __init__(self, config_path: Path | str = "config.toml") -> None:
        """Initialize configuration from TOML file.

        Args:
            config_path: Path to the TOML configuration file.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If config file is invalid.
        """
        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from TOML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse config file: {e}") from e

    @property
    def tickers(self) -> list[str]:
        """Get list of ticker symbols to track."""
        return self._config.get("tickers", [])

    @property
    def tickers_with_prices(self) -> list[tuple[str, float | None]]:
        """Get list of (ticker, entry_price) tuples.

        Parses tickers in format 'TICKER' or 'TICKER:PRICE'.

        Returns:
            List of (ticker, entry_price) tuples where entry_price is None
            if not provided.

        Examples:
            >>> config._config = {"tickers": ["AAPL", "GOOGL:2800", "SHOP.TO:200"]}
            >>> config.tickers_with_prices
            [('AAPL', None), ('GOOGL', 2800.0), ('SHOP.TO', 200.0)]
        """
        ticker_strs = self._config.get("tickers", [])
        return [parse_ticker_with_price(t) for t in ticker_strs]

    @property
    def stop_loss_percentage(self) -> float:
        """Get default stop-loss percentage (0-100)."""
        return self._config.get("stop_loss_percentage", 5.0)

    @property
    def trailing_enabled(self) -> bool:
        """Check if trailing stop-loss is enabled by default."""
        return self._config.get("trailing_enabled", False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key."""
        return self._config.get(key, default)
