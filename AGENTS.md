# AGENTS.md - Development Guide for AI Assistants

This document helps AI coding agents understand the project's architecture, decisions, and development workflow.

## Project Overview

**Purpose**: CLI tool for calculating stop-loss prices on stock positions, designed for Canadian traders using Wealthsimple.

**Core Features**:
- Simple stop-loss: Fixed percentage below current price
- Trailing stop-loss: Tracks historical high water marks using SQLite
- ATR-based stop-loss: Volatility-adaptive stops using Average True Range
- 52-week high mode: Conservative stops based on peak prices
- Multi-currency support: USD/CAD (and others via yfinance)
- Historical data storage: SQLite database with 52-week metrics
- Beautiful CLI output: Tables with typer + rich

**Target Users**: Individual traders who want to:
- Protect gains with trailing stops based on actual historical data
- Calculate stop-losses across multiple positions
- Track Canadian stocks (.TO suffix) and US stocks

## Architecture & Key Decisions

### Technology Choices

**Python 3.14 via mise**
- **Why**: Native `tomllib` (no external dependency for TOML parsing)
- **Why**: Modern type hints with PEP 604 union syntax (`X | None`)
- **Why**: Latest language features and performance improvements

**uv for package management**
- **Why**: Faster than pip/poetry for dependency resolution
- **Why**: Reproducible builds with `uv.lock`
- **Why**: Built-in virtual environment management

**yfinance for market data**
- **Why**: Free, no API key required
- **Why**: Supports Canadian stocks (.TO suffix)
- **Why**: Returns pandas DataFrames for easy historical data handling
- **Alternative considered**: Alpha Vantage (rejected: requires API key)

**typer + rich for CLI**
- **Why typer**: Modern CLI framework with excellent type hint integration
- **Why rich**: Beautiful table output without manual formatting
- **Why together**: Typer integrates seamlessly with rich for colored output

**SQLite for price history**
- **Why not text files**: Atomic operations prevent corruption
- **Why not Parquet**: No built-in deduplication, must load full file
- **Why not JSON**: Inefficient for time-series queries
- **Why SQLite**:
  - Built into Python stdlib (zero dependencies)
  - PRIMARY KEY (ticker, date) auto-deduplicates
  - Indexed queries for fast MAX(high) lookups
  - Handles concurrent access gracefully
  - Schema:
    ```sql
    CREATE TABLE price_history (
        ticker TEXT NOT NULL,
        date DATE NOT NULL,
        open REAL,
        high REAL NOT NULL,
        low REAL,
        close REAL NOT NULL,
        volume INTEGER,
        week_52_high REAL,     -- Stored from yfinance API
        week_52_low REAL,      -- Stored from yfinance API
        PRIMARY KEY (ticker, date)
    )
    ```
  - INSERT OR REPLACE: Updates existing entries (e.g., intraday price updates)
  - Automatic migration: Adds new columns to existing databases on startup

### Architecture Layers

**Separation of Concerns**:
1. `fetcher.py`: Data acquisition (yfinance API)
2. `history.py`: Data persistence (SQLite operations)
3. `calculator.py`: Business logic (stop-loss calculations)
4. `config.py`: Configuration loading (TOML parsing)
5. `cli.py`: User interface (typer + rich)

**Data Flow**:
```
User Input → CLI → Config + Fetcher → History DB → Calculator → CLI Output
```

**State Management**:
- **In-memory**: PriceFetcher cache (current session only)
- **Persistent**: SQLite database for historical high water marks
- **Why persistent**: Trailing stop-loss meaningless without historical context

## Development Workflow

### Environment Setup

**Use mise for Python version**:
```bash
# .python-version specifies 3.14
mise install python@3.14
# Automatically activated in this directory
```

**Use uv for dependencies**:
```bash
# Install dependencies (not pip install!)
uv sync --all-extras

# Add a new dependency
uv add <package>

# Update dependencies
uv sync
```

**Important**: `uv` may not be in PATH. Use `.venv/bin/` prefix for commands:
```bash
# Run tests
.venv/bin/pytest

# Run CLI
.venv/bin/python -m trailing_stop_loss.cli calculate
```

### Code Quality

**Formatting & Linting**:
```bash
# Auto-format code
.venv/bin/ruff format

# Check for issues
.venv/bin/ruff check

# Auto-fix issues
.venv/bin/ruff check --fix
```

**Ruff Configuration**:
- Line length: 100 characters
- Target: Python 3.14
- Selectors: E, F, I, N, W, UP, B, C4, PT
- Ignored: PT011 (pytest.raises without match parameter is acceptable)

