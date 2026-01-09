# Trailing Stop-Loss Calculator

Calculate stop-loss prices for stock positions with a beautiful CLI interface.

## Features

- **Simple Stop-Loss**: Calculate stop-loss as a percentage below current price
- **Trailing Stop-Loss**: Track high-water marks and adjust stop-loss dynamically
- **ATR-Based Stop-Loss**: Volatility-adaptive stop-loss using Average True Range
- **52-Week High Mode**: Base calculations on 52-week high for more conservative stops
- **Historical Data**: SQLite database stores price history and 52-week metrics
- **Beautiful CLI**: Rich table output with color-coded results using `typer` and `rich`
- **Multi-Currency Support**: Automatically handles USD, CAD, and other currencies
- **TOML Configuration**: Easy configuration for default tickers and settings
- **Real-time Prices**: Fetch current stock prices via `yfinance`
- **Type-Safe**: Full type hints throughout the codebase
- **Well-Tested**: Comprehensive test suite with `pytest`

## Installation

This project uses `uv` for package management and requires Python 3.14+.

```bash
# Install dependencies
uv sync

# Install with dev dependencies
uv sync --all-extras
```

## Configuration

Create or edit `config.toml` in the project root:

```toml
# List of ticker symbols to track
# Works with US and Canadian stocks (and others supported by yfinance)
tickers = [
    "AAPL",     # Apple Inc. (USD)
    "GOOGL",    # Alphabet Inc. (USD)
    "SHOP.TO",  # Shopify (CAD - Toronto Stock Exchange)
    "RY.TO",    # Royal Bank of Canada (CAD)
]

# Default stop-loss percentage (0-100)
stop_loss_percentage = 5.0

# Enable trailing stop-loss by default
trailing_enabled = false
```

**Note**: Canadian stocks on the Toronto Stock Exchange use the `.TO` suffix (e.g., `SHOP.TO`, `TD.TO`).

## Usage

### Basic Usage

Calculate stop-loss for configured tickers:

```bash
uv run stop-loss calculate
```

### With Custom Tickers

Override config and specify tickers directly:

```bash
uv run stop-loss calculate AAPL GOOGL SHOP.TO
```

### Custom Percentage

Use a different stop-loss percentage:

```bash
uv run stop-loss calculate --percentage 7.5
uv run stop-loss calculate -p 10
```

### Trailing Stop-Loss

Enable trailing stop-loss (tracks high-water mark):

```bash
uv run stop-loss calculate --trailing
uv run stop-loss calculate -t
```

### ATR-Based Stop-Loss

Use ATR (Average True Range) for volatility-adaptive stop-loss:

```bash
uv run stop-loss calculate --atr
uv run stop-loss calculate -a
```

Customize ATR parameters:

```bash
# Use tighter stop (1.5× ATR)
uv run stop-loss calculate --atr --atr-multiplier 1.5
uv run stop-loss calculate -a -m 1.5  # short form

# Use looser stop (3× ATR)
uv run stop-loss calculate --atr --atr-multiplier 3.0
uv run stop-loss calculate -a -m 3.0  # short form

# Change ATR period (default 14 days)
uv run stop-loss calculate --atr --atr-period 20
uv run stop-loss calculate -a -P 20  # short form
```

### Simple Stop-Loss

Use simple stop-loss explicitly:

```bash
uv run stop-loss calculate --simple
uv run stop-loss calculate -s
```

### Combine Options

```bash
uv run stop-loss calculate SHOP.TO NVDA -p 8 --trailing
```

### Custom Config File

```bash
uv run stop-loss calculate --config /path/to/config.toml
uv run stop-loss calculate -c custom-config.toml
```

### 52-Week High Mode

Base stop-loss calculations on the 52-week high instead of current price (more conservative):

```bash
# Simple mode with 52-week high (8% below peak)
uv run stop-loss calculate --week52-high --simple -p 8
uv run stop-loss calculate -w --simple -p 8  # short flag

# ATR mode with 52-week high
uv run stop-loss calculate --week52-high --atr
uv run stop-loss calculate -w --atr  # short flag

# Works with multiple tickers
uv run stop-loss calculate AAPL MSFT NVDA -w --simple -p 10
```

**When to use**: If you bought near the 52-week high and want to protect gains from the peak price rather than current price.

**Example**: AAPL at $259.04 with 52-week high of $288.62:
- **Normal mode**: 8% stop = $238.32 (risk $20.72/share)
- **52-week mode**: 8% stop = $265.53 (risk -$6.49/share, above current price)

