"""Stop-loss calculation logic."""

from dataclasses import dataclass
from enum import Enum

from trailing_stop_loss.fetcher import StockPrice


class StopLossType(Enum):
    """Type of stop-loss calculation."""

    SIMPLE = "simple"
    TRAILING = "trailing"


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

    @property
    def formatted_percentage(self) -> str:
        """Get formatted percentage string."""
        return f"{self.percentage:.2f}%"

    @property
    def formatted_risk(self) -> str:
        """Get formatted risk amount."""
        return f"{self.currency} {self.dollar_risk:.2f}"


class StopLossCalculator:
    """Calculate stop-loss prices for stocks."""

    def __init__(self) -> None:
        """Initialize the calculator."""
        self._high_water_marks: dict[str, float] = {}

    def calculate_simple(self, stock_price: StockPrice, percentage: float) -> StopLossResult:
        """Calculate simple stop-loss (percentage below current price).

        Args:
            stock_price: Current stock price information.
            percentage: Stop-loss percentage (0-100).

        Returns:
            StopLossResult with calculated stop-loss price.

        Raises:
            ValueError: If percentage is invalid.
        """
        if not 0 < percentage < 100:
            raise ValueError(f"Percentage must be between 0 and 100, got {percentage}")

        stop_loss_price = stock_price.current_price * (1 - percentage / 100)
        dollar_risk = stock_price.current_price - stop_loss_price

        return StopLossResult(
            ticker=stock_price.ticker,
            current_price=stock_price.current_price,
            stop_loss_price=stop_loss_price,
            stop_loss_type=StopLossType.SIMPLE,
            percentage=percentage,
            currency=stock_price.currency,
            dollar_risk=dollar_risk,
        )

    def calculate_trailing(self, stock_price: StockPrice, percentage: float) -> StopLossResult:
        """Calculate trailing stop-loss (tracks high water mark).

        Args:
            stock_price: Current stock price information.
            percentage: Stop-loss percentage (0-100).

        Returns:
            StopLossResult with calculated trailing stop-loss price.

        Raises:
            ValueError: If percentage is invalid.
        """
        if not 0 < percentage < 100:
            raise ValueError(f"Percentage must be between 0 and 100, got {percentage}")

        # Update high water mark if current price is higher
        ticker = stock_price.ticker
        if ticker not in self._high_water_marks:
            self._high_water_marks[ticker] = stock_price.current_price
        else:
            self._high_water_marks[ticker] = max(
                self._high_water_marks[ticker], stock_price.current_price
            )

        high_water_mark = self._high_water_marks[ticker]
        stop_loss_price = high_water_mark * (1 - percentage / 100)
        dollar_risk = stock_price.current_price - stop_loss_price

        return StopLossResult(
            ticker=stock_price.ticker,
            current_price=stock_price.current_price,
            stop_loss_price=stop_loss_price,
            stop_loss_type=StopLossType.TRAILING,
            percentage=percentage,
            currency=stock_price.currency,
            dollar_risk=dollar_risk,
        )

    def calculate(
        self, stock_price: StockPrice, percentage: float, trailing: bool = False
    ) -> StopLossResult:
        """Calculate stop-loss price.

        Args:
            stock_price: Current stock price information.
            percentage: Stop-loss percentage (0-100).
            trailing: Whether to use trailing stop-loss.

        Returns:
            StopLossResult with calculated stop-loss price.
        """
        if trailing:
            return self.calculate_trailing(stock_price, percentage)
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