### Testing

**Run tests**:
```bash
# All tests with coverage
.venv/bin/pytest

# Specific test file
.venv/bin/pytest tests/test_history.py -v

# Quick run without coverage
.venv/bin/pytest -q
```

**Testing Strategy**:
- **Unit tests**: `calculator.py`, `config.py` (pure logic, no I/O)
- **Integration tests**: `fetcher.py` (real API calls are acceptable)
- **Database tests**: `history.py` (use temp directories, auto-cleanup)
- **CLI tests**: Intentionally excluded from coverage (integration layer)

**Why exclude CLI from coverage?**
- CLI is thin integration layer
- Testing via `typer.testing.CliRunner` is brittle
- Manual testing with real data is more valuable

### Git Workflow

**Commit Message Format**:
```
<type>: <short summary>

<detailed body explaining what and why>

Technical decisions:
- Decision 1 with rationale
- Decision 2 with rationale

Architecture:
- Key architectural points

Testing approach:
- How features are tested

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types**: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`

**Example**:
```
feat: add historical price tracking with SQLite

Implemented persistent storage for trailing stop-loss calculations.

Technical decisions:
- SQLite over Parquet for atomic operations and deduplication
- PRIMARY KEY (ticker, date) prevents duplicate data
```

## Code Conventions

### Type Hints

**Always use type hints** - this is non-negotiable:
```python
# ✅ Good
def calculate(price: float, percentage: float) -> float:
    return price * (1 - percentage / 100)

# ❌ Bad
def calculate(price, percentage):
    return price * (1 - percentage / 100)
```

**Use modern union syntax** (Python 3.10+):
```python
# ✅ Good (PEP 604)
def get_price(ticker: str) -> float | None:
    ...

# ❌ Bad (old style)
from typing import Optional
def get_price(ticker: str) -> Optional[float]:
    ...
```

### Dataclasses Over Dictionaries

**Use dataclasses for structured data**:
```python
# ✅ Good
@dataclass
class StockPrice:
    ticker: str
    current_price: float
    currency: str

# ❌ Bad
price = {
    "ticker": "AAPL",
    "current_price": 150.0,
    "currency": "USD"
}
```

**Why**: Type safety, IDE autocomplete, clear contracts

### Typer CLI Annotations

**Use Annotated for CLI parameters** (avoids B008 linting error):
```python
# ✅ Good
def calculate(
    percentage: Annotated[
        float | None,
        typer.Option("--percentage", "-p", help="Stop-loss percentage"),
    ] = None,
) -> None:
    ...

# ❌ Bad (function call in default)
def calculate(
    percentage: float | None = typer.Option(
        None, "--percentage", "-p", help="Stop-loss percentage"
    ),
) -> None:
    ...
```

### Error Handling

**Graceful degradation** - continue processing even if some operations fail:
```python
# ✅ Good
results = []
for ticker in tickers:
    try:
        price = fetcher.fetch_price(ticker)
        results.append((ticker, price))
    except Exception as e:
        results.append((ticker, e))  # Don't stop processing
```

**Why**: One failed ticker shouldn't block all calculations

### SQLite Context Managers

**Always use context managers** for database connections:
```python
# ✅ Good
def get_high_water_mark(self, ticker: str) -> float | None:
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.execute("SELECT MAX(high) FROM prices WHERE ticker = ?", (ticker,))
        return cursor.fetchone()[0]
    # Connection auto-closes here

# ❌ Bad (manual close)
def get_high_water_mark(self, ticker: str) -> float | None:
    conn = sqlite3.connect(self.db_path)
    cursor = conn.execute("SELECT MAX(high) FROM prices WHERE ticker = ?", (ticker,))
    result = cursor.fetchone()[0]
    conn.close()  # Easy to forget!
    return result
```

### No Emojis in Code

**Exception**: CLI output only (user explicitly requested):
```python
# ✅ Acceptable (user-facing output)
type_str = "🔄 Trailing" if trailing else "📊 Simple"

# ❌ Bad (code comments or variable names)
# 🚀 This function calculates stuff
def calculate_🎯(x):  # ❌ Never use emoji in identifiers
    ...
```

## Common Tasks

### Adding a New CLI Option

1. **Update function signature** in `cli.py`:
   ```python
   def calculate(
       # ... existing parameters ...
       new_option: Annotated[
           str | None,
           typer.Option("--new-option", help="Description"),
       ] = None,
   ) -> None:
   ```

