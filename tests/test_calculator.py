"""Tests for stop-loss calculator."""

from datetime import datetime

import pandas as pd
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


def test_calculate_atr() -> None:
    """Test ATR calculation with known data."""
    # Create test data with known True Range values
    data = {
        "High": [105.0, 107.0, 106.0, 108.0, 110.0, 109.0, 111.0, 112.0, 113.0, 114.0,
                 115.0, 116.0, 117.0, 118.0, 119.0],
        "Low": [99.0, 101.0, 100.0, 102.0, 104.0, 103.0, 105.0, 106.0, 107.0, 108.0,
                109.0, 110.0, 111.0, 112.0, 113.0],
        "Close": [103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 109.0, 110.0, 111.0, 112.0,
                  113.0, 114.0, 115.0, 116.0, 117.0],
    }
    dates = pd.date_range("2024-01-01", periods=15)
    df = pd.DataFrame(data, index=dates)

    atr = StopLossCalculator.calculate_atr(df, period=14)

    # ATR should be positive
    assert atr > 0
    # For this data, ATR should be reasonable
    assert 4.0 < atr < 8.0


def test_calculate_atr_insufficient_data() -> None:
    """Test ATR calculation with insufficient data."""
    data = {
        "High": [105.0, 107.0],
        "Low": [99.0, 101.0],
        "Close": [103.0, 105.0],
    }
    dates = pd.date_range("2024-01-01", periods=2)
    df = pd.DataFrame(data, index=dates)

    with pytest.raises(ValueError, match="Insufficient data"):
        StopLossCalculator.calculate_atr(df, period=14)


def test_calculate_atr_missing_columns() -> None:
    """Test ATR calculation with missing columns."""
    data = {
        "High": [105.0, 107.0, 106.0],
        "Low": [99.0, 101.0, 100.0],
        # Missing Close column
    }
    dates = pd.date_range("2024-01-01", periods=3)
    df = pd.DataFrame(data, index=dates)

    with pytest.raises(ValueError, match="Missing required columns"):
        StopLossCalculator.calculate_atr(df, period=2)


def test_calculate_atr_stop_loss(
    calculator: StopLossCalculator, sample_stock_price: StockPrice
) -> None:
    """Test ATR-based stop-loss calculation."""
    atr = 10.0  # $10 ATR
    result = calculator.calculate_atr_stop_loss(sample_stock_price, 5.0, atr, atr_multiplier=2.0)

    # Stop-loss should be current price - (ATR × multiplier)
    expected_stop = 150.0 - (10.0 * 2.0)
    assert result.stop_loss_price == pytest.approx(expected_stop)
    assert result.stop_loss_type == StopLossType.ATR
    assert result.dollar_risk == pytest.approx(20.0)


def test_calculate_atr_stop_loss_different_multiplier(
    calculator: StopLossCalculator, sample_stock_price: StockPrice
) -> None:
    """Test ATR stop-loss with different multiplier."""
    atr = 10.0
    result = calculator.calculate_atr_stop_loss(sample_stock_price, 5.0, atr, atr_multiplier=1.5)

    expected_stop = 150.0 - (10.0 * 1.5)
    assert result.stop_loss_price == pytest.approx(expected_stop)
    assert result.dollar_risk == pytest.approx(15.0)


def test_calculate_atr_stop_loss_invalid_multiplier(
    calculator: StopLossCalculator, sample_stock_price: StockPrice
) -> None:
    """Test ATR stop-loss with invalid multiplier."""
    with pytest.raises(ValueError, match="ATR multiplier must be positive"):
        calculator.calculate_atr_stop_loss(sample_stock_price, 5.0, 10.0, atr_multiplier=0.0)


