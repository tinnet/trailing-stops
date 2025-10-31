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