2. **Handle the option** in function body
3. **Update docstring examples**
4. **Test manually** with `.venv/bin/python -m trailing_stop_loss.cli`
5. **Update README** if user-facing

### Adding a New Ticker

1. **Edit `config.toml`**:
   ```toml
   tickers = [
       "AAPL",
       "NEW_TICKER",
   ]
   ```

2. **Run with trailing mode** to populate history:
   ```bash
   .venv/bin/python -m trailing_stop_loss.cli calculate --trailing
   ```

3. **For Canadian stocks**, use `.TO` suffix:
   ```toml
   tickers = ["SHOP.TO", "TD.TO"]
   ```

### Modifying Database Schema

1. **Create migration logic** in `history.py`:
   ```python
   def _migrate_db(self) -> None:
       with sqlite3.connect(self.db_path) as conn:
           # Check current version
           # Apply migrations
   ```

2. **Test with temporary database**:
   ```python
   def test_migration():
       with TemporaryDirectory() as tmpdir:
           db = PriceHistoryDB(Path(tmpdir) / "test.db")
           # Test migration
   ```

3. **Update schema documentation** in this file

### Adding a New Stop-Loss Calculation Mode

1. **Add to enum** in `calculator.py`:
   ```python
   class StopLossType(Enum):
       SIMPLE = "simple"
       TRAILING = "trailing"
       NEW_MODE = "new_mode"
   ```

2. **Implement calculation** method:
   ```python
   def calculate_new_mode(self, stock_price: StockPrice, percentage: float) -> StopLossResult:
       # Implementation
   ```

3. **Update `calculate()` dispatcher**
4. **Add tests** in `tests/test_calculator.py`
5. **Update CLI** to expose new mode

### Implementing Optional Calculation Variants (like 52-Week High)

Instead of creating entirely new modes, use optional parameters when calculation varies only by base price:

1. **Add optional parameter** to existing calculation methods:
   ```python
   def calculate_simple(
       self,
       stock_price: StockPrice,
       percentage: float,
       sma_50: float | None = None,
       base_price: float | None = None,  # New parameter
   ) -> StopLossResult:
       # Use base_price if provided, else current_price
       calculation_base = base_price if base_price is not None else stock_price.current_price
       stop_loss_price = calculation_base * (1 - percentage / 100)
       # Risk always relative to current price
       dollar_risk = stock_price.current_price - stop_loss_price
   ```

2. **Add to result dataclass** for display:
   ```python
   @dataclass
   class StopLossResult:
       # ... existing fields ...
       week_52_high: float | None = None  # Store base price used
   ```

3. **Update CLI** to fetch and pass the value:
   ```python
   # Fetch 52-week high if flag set
   week_52_highs: dict[str, float | None] = {}
   if use_52week_high and history_db:
       for ticker in price_results.keys():
           week_52_highs[ticker] = history_db.get_latest_52week_high(ticker)

   # Pass to calculator
   base_price = week_52_highs.get(ticker) if use_52week_high else None
   result = calculator.calculate_simple(price, percentage, sma_50, base_price)
   ```

4. **Update display** to show optional column:
   ```python
   # Check if any results have 52-week data
   has_52week = any(
       hasattr(result, "week_52_high") and result.week_52_high is not None
       for _, result in results
       if not isinstance(result, Exception)
   )

   # Conditionally add column
   if has_52week:
       table.add_column("52-Week High", justify="right")
   ```

5. **Write comprehensive tests**:
   - Test with base_price parameter
   - Test without base_price (backward compatibility)
   - Test that risk is always relative to current price
   - Test edge cases (base_price < current_price)

## File Organization

### Project Structure

```
trailing-stop-loss/
├── src/trailing_stop_loss/    # All source code
│   ├── __init__.py            # Package metadata
│   ├── cli.py                 # CLI interface (typer + rich)
│   ├── config.py              # TOML configuration
│   ├── fetcher.py             # yfinance integration
│   ├── calculator.py          # Stop-loss logic
│   └── history.py             # SQLite database
├── tests/                     # Tests mirror src/ structure
│   ├── test_config.py
│   ├── test_fetcher.py
│   ├── test_calculator.py
│   └── test_history.py
├── .data/                     # SQLite database (gitignored)
│   └── price_history.db
├── config.toml                # User configuration
├── pyproject.toml             # Project metadata
├── .python-version            # mise Python version
└── AGENTS.md                  # This file
```

### Module Responsibilities

