"""Tests for configuration loading."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from trailing_stop_loss.config import Config, parse_ticker_with_price


def test_config_loading() -> None:
    """Test loading a valid config file."""
    config_content = """
tickers = ["AAPL", "GOOGL"]
stop_loss_percentage = 7.5
trailing_enabled = true
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config_path = Path(f.name)

    try:
        config = Config(config_path)
        assert config.tickers == ["AAPL", "GOOGL"]
        assert config.stop_loss_percentage == 7.5
        assert config.trailing_enabled is True
    finally:
        config_path.unlink()


def test_config_defaults() -> None:
    """Test default values when fields are missing."""
    config_content = """
# Minimal config
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config_path = Path(f.name)

    try:
        config = Config(config_path)
        assert config.tickers == []
        assert config.stop_loss_percentage == 5.0
        assert config.trailing_enabled is False
    finally:
        config_path.unlink()


def test_config_file_not_found() -> None:
    """Test error when config file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        Config("nonexistent.toml")


def test_config_invalid_toml() -> None:
    """Test error when config file is invalid TOML."""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("invalid [ toml content")
        f.flush()
        config_path = Path(f.name)

    try:
        with pytest.raises(ValueError):
            Config(config_path)
    finally:
        config_path.unlink()


# Tests for parse_ticker_with_price()


def test_parse_ticker_plain() -> None:
    """Test parsing plain ticker without price."""
    ticker, price = parse_ticker_with_price("AAPL")
    assert ticker == "AAPL"
    assert price is None


def test_parse_ticker_with_price_simple() -> None:
    """Test parsing ticker with price."""
    ticker, price = parse_ticker_with_price("AAPL:150")
    assert ticker == "AAPL"
    assert price == 150.0


def test_parse_ticker_with_decimal_price() -> None:
    """Test parsing ticker with decimal price."""
    ticker, price = parse_ticker_with_price("AAPL:150.50")
    assert ticker == "AAPL"
    assert price == 150.50


def test_parse_ticker_canadian() -> None:
    """Test parsing Canadian ticker with price."""
    ticker, price = parse_ticker_with_price("SHOP.TO:200")
    assert ticker == "SHOP.TO"
    assert price == 200.0


def test_parse_ticker_lowercase() -> None:
    """Test that ticker is converted to uppercase."""
    ticker, price = parse_ticker_with_price("aapl:150")
    assert ticker == "AAPL"
    assert price == 150.0


def test_parse_ticker_with_whitespace() -> None:
    """Test parsing with whitespace."""
    ticker, price = parse_ticker_with_price("  AAPL:150  ")
    assert ticker == "AAPL"
    assert price == 150.0


def test_parse_ticker_empty_string() -> None:
    """Test error on empty string."""
    with pytest.raises(ValueError, match="Ticker string cannot be empty"):
        parse_ticker_with_price("")


def test_parse_ticker_empty_price() -> None:
    """Test error on empty price."""
    with pytest.raises(ValueError, match="Empty price in: AAPL:"):
        parse_ticker_with_price("AAPL:")


def test_parse_ticker_empty_ticker() -> None:
    """Test error on empty ticker."""
    with pytest.raises(ValueError, match="Empty ticker in: :150"):
        parse_ticker_with_price(":150")


def test_parse_ticker_invalid_price() -> None:
    """Test error on invalid price."""
    with pytest.raises(ValueError, match="Invalid price in 'AAPL:abc': abc"):
        parse_ticker_with_price("AAPL:abc")


def test_parse_ticker_negative_price() -> None:
    """Test error on negative price."""
    with pytest.raises(ValueError, match="Entry price must be positive, got -150.0"):
        parse_ticker_with_price("AAPL:-150")


def test_parse_ticker_zero_price() -> None:
    """Test error on zero price."""
    with pytest.raises(ValueError, match="Entry price must be positive, got 0.0"):
        parse_ticker_with_price("AAPL:0")


def test_parse_ticker_multiple_colons() -> None:
    """Test parsing ticker with multiple colons (splits on first)."""
    # We split on the first colon only, so "ABC:DEF:150" becomes ticker="ABC", price="DEF:150"
    # This will raise ValueError because "DEF:150" is not a valid float
    with pytest.raises(ValueError, match="Invalid price"):
        parse_ticker_with_price("ABC:DEF:150")


# Tests for Config.tickers_with_prices property


def test_config_tickers_with_prices() -> None:
    """Test tickers_with_prices property with mixed format."""
    config_content = """
tickers = ["AAPL:150", "GOOGL:2800", "SHOP.TO:200", "NVDA"]
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config_path = Path(f.name)

    try:
        config = Config(config_path)
        result = config.tickers_with_prices
        assert len(result) == 4
        assert result[0] == ("AAPL", 150.0)
        assert result[1] == ("GOOGL", 2800.0)
        assert result[2] == ("SHOP.TO", 200.0)
        assert result[3] == ("NVDA", None)
    finally:
        config_path.unlink()


def test_config_tickers_with_prices_all_plain() -> None:
    """Test tickers_with_prices with all plain tickers."""
    config_content = """
tickers = ["AAPL", "GOOGL", "NVDA"]
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config_path = Path(f.name)

    try:
        config = Config(config_path)
        result = config.tickers_with_prices
        assert len(result) == 3
        assert result[0] == ("AAPL", None)
        assert result[1] == ("GOOGL", None)
        assert result[2] == ("NVDA", None)
    finally:
        config_path.unlink()


def test_config_tickers_with_prices_all_with_prices() -> None:
    """Test tickers_with_prices with all tickers having prices."""
    config_content = """
tickers = ["AAPL:150.50", "GOOGL:2800", "NVDA:900.25"]
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config_path = Path(f.name)

    try:
        config = Config(config_path)
        result = config.tickers_with_prices
        assert len(result) == 3
        assert result[0] == ("AAPL", 150.50)
        assert result[1] == ("GOOGL", 2800.0)
        assert result[2] == ("NVDA", 900.25)
    finally:
        config_path.unlink()


def test_config_tickers_with_prices_empty() -> None:
    """Test tickers_with_prices with empty tickers list."""
    config_content = """
tickers = []
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config_path = Path(f.name)

    try:
        config = Config(config_path)
        result = config.tickers_with_prices
        assert result == []
    finally:
        config_path.unlink()


def test_config_backward_compatibility() -> None:
    """Test that old configs without prices still work."""
    config_content = """
tickers = ["AAPL", "GOOGL"]
stop_loss_percentage = 5.0
trailing_enabled = false
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config_path = Path(f.name)

    try:
        config = Config(config_path)
        # Old property should still work
        assert config.tickers == ["AAPL", "GOOGL"]
        # New property should also work
        result = config.tickers_with_prices
        assert result == [("AAPL", None), ("GOOGL", None)]
    finally:
        config_path.unlink()
