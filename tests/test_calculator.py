"""Tests for stop-loss calculator."""

from datetime import datetime

import pytest

from trailing_stop_loss.calculator import StopLossCalculator, StopLossType
from trailing_stop_loss.fetcher import StockPrice


@pytest.fixture
def sample_stock_price() -> StockPrice:
    """Create a sample stock price for testing."""
    return StockPrice(
        ticker="AAPL",
        current_price=150.0,
        currency="USD",
        timestamp=datetime.now(),
        previous_close=148.0,
    )


@pytest.fixture
def calculator() -> StopLossCalculator:
    """Create a fresh calculator instance."""
    return StopLossCalculator()


def test_simple_stop_loss(calculator: StopLossCalculator, sample_stock_price: StockPrice) -> None:
    """Test simple stop-loss calculation."""
    result = calculator.calculate_simple(sample_stock_price, 5.0)

    assert result.ticker == "AAPL"
    assert result.current_price == 150.0
    assert result.stop_loss_price == pytest.approx(142.5)  # 150 * 0.95
    assert result.stop_loss_type == StopLossType.SIMPLE
    assert result.percentage == 5.0
    assert result.dollar_risk == pytest.approx(7.5)


def test_simple_stop_loss_different_percentage(
    calculator: StopLossCalculator, sample_stock_price: StockPrice
) -> None:
    """Test simple stop-loss with different percentage."""
    result = calculator.calculate_simple(sample_stock_price, 10.0)

    assert result.stop_loss_price == pytest.approx(135.0)  # 150 * 0.90
    assert result.dollar_risk == pytest.approx(15.0)


def test_trailing_stop_loss(calculator: StopLossCalculator, sample_stock_price: StockPrice) -> None:
    """Test trailing stop-loss calculation."""
    result = calculator.calculate_trailing(sample_stock_price, 5.0)

    assert result.ticker == "AAPL"
    assert result.current_price == 150.0
    assert result.stop_loss_price == pytest.approx(142.5)
    assert result.stop_loss_type == StopLossType.TRAILING


def test_trailing_stop_loss_tracks_high(
    calculator: StopLossCalculator, sample_stock_price: StockPrice
) -> None:
    """Test that trailing stop-loss tracks high water mark."""
    # First calculation at 150
    result1 = calculator.calculate_trailing(sample_stock_price, 5.0)
    assert result1.stop_loss_price == pytest.approx(142.5)

    # Price goes up to 160
    sample_stock_price.current_price = 160.0
    result2 = calculator.calculate_trailing(sample_stock_price, 5.0)
    assert result2.stop_loss_price == pytest.approx(152.0)  # 160 * 0.95

    # Price drops to 155, but stop-loss stays at high water mark
    sample_stock_price.current_price = 155.0
    result3 = calculator.calculate_trailing(sample_stock_price, 5.0)
    assert result3.stop_loss_price == pytest.approx(152.0)  # Still based on 160


def test_calculate_method(calculator: StopLossCalculator, sample_stock_price: StockPrice) -> None:
    """Test the unified calculate method."""
    # Simple mode
    result_simple = calculator.calculate(sample_stock_price, 5.0, trailing=False)
    assert result_simple.stop_loss_type == StopLossType.SIMPLE

    # Trailing mode
    result_trailing = calculator.calculate(sample_stock_price, 5.0, trailing=True)
    assert result_trailing.stop_loss_type == StopLossType.TRAILING


def test_invalid_percentage(calculator: StopLossCalculator, sample_stock_price: StockPrice) -> None:
    """Test that invalid percentages raise errors."""
    with pytest.raises(ValueError):
        calculator.calculate_simple(sample_stock_price, 0.0)

    with pytest.raises(ValueError):
        calculator.calculate_simple(sample_stock_price, 100.0)

    with pytest.raises(ValueError):
        calculator.calculate_simple(sample_stock_price, -5.0)


def test_reset_high_water_mark(
    calculator: StopLossCalculator, sample_stock_price: StockPrice
) -> None:
    """Test resetting high water mark."""
    # Set initial high water mark
    calculator.calculate_trailing(sample_stock_price, 5.0)
    assert calculator.get_high_water_mark("AAPL") == 150.0

    # Reset specific ticker
    calculator.reset_high_water_mark("AAPL")
    assert calculator.get_high_water_mark("AAPL") is None

    # Set multiple high water marks
    calculator.calculate_trailing(sample_stock_price, 5.0)
    other_stock = StockPrice("GOOGL", 200.0, "USD", datetime.now())
    calculator.calculate_trailing(other_stock, 5.0)

    # Reset all
    calculator.reset_high_water_mark()
    assert calculator.get_high_water_mark("AAPL") is None
    assert calculator.get_high_water_mark("GOOGL") is None


def test_formatted_output(calculator: StopLossCalculator, sample_stock_price: StockPrice) -> None:
    """Test formatted output properties."""
    result = calculator.calculate_simple(sample_stock_price, 5.0)

    assert result.formatted_percentage == "5.00%"
    assert result.formatted_risk == "USD 7.50"