**fetcher.py**:
- Fetch current prices (`fetch_price`)
- Fetch 52-week high/low from yfinance (`week_52_high`, `week_52_low` fields)
- Fetch historical OHLC data (`fetch_historical_data`)
- In-memory caching for current session
- **No** business logic or database access

**history.py**:
- SQLite connection management
- Store/retrieve historical OHLC data
- Store/retrieve 52-week high/low values
- Calculate high water marks from DB (`get_high_water_mark`)
- Get latest 52-week high (`get_latest_52week_high`)
- Schema initialization with automatic migration
- **No** fetching or calculations

**calculator.py**:
- Stop-loss calculations (simple, trailing, ATR)
- Optional `base_price` parameter for 52-week high mode
- ATR calculation from historical DataFrame
- **No** data fetching or persistence
- Pure functions (except legacy in-memory trailing mode)

**config.py**:
- Load TOML configuration
- Provide typed accessors
- **No** validation logic (fail fast)

**cli.py**:
- Parse command-line arguments
- Coordinate: config → fetch → calculate → display
- Rich table formatting
- **Minimal** business logic

## Dependencies & Tools

### Required Dependencies

- **yfinance** (≥0.2.50): Market data API
- **typer** (≥0.15.0): CLI framework
- **rich** (≥14.0.0): Terminal formatting
- **tomli** (<3.11 only): TOML parsing backport

### Implicit Dependencies

- **pandas**: Via yfinance (used for history DataFrames)
- **sqlite3**: Python stdlib

### Dev Dependencies

- **pytest** (≥8.3.0): Test runner
- **pytest-cov** (≥6.0.0): Coverage reporting
- **ruff** (≥0.8.0): Linter + formatter

### When to Add Dependencies

**Ask these questions**:
1. Is it in stdlib? (prefer that)
2. Is it already an implicit dependency? (reuse)
3. Does it solve a real problem? (not speculative)
4. Is it maintained? (check last release date)
5. Does it have few dependencies itself? (avoid bloat)

**Examples**:
- ✅ Add: pandas (already via yfinance)
- ❌ Don't add: requests (use urllib from stdlib)
- ❌ Don't add: SQLAlchemy (overkill for simple queries)

## Anti-Patterns (What NOT to Do)

### Configuration

❌ **Don't use .env files**:
```python
# ❌ Bad
import os
tickers = os.getenv("TICKERS").split(",")

# ✅ Good
from config import Config
config = Config("config.toml")
tickers = config.tickers
```

**Why**: TOML is typed, version-controlled, and easier to edit

### Dependencies

❌ **Don't add dependencies without justification**:
- Need HTTP? Use stdlib `urllib`
- Need JSON? Use stdlib `json`
- Need TOML (Python 3.11+)? Use stdlib `tomllib`

❌ **Don't create proactive documentation**:
- Don't create CHANGELOG.md unless asked
- Don't create CONTRIBUTING.md unless asked
- README.md is sufficient

### CLI Design

❌ **Don't use function calls in defaults**:
```python
# ❌ Bad (causes B008 linting error)
def calculate(
    percentage: float = typer.Option(5.0, "--percentage")
):
    ...

# ✅ Good (use Annotated)
def calculate(
    percentage: Annotated[float, typer.Option("--percentage")] = 5.0
):
    ...
```

### Testing

❌ **Don't ignore test failures**:
- Fix or document why failure is acceptable
- Don't commit broken tests

❌ **Don't mix business logic in tests**:
```python
# ❌ Bad
def test_calculation():
    price = 100
    percentage = 5
    expected = price * (1 - percentage / 100)  # Business logic in test!
    assert calculate(price, percentage) == expected

# ✅ Good
def test_calculation():
    assert calculate(100, 5) == pytest.approx(95.0)
```

### Database

❌ **Don't manually close connections**:
```python
# ❌ Bad
conn = sqlite3.connect(db_path)
cursor = conn.execute("SELECT ...")
conn.close()

# ✅ Good
with sqlite3.connect(db_path) as conn:
    cursor = conn.execute("SELECT ...")
# Auto-closes
```

## Troubleshooting

### "Command not found: uv"

**Problem**: `uv` not in PATH
**Solution**: Use `.venv/bin/` prefix:
```bash
# Instead of: uv run pytest
.venv/bin/pytest

# Instead of: uv run stop-loss
.venv/bin/python -m trailing_stop_loss.cli
```

### ResourceWarning: unclosed database

**Problem**: Lots of warnings in pytest output
**Solution**: Ignore - these are false positives. Connections use context managers and auto-close.

### Historical data fetch fails

