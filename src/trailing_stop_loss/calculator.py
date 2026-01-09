"""Stop-loss calculation logic."""

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from trailing_stop_loss.fetcher import StockPrice


class StopLossType(Enum):
    """Type of stop-loss calculation."""

    SIMPLE = "simple"
    TRAILING = "trailing"
    ATR = "atr"


@dataclass
class StopLossResult:
    """Result of stop-loss calculation."""

    ticker: str
    current_price: float
    stop_loss_price: float
    stop_loss_type: StopLossType
    percentage: float
    currency: str
    dollar_risk: float  # Amount at risk per share
    sma_50: float | None = None  # 50-day simple moving average (for display only)
    atr_value: float | None = None  # ATR value (for ATR mode display)
    atr_multiplier: float | None = None  # ATR multiplier (for ATR mode display)
    week_52_high: float | None = None  # 52-week high (for display only)

    @property
    def formatted_guidance(self) -> str:
        """Get guidance on whether to update stop-loss based on SMA.

        Uses 50-day SMA as a sanity check:
        - If stop < SMA: Price above support, raise stop to lock gains
        - If stop > SMA: Stop is appropriately positioned, keep current
        """
        if self.sma_50 is None:
            return "N/A"
        elif self.stop_loss_price < self.sma_50:
            return "Raise stop"
        else:
            return "Keep current"

    @property
    def formatted_percentage(self) -> str:
        """Get formatted percentage string."""
        if self.stop_loss_type == StopLossType.ATR and self.atr_value is not None:
            # For ATR mode, show multiplier and ATR value
            return f"{self.atr_multiplier:.1f}× ({self.currency} {self.atr_value:.2f} ATR)"
        return f"{self.percentage:.2f}%"

    @property
    def formatted_risk(self) -> str:
        """Get formatted risk amount."""
        return f"{self.currency} {self.dollar_risk:.2f}"

    @property
    def formatted_sma(self) -> str:
        """Get formatted 50-day SMA string."""
        if self.sma_50 is None:
            return "N/A"
        return f"{self.currency} {self.sma_50:.2f}"