### Advanced Options

Calculate from a specific date (useful if you bought at a known date):

```bash
uv run stop-loss calculate --trailing --since 2024-01-15
uv run stop-loss calculate -t -d 2024-01-15  # short form
```

Skip historical data fetching (use only in-memory tracking):

```bash
uv run stop-loss calculate --trailing --no-history
uv run stop-loss calculate -t -H  # short form
```

### CLI Flag Reference

All flags with their short forms:

| Flag | Short | Description |
|------|-------|-------------|
| `--config` | `-c` | Path to configuration file |
| `--percentage` | `-p` | Stop-loss percentage (0-100) |
| `--simple` | `-s` | Use simple stop-loss mode |
| `--trailing` | `-t` | Use trailing stop-loss mode |
| `--atr` | `-a` | Use ATR-based stop-loss mode |
| `--atr-period` | `-P` | ATR calculation period in trading days (default: 14) |
| `--atr-multiplier` | `-m` | ATR multiplier for stop distance (default: 2.0) |
| `--since` | `-d` | Start date for trailing calculation (YYYY-MM-DD) |
| `--no-history` | `-H` | Skip historical data fetching |
| `--week52-high` | `-w` | Base calculations on 52-week high |

### Version Info

```bash
uv run stop-loss version
```

**Note**: If you install the package globally or in a virtual environment, you can use `stop-loss` directly without `uv run`.

## Development

### Setup with mise

This project uses `mise` for Python version management:

```bash
# Python 3.14 will be automatically activated via .python-version
mise install python@3.14
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_calculator.py
```

### Code Quality

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Fix linting issues
uv run ruff check --fix
```

## Project Structure

```
trailing-stop-loss/
├── src/
│   └── trailing_stop_loss/
│       ├── __init__.py       # Package initialization
│       ├── cli.py            # Typer CLI interface
│       ├── config.py         # TOML configuration loader
│       ├── fetcher.py        # yfinance price fetching
│       ├── calculator.py     # Stop-loss calculation logic
│       └── history.py        # SQLite price history database
├── tests/
│   ├── test_config.py        # Config tests
│   ├── test_fetcher.py       # Fetcher tests (integration)
│   ├── test_calculator.py    # Calculator tests
│   └── test_history.py       # History database tests
├── .data/                    # SQLite database (gitignored)
│   └── price_history.db      # Historical OHLC data
├── config.toml               # Configuration file
├── pyproject.toml            # Project metadata and dependencies
└── .python-version           # Python version for mise
```

## How It Works

### Simple Stop-Loss

Calculates stop-loss as a fixed percentage below the current price:

```
Stop-Loss Price = Current Price × (1 - Percentage / 100)
```

Example: If AAPL is at $150 USD with 5% stop-loss:
- Stop-Loss Price = $150 × 0.95 = $142.50 USD

### Trailing Stop-Loss

Tracks the highest price seen (high-water mark) from historical data and calculates stop-loss from that:

```
Stop-Loss Price = High-Water Mark × (1 - Percentage / 100)
```

**How it works:**
1. First run: Fetches 3 months of historical OHLC data from yfinance
2. Stores data in SQLite database (`.data/price_history.db`)
3. Finds the maximum high price since you started tracking
4. Subsequent runs: Only fetches new data since last update
5. Current price is appended to history on each run

**Example:** If AMD went from $220 → $267 → $255 over 3 months with 5% trailing stop:
- Historical High: $267
- Current Price: $255
- Stop-Loss: $267 × 0.95 = $253.65 (only $1.35 at risk!)
- Simple mode would give: $255 × 0.95 = $242.25 ($12.75 at risk)

The trailing mode protects your gains by locking in profits as the price rises.

### ATR-Based Stop-Loss

Uses Average True Range (ATR) to adapt stop-loss distance to each stock's volatility:

```
ATR = 14-day moving average of True Range
True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
Stop-Loss Price = Current Price - (ATR × Multiplier)
```

**How it works:**
1. Fetches historical OHLC data (same as trailing mode)
2. Calculates True Range for each day (captures daily volatility)
3. Takes 14-day moving average of True Range = ATR
4. Stop-loss is placed at Current Price - (ATR × Multiplier)

**Example:** AMD at $254.84 with ATR = $10.89:
- **ATR (2.0×)**: $254.84 - (2.0 × $10.89) = $233.06 stop ($21.78 at risk)
- **Simple (5%)**: $254.84 × 0.95 = $242.10 stop ($12.74 at risk)
- **Trailing (5%)**: $267 (historical high) × 0.95 = $253.65 stop ($1.19 at risk)

**When to use ATR:**
- Volatile stocks need wider stops to avoid being stopped out by normal price swings
- ATR automatically adapts: volatile stocks get wider stops, stable stocks get tighter stops
- Standard multipliers: 1.5× (tight), 2.0× (normal), 3.0× (loose)

**Key difference from percentage modes:**
- Percentage modes: Fixed % regardless of volatility
- ATR mode: Adapts to each stock's actual price movement patterns

### 52-Week High Mode

Uses the 52-week high as the base price for calculating stop-losses:

```
# With Simple Strategy
Stop-Loss Price = 52-Week High × (1 - Percentage / 100)