def test_simple_stop_loss_with_base_price(
    calculator: StopLossCalculator, sample_stock_price: StockPrice
) -> None:
    """Test simple stop-loss calculation with base price (52-week high mode)."""
    # 52-week high is $180, current price is $150
    result = calculator.calculate_simple(sample_stock_price, 10.0, base_price=180.0)

    # Stop-loss should be 10% below base price (180)
    assert result.stop_loss_price == pytest.approx(162.0)  # 180 * 0.90
    # Dollar risk is still relative to current price
    assert result.dollar_risk == pytest.approx(-12.0)  # 150 - 162 (negative when current < stop)
    # Base price should be stored in result
    assert result.week_52_high == 180.0
    assert result.stop_loss_type == StopLossType.SIMPLE


def test_atr_stop_loss_with_base_price(
    calculator: StopLossCalculator, sample_stock_price: StockPrice
) -> None:
    """Test ATR stop-loss calculation with base price (52-week high mode)."""
    # 52-week high is $180, current price is $150, ATR is $10
    atr = 10.0
    result = calculator.calculate_atr_stop_loss(
        sample_stock_price, 5.0, atr, atr_multiplier=2.0, base_price=180.0
    )

    # Stop-loss should be base price - (ATR × multiplier)
    expected_stop = 180.0 - (10.0 * 2.0)
    assert result.stop_loss_price == pytest.approx(expected_stop)  # 160.0
    # Dollar risk is still relative to current price
    assert result.dollar_risk == pytest.approx(-10.0)  # 150 - 160
    # Base price should be stored in result
    assert result.week_52_high == 180.0
    assert result.stop_loss_type == StopLossType.ATR


def test_simple_stop_loss_without_base_price_default(
    calculator: StopLossCalculator, sample_stock_price: StockPrice
) -> None:
    """Test that simple stop-loss without base_price behaves as before."""
    result = calculator.calculate_simple(sample_stock_price, 10.0)

    # Stop-loss should be based on current price
    assert result.stop_loss_price == pytest.approx(135.0)  # 150 * 0.90
    assert result.dollar_risk == pytest.approx(15.0)  # 150 - 135
    assert result.week_52_high is None


def test_atr_stop_loss_without_base_price_default(
    calculator: StopLossCalculator, sample_stock_price: StockPrice
) -> None:
    """Test that ATR stop-loss without base_price behaves as before."""
    atr = 10.0
    result = calculator.calculate_atr_stop_loss(sample_stock_price, 5.0, atr, atr_multiplier=2.0)

    # Stop-loss should be based on current price
    expected_stop = 150.0 - (10.0 * 2.0)
    assert result.stop_loss_price == pytest.approx(expected_stop)  # 130.0
    assert result.dollar_risk == pytest.approx(20.0)  # 150 - 130
    assert result.week_52_high is None


def test_guidance_when_stop_above_current(
    calculator: StopLossCalculator, sample_stock_price: StockPrice
) -> None:
    """Test that guidance shows warning when stop-loss is above current price."""
    # Use 52-week high mode with high base price to create stop > current scenario
    result = calculator.calculate_simple(
        sample_stock_price, 5.0, sma_50=140.0, base_price=180.0
    )

    # Stop-loss should be above current price
    assert result.stop_loss_price == pytest.approx(171.0)  # 180 * 0.95
    assert result.current_price == 150.0
    assert result.stop_loss_price > result.current_price

    # Guidance should show warning, not SMA-based guidance
    assert result.formatted_guidance == "⚠️ Above current"


def test_guidance_normal_behavior(
    calculator: StopLossCalculator, sample_stock_price: StockPrice
) -> None:
    """Test that guidance works normally when stop-loss is below current price."""
    # Normal case: stop below SMA
    result1 = calculator.calculate_simple(sample_stock_price, 5.0, sma_50=145.0)
    assert result1.stop_loss_price == pytest.approx(142.5)
    assert result1.formatted_guidance == "Raise stop"

    # Normal case: stop above SMA
    result2 = calculator.calculate_simple(sample_stock_price, 5.0, sma_50=140.0)
    assert result2.stop_loss_price == pytest.approx(142.5)
    assert result2.formatted_guidance == "Keep current"

    # No SMA available
    result3 = calculator.calculate_simple(sample_stock_price, 5.0)
    assert result3.formatted_guidance == "N/A"