**Problem**: `fetch_historical_data()` raises ValueError
**Solution**: This is non-blocking by design. CLI continues with current price only.

**Debug**:
```python
# Check if ticker is valid
stock = yf.Ticker("INVALID")
print(stock.history(period="1mo"))  # Empty DataFrame = invalid
```

### Canadian stocks not working

**Problem**: Ticker like "SHOP" returns no data
**Solution**: Use `.TO` suffix for Toronto Stock Exchange:
```toml
tickers = ["SHOP.TO", "TD.TO", "RY.TO"]
```

### Trailing and simple give same result

**Problem**: First run shows identical stop-loss for both modes
**Solution**: Expected behavior! Historical data is fetched on first trailing run. Run again to see difference.

**Debug**:
```bash
# Check if database exists
ls -la .data/price_history.db

# Check database contents
sqlite3 .data/price_history.db "SELECT COUNT(*) FROM price_history WHERE ticker='AAPL'"
```

### Tests pass but coverage is low

**Expected**: CLI is excluded from coverage by design (60% coverage is normal)

**If legitimately low**:
1. Check `pyproject.toml` for `--cov=trailing_stop_loss`
2. Add tests for uncovered branches
3. Don't force 100% coverage - focus on critical paths

## Project-Specific Context

### Why This Project Exists

**Problem**: Wealthsimple (Canadian brokerage) doesn't offer automatic stop-loss orders.

**Solution**: Manual tracking tool that:
- Fetches real-time prices
- Calculates where to set mental/manual stop-loss
- Preserves historical highs so trailing stops make sense

**User workflow**:
1. Add tickers to `config.toml`
2. Run `stop-loss calculate --trailing` daily/weekly
3. Use output to manually set stop-losses in Wealthsimple

### Guidance Column Design Decision

**What it does:**
The "Guidance" column provides warnings and suggestions based on stop-loss position:
- `stop_loss_price > current_price` → "⚠️ Above current" (red) - **Priority check**
- `stop_loss_price < sma_50` → "Raise stop" (yellow)
- `stop_loss_price >= sma_50` → "Keep current" (green)
- `sma_50 is None` → "N/A"

**Technical assumption:**
Assumes the 50-day SMA acts as a support level (technical analysis concept). If price is above SMA and holding, the theory is you could tighten your stop-loss to lock in gains.

**Code location:**
- Calculated: `calculator.py:36-48` (`formatted_guidance` property)
- Displayed: `cli.py:83-88` (with color coding)

**Known limitations:**
1. **Not universal**: SMA as support is a technical analysis concept, not a market law. Works better in trending markets than ranging markets.
2. **Optional data**: Requires 50+ days of historical data. First-time users see "N/A" until enough data accumulates.
3. **Different applicability by mode**:
   - Simple/Trailing: Straightforward - tighten if above support
   - ATR: Less applicable since ATR already adapts to volatility
   - 52-week high: Warning shows when stop > current (fixed in latest version)

**Fixed issues:**
- ✅ **52-week high mode**: Now correctly shows "⚠️ Above current" warning when stop-loss is above current price
- ✅ **Stop-loss price coloring**: Displays in red when above current price (would trigger immediately)
- ✅ Priority check ensures warning shows before SMA-based guidance

**Why it exists:**
User-requested feature to provide actionable guidance. Intended as educational, not prescriptive. Users should apply their own judgment.

**Potential improvements (not yet implemented):**
- Different logic for different stop-loss modes (currently uses same SMA check for all)
- Configurable comparison period (e.g., 20-day vs 50-day SMA)
- Add disclaimer in table footer explaining guidance is educational
- Option to disable guidance entirely for users who don't want it

### Design Philosophy

**Pragmatism over purity**:
- SQLite over "proper" database (PostgreSQL)
- In-memory cache over Redis
- Manual testing over complex integration tests

**User experience first**:
- Beautiful tables (rich) over plain text
- Smart defaults (3 months history)
- Graceful errors (skip failed tickers)

**Minimal dependencies**:
- Prefer stdlib when possible
- Avoid frameworks (Django, Flask, etc.)
- Keep it lightweight and fast

### Future Considerations

**Potential features** (not yet implemented):
- Portfolio-level tracking (total value, allocation)
- Buy price tracking (from config or input)
- Alert thresholds (notify when stop hit)
- Historical performance (backtesting)

**Database migrations**:
- No migration framework (yet)
- Schema changes require manual SQL
- Document migrations in this file

**Multi-user**:
- Currently single-user (local SQLite)
- Could add user_id column for multi-user
- Or use separate databases per user
