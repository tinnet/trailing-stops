"""Tests for price history database."""

from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import pytest

from trailing_stop_loss.history import PriceHistoryDB


@pytest.fixture
def temp_db() -> PriceHistoryDB:
    """Create a temporary database for testing."""
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield PriceHistoryDB(db_path)


@pytest.fixture
def sample_history_df() -> pd.DataFrame:
    """Create sample historical data."""
    data = {
        "Open": [100.0, 102.0, 101.0],
        "High": [105.0, 107.0, 106.0],
        "Low": [99.0, 101.0, 100.0],
        "Close": [103.0, 105.0, 104.0],
        "Volume": [1000000, 1100000, 1050000],
    }
    dates = pd.date_range("2024-01-01", periods=3)
    return pd.DataFrame(data, index=dates)


def test_db_initialization(temp_db: PriceHistoryDB) -> None:
    """Test that database is initialized correctly."""
    assert temp_db.db_path.exists()
    assert not temp_db.has_data("AAPL")


def test_store_history(temp_db: PriceHistoryDB, sample_history_df: pd.DataFrame) -> None:
    """Test storing historical data."""
    rows = temp_db.store_history("AAPL", sample_history_df)
    assert rows == 3
    assert temp_db.has_data("AAPL")


def test_store_history_ignores_duplicates(
    temp_db: PriceHistoryDB, sample_history_df: pd.DataFrame
) -> None:
    """Test that duplicate entries are ignored."""
    temp_db.store_history("AAPL", sample_history_df)
    # Try to store the same data again
    rows = temp_db.store_history("AAPL", sample_history_df)
    assert rows == 0  # No new rows inserted


def test_store_current_price(temp_db: PriceHistoryDB) -> None:
    """Test storing current price."""
    success = temp_db.store_current_price("AAPL", 150.0)
    assert success
    assert temp_db.has_data("AAPL")

    # Try to store again on same day
    success = temp_db.store_current_price("AAPL", 151.0)
    assert not success  # Already exists for today


def test_get_high_water_mark(temp_db: PriceHistoryDB, sample_history_df: pd.DataFrame) -> None:
    """Test getting high water mark."""
    temp_db.store_history("AAPL", sample_history_df)

    # Get max high (should be 107.0)
    hwm = temp_db.get_high_water_mark("AAPL")
    assert hwm == pytest.approx(107.0)


def test_get_high_water_mark_with_since_date(
    temp_db: PriceHistoryDB, sample_history_df: pd.DataFrame
) -> None:
    """Test getting high water mark since a specific date."""
    temp_db.store_history("AAPL", sample_history_df)

    # Get max high since 2024-01-02
    hwm = temp_db.get_high_water_mark("AAPL", since_date="2024-01-02")
    assert hwm == pytest.approx(107.0)  # Max of last two days


def test_get_high_water_mark_no_data(temp_db: PriceHistoryDB) -> None:
    """Test getting high water mark when no data exists."""
    hwm = temp_db.get_high_water_mark("AAPL")
    assert hwm is None


def test_get_last_update_date(temp_db: PriceHistoryDB, sample_history_df: pd.DataFrame) -> None:
    """Test getting last update date."""
    temp_db.store_history("AAPL", sample_history_df)

    last_date = temp_db.get_last_update_date("AAPL")
    assert last_date == date(2024, 1, 3)


def test_get_last_update_date_no_data(temp_db: PriceHistoryDB) -> None:
    """Test getting last update date when no data exists."""
    last_date = temp_db.get_last_update_date("AAPL")
    assert last_date is None


def test_delete_ticker_history(temp_db: PriceHistoryDB, sample_history_df: pd.DataFrame) -> None:
    """Test deleting ticker history."""
    temp_db.store_history("AAPL", sample_history_df)
    assert temp_db.has_data("AAPL")

    rows = temp_db.delete_ticker_history("AAPL")
    assert rows == 3
    assert not temp_db.has_data("AAPL")


def test_get_history(temp_db: PriceHistoryDB, sample_history_df: pd.DataFrame) -> None:
    """Test retrieving historical data."""
    temp_db.store_history("AAPL", sample_history_df)

    history = temp_db.get_history("AAPL")
    assert len(history) == 3
    assert history[0]["ticker"] == "AAPL"
    assert history[0]["high"] == pytest.approx(105.0)


def test_get_history_with_since_date(
    temp_db: PriceHistoryDB, sample_history_df: pd.DataFrame
) -> None:
    """Test retrieving historical data since a specific date."""
    temp_db.store_history("AAPL", sample_history_df)

    history = temp_db.get_history("AAPL", since_date="2024-01-02")
    assert len(history) == 2  # Only last two days


def test_multiple_tickers(temp_db: PriceHistoryDB, sample_history_df: pd.DataFrame) -> None:
    """Test storing and retrieving data for multiple tickers."""
    temp_db.store_history("AAPL", sample_history_df)
    temp_db.store_history("GOOGL", sample_history_df)

    assert temp_db.has_data("AAPL")
    assert temp_db.has_data("GOOGL")

    hwm_aapl = temp_db.get_high_water_mark("AAPL")
    hwm_googl = temp_db.get_high_water_mark("GOOGL")

    assert hwm_aapl == hwm_googl == pytest.approx(107.0)