class StopLossCalculator:
    """Calculate stop-loss prices for stocks."""

    def __init__(self) -> None:
        """Initialize the calculator."""
        self._high_water_marks: dict[str, float] = {}

    def calculate_simple(
        self,
        stock_price: StockPrice,
        percentage: float,
        sma_50: float | None = None,
        base_price: float | None = None,
    ) -> StopLossResult:
        """Calculate simple stop-loss (percentage below current or base price).

        Args:
            stock_price: Current stock price information.
            percentage: Stop-loss percentage (0-100).
            sma_50: Optional 50-day simple moving average (for display only).
            base_price: Optional base price (e.g., 52-week high) to use instead of current price.

        Returns:
            StopLossResult with calculated stop-loss price.

        Raises:
            ValueError: If percentage is invalid.
        """
        if not 0 < percentage < 100:
            raise ValueError(f"Percentage must be between 0 and 100, got {percentage}")

        # Use base_price if provided, otherwise use current price
        calculation_base = base_price if base_price is not None else stock_price.current_price
        stop_loss_price = calculation_base * (1 - percentage / 100)
        dollar_risk = stock_price.current_price - stop_loss_price

        return StopLossResult(
            ticker=stock_price.ticker,
            current_price=stock_price.current_price,
            stop_loss_price=stop_loss_price,
            stop_loss_type=StopLossType.SIMPLE,
            percentage=percentage,
            currency=stock_price.currency,
            dollar_risk=dollar_risk,
            sma_50=sma_50,
            week_52_high=base_price if base_price is not None else None,
        )

    def calculate_trailing(
        self,
        stock_price: StockPrice,
        percentage: float,
        high_water_mark: float | None = None,
        sma_50: float | None = None,
    ) -> StopLossResult:
        """Calculate trailing stop-loss (tracks high water mark).

        Args:
            stock_price: Current stock price information.
            percentage: Stop-loss percentage (0-100).
            high_water_mark: Optional pre-calculated high water mark. If None,
                           uses in-memory tracking (legacy behavior).
            sma_50: Optional 50-day simple moving average (for display only).

        Returns:
            StopLossResult with calculated trailing stop-loss price.

        Raises:
            ValueError: If percentage is invalid.
        """
        if not 0 < percentage < 100:
            raise ValueError(f"Percentage must be between 0 and 100, got {percentage}")

        # Use provided high water mark, or fall back to in-memory tracking
        if high_water_mark is not None:
            # Use the provided high water mark (from database)
            hwm = high_water_mark
        else:
            # Legacy in-memory tracking
            ticker = stock_price.ticker
            if ticker not in self._high_water_marks:
                self._high_water_marks[ticker] = stock_price.current_price
            else:
                self._high_water_marks[ticker] = max(
                    self._high_water_marks[ticker], stock_price.current_price
                )
            hwm = self._high_water_marks[ticker]

        stop_loss_price = hwm * (1 - percentage / 100)
        dollar_risk = stock_price.current_price - stop_loss_price

        return StopLossResult(
            ticker=stock_price.ticker,
            current_price=stock_price.current_price,
            stop_loss_price=stop_loss_price,
            stop_loss_type=StopLossType.TRAILING,
            percentage=percentage,
            currency=stock_price.currency,
            dollar_risk=dollar_risk,
            sma_50=sma_50,
            week_52_high=None,
        )

    def calculate(
        self,
        stock_price: StockPrice,
        percentage: float,
        trailing: bool = False,
        high_water_mark: float | None = None,
    ) -> StopLossResult:
        """Calculate stop-loss price.

        Args:
            stock_price: Current stock price information.
            percentage: Stop-loss percentage (0-100).
            trailing: Whether to use trailing stop-loss.
            high_water_mark: Optional high water mark for trailing mode.

        Returns:
            StopLossResult with calculated stop-loss price.
        """
        if trailing:
            return self.calculate_trailing(stock_price, percentage, high_water_mark)
        else:
            return self.calculate_simple(stock_price, percentage)

    def reset_high_water_mark(self, ticker: str | None = None) -> None:
        """Reset high water mark for trailing stop-loss.

        Args:
            ticker: Ticker symbol to reset, or None to reset all.
        """
        if ticker is None:
            self._high_water_marks.clear()
        elif ticker in self._high_water_marks:
            del self._high_water_marks[ticker]

    def get_high_water_mark(self, ticker: str) -> float | None:
        """Get current high water mark for a ticker.

        Args:
            ticker: Ticker symbol.

        Returns:
            High water mark price or None if not set.
        """
        return self._high_water_marks.get(ticker)

    @staticmethod
    def calculate_atr(history_df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range from historical data.

        Args:
            history_df: DataFrame with High, Low, Close columns and DatetimeIndex.
            period: Number of periods for ATR calculation (default 14).

        Returns:
            Average True Range value.

        Raises:
            ValueError: If insufficient data or required columns missing.
        """
        if len(history_df) < period:
            raise ValueError(f"Insufficient data: need {period} periods, got {len(history_df)}")

        required_cols = ["High", "Low", "Close"]
        missing = [col for col in required_cols if col not in history_df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Calculate True Range components
        high = history_df["High"]
        low = history_df["Low"]
        prev_close = history_df["Close"].shift(1)

        tr1 = high - low  # High - Low
        tr2 = abs(high - prev_close)  # |High - Previous Close|
        tr3 = abs(low - prev_close)  # |Low - Previous Close|

        # True Range is the maximum of the three
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR is the moving average of True Range
        atr = true_range.rolling(window=period).mean().iloc[-1]

        if pd.isna(atr):
            raise ValueError("ATR calculation resulted in NaN")

        return float(atr)

    def calculate_atr_stop_loss(
        self,
        stock_price: StockPrice,
        percentage: float,
        atr: float,
        atr_multiplier: float = 2.0,
        sma_50: float | None = None,
    ) -> StopLossResult:
        """Calculate ATR-based stop-loss.

        Args:
            stock_price: Current stock price information.
            percentage: Stop-loss percentage (not used in calculation, for compatibility).
            atr: Average True Range value.
            atr_multiplier: Multiplier for ATR (default 2.0).
            sma_50: Optional 50-day simple moving average (for display only).

        Returns:
            StopLossResult with calculated ATR-based stop-loss price.

        Raises:
            ValueError: If atr_multiplier is invalid.
        """
        if atr_multiplier <= 0:
            raise ValueError(f"ATR multiplier must be positive, got {atr_multiplier}")

        stop_loss_price = stock_price.current_price - (atr * atr_multiplier)
        dollar_risk = stock_price.current_price - stop_loss_price

        return StopLossResult(
            ticker=stock_price.ticker,
            current_price=stock_price.current_price,
            stop_loss_price=stop_loss_price,
            stop_loss_type=StopLossType.ATR,
            percentage=percentage,  # Not used in ATR mode
            currency=stock_price.currency,
            dollar_risk=dollar_risk,
            sma_50=sma_50,
            atr_value=atr,
            atr_multiplier=atr_multiplier,
        )