# With ATR Strategy
Stop-Loss Price = 52-Week High - (ATR × Multiplier)
```

**How it works:**
1. Fetches current 52-week high from yfinance on each run
2. Stores the value in SQLite database with the price snapshot
3. Uses the most recent 52-week high as the base for calculations
4. Dollar risk is still calculated relative to current price

**Example:** AAPL at $259.04 with 52-week high of $288.62:

| Mode | Calculation | Stop-Loss | Risk/Share |
|------|------------|-----------|------------|
| **Simple (8%)** | $259.04 × 0.92 | $238.32 | $20.72 |
| **52-week Simple (8%)** | $288.62 × 0.92 | $265.53 | -$6.49* |
| **ATR (2.0×)** | $259.04 - ($3.85 × 2.0) | $251.33 | $7.71 |
| **52-week ATR (2.0×)** | $288.62 - ($3.85 × 2.0) | $280.91 | -$21.87* |

**Note on negative risk**: When 52-week high mode places the stop-loss above current price, the risk appears negative. This indicates a more conservative position where you'd exit if the price doesn't recover to near its peak.

**When to use 52-week high mode:**
- You bought near the peak and want to break even or minimize losses
- You're protecting paper gains from a stock that's pulled back from highs
- You prefer a more conservative approach that doesn't chase price declines

**When NOT to use:**
- Stock is at or near its 52-week high (use normal mode instead)
- You bought significantly below current price (trailing mode is better)
- Stock has strong downtrend from peak (may get stopped out immediately)

### Currency Handling

The tool automatically detects and displays the currency for each stock:
- US stocks typically show prices in USD
- Canadian stocks (`.TO`) show prices in CAD
- Each stock's currency is fetched from yfinance and displayed in the output

## API Example

You can also use the package programmatically:

```python
from trailing_stop_loss.config import Config
from trailing_stop_loss.fetcher import PriceFetcher
from trailing_stop_loss.calculator import StopLossCalculator
from trailing_stop_loss.history import PriceHistoryDB

# Load config
config = Config("config.toml")

# Fetch prices
fetcher = PriceFetcher()
price = fetcher.fetch_price("AAPL")
print(f"Current: ${price.current_price}, 52-week high: ${price.week_52_high}")

# Simple stop-loss
calculator = StopLossCalculator()
simple_result = calculator.calculate_simple(price, percentage=8.0)
print(f"Simple: ${simple_result.stop_loss_price:.2f} (${simple_result.dollar_risk:.2f} risk)")

# 52-week high mode
week52_result = calculator.calculate_simple(price, percentage=8.0, base_price=price.week_52_high)
print(f"52-week: ${week52_result.stop_loss_price:.2f} (${week52_result.dollar_risk:.2f} risk)")

# ATR-based with 52-week high
history_db = PriceHistoryDB()
history_df = history_db.get_recent_history_df("AAPL", days=15)
atr = calculator.calculate_atr(history_df, period=14)
atr_result = calculator.calculate_atr_stop_loss(
    price, percentage=8.0, atr=atr, atr_multiplier=2.0,
    base_price=price.week_52_high  # Optional: use 52-week high
)
print(f"ATR: ${atr_result.stop_loss_price:.2f} (${atr_result.dollar_risk:.2f} risk)")
```

## Dependencies

- **yfinance**: Real-time stock price data
- **typer**: Modern CLI framework
- **rich**: Beautiful terminal output
- **pytest**: Testing framework
- **ruff**: Fast Python linter and formatter

## License

MIT

## Contributing

Contributions welcome! Please ensure:
- All tests pass (`uv run pytest`)
- Code is formatted (`uv run ruff format`)
- Code passes linting (`uv run ruff check`)
- Type hints are used throughout
