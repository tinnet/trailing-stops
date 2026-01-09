"""Tests for price fetcher."""

import pytest

from trailing_stop_loss.fetcher import PriceFetcher, StockPrice


@pytest.fixture
def fetcher() -> PriceFetcher:
    """Create a fresh fetcher instance."""
    return PriceFetcher()


def test_fetch_price_valid_ticker(fetcher: PriceFetcher) -> None:
    """Test fetching price for a valid ticker.

    Note: This is an integration test that makes real API calls.
    """
    stock_price = fetcher.fetch_price("AAPL")

    assert isinstance(stock_price, StockPrice)
    assert stock_price.ticker == "AAPL"
    assert stock_price.current_price > 0
    assert stock_price.currency in ["USD", "usd"]
    assert stock_price.timestamp is not None


def test_fetch_price_invalid_ticker(fetcher: PriceFetcher) -> None:
    """Test fetching price for an invalid ticker."""
    with pytest.raises(ValueError):
        fetcher.fetch_price("NOTAREALTICKERXYZ123")


def test_fetch_price_caching(fetcher: PriceFetcher) -> None:
    """Test that caching works correctly."""
    # First fetch (not cached)
    price1 = fetcher.fetch_price("AAPL")

    # Second fetch with cache enabled
    price2 = fetcher.fetch_price("AAPL", use_cache=True)

    # Should be the same object from cache
    assert price1.ticker == price2.ticker
    assert price1.current_price == price2.current_price
    assert price1.timestamp == price2.timestamp


def test_fetch_multiple_tickers(fetcher: PriceFetcher) -> None:
    """Test fetching multiple tickers."""
    tickers = ["AAPL", "GOOGL", "MSFT"]
    results = fetcher.fetch_multiple(tickers, skip_errors=True)

    assert len(results) == 3
    for ticker in tickers:
        assert ticker in results
        # Should be either StockPrice or Exception
        assert isinstance(results[ticker], (StockPrice, Exception))


def test_fetch_multiple_with_invalid(fetcher: PriceFetcher) -> None:
    """Test fetching multiple tickers with some invalid ones."""
    tickers = ["AAPL", "NOTAREALTICKER123"]
    results = fetcher.fetch_multiple(tickers, skip_errors=True)

    assert len(results) == 2
    assert isinstance(results["AAPL"], StockPrice)
    assert isinstance(results["NOTAREALTICKER123"], Exception)


def test_fetch_multiple_no_skip_errors(fetcher: PriceFetcher) -> None:
    """Test that errors are raised when skip_errors=False."""
    tickers = ["AAPL", "NOTAREALTICKER123"]

    with pytest.raises(ValueError):
        fetcher.fetch_multiple(tickers, skip_errors=False)


def test_clear_cache(fetcher: PriceFetcher) -> None:
    """Test clearing the cache."""
    # Fetch and cache
    fetcher.fetch_price("AAPL")
    assert "AAPL" in fetcher._cache

    # Clear cache
    fetcher.clear_cache()
    assert len(fetcher._cache) == 0


def test_ticker_normalization(fetcher: PriceFetcher) -> None:
    """Test that tickers are normalized to uppercase."""
    stock_price = fetcher.fetch_price("aapl")
    assert stock_price.ticker == "AAPL"


def test_fetch_52week_high_low(fetcher: PriceFetcher) -> None:
    """Test that 52-week high and low are fetched.

    Note: This is an integration test that makes real API calls.
    """
    stock_price = fetcher.fetch_price("AAPL")

    # Check that 52-week high/low are present (should be numbers or None)
    assert stock_price.week_52_high is None or isinstance(stock_price.week_52_high, (int, float))
    assert stock_price.week_52_low is None or isinstance(stock_price.week_52_low, (int, float))

    # If they exist, verify they're reasonable
    if stock_price.week_52_high is not None:
        assert stock_price.week_52_high > 0
        # 52-week high should be >= current price (or close to it)
        # Allow some tolerance for intraday changes
        assert stock_price.week_52_high >= stock_price.current_price * 0.5

    if stock_price.week_52_low is not None:
        assert stock_price.week_52_low > 0
        # 52-week low should be <= current price (or close to it)
        assert stock_price.week_52_low <= stock_price.current_price * 2.0


# Tests for entry_price functionality


def test_fetch_price_with_entry_price(fetcher: PriceFetcher) -> None:
    """Test fetching price with entry price."""
    stock_price = fetcher.fetch_price("AAPL", entry_price=150.0)

    assert isinstance(stock_price, StockPrice)
    assert stock_price.ticker == "AAPL"
    assert stock_price.current_price > 0
    assert stock_price.entry_price == 150.0


def test_fetch_price_without_entry_price(fetcher: PriceFetcher) -> None:
    """Test fetching price without entry price (default behavior)."""
    stock_price = fetcher.fetch_price("AAPL")

    assert isinstance(stock_price, StockPrice)
    assert stock_price.entry_price is None


def test_fetch_multiple_with_entry_prices(fetcher: PriceFetcher) -> None:
    """Test fetching multiple tickers with entry prices (tuple format)."""
    tickers = [("AAPL", 150.0), ("GOOGL", 2800.0)]
    results = fetcher.fetch_multiple(tickers, skip_errors=True)

    assert len(results) == 2
    assert isinstance(results["AAPL"], StockPrice)
    assert results["AAPL"].entry_price == 150.0
    assert isinstance(results["GOOGL"], StockPrice)
    assert results["GOOGL"].entry_price == 2800.0


def test_fetch_multiple_mixed_format(fetcher: PriceFetcher) -> None:
    """Test fetching with mixed format (some with entry prices, some without)."""
    tickers: list[str | tuple[str, float]] = [("AAPL", 150.0), "GOOGL", ("MSFT", 400.0)]
    results = fetcher.fetch_multiple(tickers, skip_errors=True)

    assert len(results) == 3
    assert isinstance(results["AAPL"], StockPrice)
    assert results["AAPL"].entry_price == 150.0
    assert isinstance(results["GOOGL"], StockPrice)
    assert results["GOOGL"].entry_price is None
    assert isinstance(results["MSFT"], StockPrice)
    assert results["MSFT"].entry_price == 400.0


def test_fetch_price_entry_price_with_cache(fetcher: PriceFetcher) -> None:
    """Test that entry price is updated when using cache."""
    # First fetch without entry price
    price1 = fetcher.fetch_price("AAPL")
    assert price1.entry_price is None

    # Second fetch with cache and entry price
    price2 = fetcher.fetch_price("AAPL", use_cache=True, entry_price=150.0)
    assert price2.entry_price == 150.0

    # Both should reference the same cached object
    assert price1.ticker == price2.ticker


def test_entry_price_persists_in_stock_price(fetcher: PriceFetcher) -> None:
    """Test that entry price flows through the StockPrice object."""
    stock_price = fetcher.fetch_price("AAPL", entry_price=175.50)

    # Verify all expected fields are present
    assert stock_price.ticker == "AAPL"
    assert stock_price.current_price > 0
    assert stock_price.currency in ["USD", "usd"]
    assert stock_price.timestamp is not None
    assert stock_price.entry_price == 175.50


def test_fetch_multiple_all_plain_tickers(fetcher: PriceFetcher) -> None:
    """Test backward compatibility with plain ticker list."""
    tickers = ["AAPL", "GOOGL"]
    results = fetcher.fetch_multiple(tickers, skip_errors=True)

    assert len(results) == 2
    for ticker in tickers:
        assert isinstance(results[ticker], StockPrice)
        assert results[ticker].entry_price is None
