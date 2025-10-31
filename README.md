# Trailing Stop-Loss Calculator

Calculate stop-loss prices for stock positions with a beautiful CLI interface.

## Features

- **Simple Stop-Loss**: Calculate stop-loss as a percentage below current price
- **Trailing Stop-Loss**: Track high-water marks and adjust stop-loss dynamically
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

Or use simple stop-loss explicitly:

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
│       └── calculator.py     # Stop-loss calculation logic
├── tests/
│   ├── test_config.py        # Config tests
│   ├── test_fetcher.py       # Fetcher tests (integration)
│   └── test_calculator.py    # Calculator tests
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

Tracks the highest price seen (high-water mark) and calculates stop-loss from that:

```
Stop-Loss Price = High-Water Mark × (1 - Percentage / 100)
```

Example: If SHOP.TO goes from $80 CAD → $90 CAD → $85 CAD with 5% trailing stop:
- At $80: Stop-Loss = $76.00 CAD
- At $90: Stop-Loss = $85.50 CAD (tracks new high)
- At $85: Stop-Loss = $85.50 CAD (stays at high-water mark)

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

# Load config
config = Config("config.toml")

# Fetch prices
fetcher = PriceFetcher()
price = fetcher.fetch_price("SHOP.TO")  # Canadian stock

# Calculate stop-loss
calculator = StopLossCalculator()
result = calculator.calculate(price, percentage=5.0, trailing=False)

print(f"{result.ticker}: {result.currency} {result.current_price} → {result.currency} {result.stop_loss_price}")
# Output: SHOP.TO: CAD 85.50 → CAD 81.23
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
