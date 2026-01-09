"""Beautiful CLI interface using typer and rich."""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from trailing_stop_loss.calculator import StopLossCalculator
from trailing_stop_loss.config import Config
from trailing_stop_loss.fetcher import PriceFetcher, StockPrice
from trailing_stop_loss.history import PriceHistoryDB

app = typer.Typer(
    name="stop-loss",
    help="Calculate stop-loss prices for stock positions with beautiful CLI output.",
    add_completion=False,
)
console = Console()


def create_results_table(results: list[tuple[StockPrice, object]]) -> Table:
    """Create a rich table for displaying results.

    Args:
        results: List of (StockPrice, StopLossResult or Exception) tuples.

    Returns:
        Formatted rich Table.
    """
    # Check if any results have 52-week high data
    has_52week = any(
        hasattr(result, "week_52_high") and result.week_52_high is not None
        for _, result in results
        if not isinstance(result, Exception)
    )

    table = Table(title="Stop-Loss Calculator Results", show_header=True, header_style="bold cyan")

    table.add_column("Ticker", style="bold", justify="left")
    table.add_column("Current Price", justify="right")
    if has_52week:
        table.add_column("52-Week High", justify="right")
    table.add_column("50-Day SMA", justify="right")
    table.add_column("Stop-Loss Price", justify="right")
    table.add_column("Type", justify="center")
    table.add_column("Stop Method", justify="right")
    table.add_column("Risk/Share", justify="right")
    table.add_column("Guidance", justify="center")

    for stock_price, result in results:
        from trailing_stop_loss.calculator import StopLossResult

        if isinstance(result, Exception):
            row_data = [
                stock_price.ticker if hasattr(stock_price, "ticker") else "?",
                "[red]ERROR[/red]",
            ]
            if has_52week:
                row_data.append("[red]N/A[/red]")
            row_data.extend([
                "[red]N/A[/red]",
                "[red]N/A[/red]",
                "[red]N/A[/red]",
                "[red]N/A[/red]",
                f"[red]{str(result)[:30]}[/red]",
                "[red]N/A[/red]",
            ])
            table.add_row(*row_data)
        elif isinstance(result, StopLossResult):
            if result.stop_loss_type.value == "trailing":
                type_str = "🔄 Trailing"
            elif result.stop_loss_type.value == "atr":
                type_str = "📈 ATR"
            else:
                type_str = "📊 Simple"

            # Color stop-loss price: red if above current (would trigger), green if below
            if result.stop_loss_price > result.current_price:
                price_color = "red"
            else:
                price_color = "green"

            # Color code guidance
            if result.formatted_guidance == "⚠️ Above current":
                guidance_str = f"[red]{result.formatted_guidance}[/red]"
            elif result.formatted_guidance == "Raise stop":
                guidance_str = f"[yellow]{result.formatted_guidance}[/yellow]"
            elif result.formatted_guidance == "Keep current":
                guidance_str = f"[green]{result.formatted_guidance}[/green]"
            else:
                guidance_str = result.formatted_guidance

            # Build row data
            row_data = [
                result.ticker,
                f"{result.currency} {result.current_price:.2f}",
            ]
            if has_52week:
                if result.week_52_high is not None:
                    row_data.append(f"[cyan]{result.currency} {result.week_52_high:.2f}[/cyan]")
                else:
                    row_data.append("N/A")
            row_data.extend([
                result.formatted_sma,
                f"[{price_color}]{result.currency} {result.stop_loss_price:.2f}[/{price_color}]",
                type_str,
                result.formatted_percentage,
                result.formatted_risk,
                guidance_str,
            ])
            table.add_row(*row_data)

    return table


@app.command()
def calculate(
    tickers: Annotated[
        list[str] | None,
        typer.Argument(help="Ticker symbols to calculate (overrides config)"),
    ] = None,
    config_file: Annotated[
        Path, typer.Option("--config", "-c", help="Path to configuration file")
    ] = Path("config.toml"),
    percentage: Annotated[
        float | None,
        typer.Option("--percentage", "-p", help="Stop-loss percentage (overrides config)"),
    ] = None,
    trailing: Annotated[
        bool,
        typer.Option("--trailing", "-t", help="Use trailing stop-loss"),
    ] = False,
    simple: Annotated[
        bool,
        typer.Option("--simple", "-s", help="Use simple stop-loss"),
    ] = False,
    atr: Annotated[
        bool,
        typer.Option("--atr", "-a", help="Use ATR-based stop-loss"),
    ] = False,
    atr_period: Annotated[
        int,
        typer.Option("--atr-period", "-P", help="ATR calculation period (trading days)"),
    ] = 14,
    atr_multiplier: Annotated[
        float,
        typer.Option("--atr-multiplier", "-m", help="ATR multiplier for stop-loss distance"),
    ] = 2.0,
    since: Annotated[
        str | None,
        typer.Option("--since", "-d", help="Start date for trailing calculation (YYYY-MM-DD)"),
    ] = None,
    no_history: Annotated[
        bool,
        typer.Option("--no-history", "-H", help="Skip historical data fetching"),
    ] = False,
    week52_high: Annotated[
        bool,
        typer.Option("--week52-high", "-w", help="Base calculations on 52-week high instead of current price"),
    ] = False,
) -> None:
    """Calculate stop-loss prices for configured tickers.

    Examples:
        uv run stop-loss calculate
        uv run stop-loss calculate AAPL GOOGL MSFT
        uv run stop-loss calculate --percentage 7.5 --trailing
        uv run stop-loss calculate TSLA -p 10 --simple
        uv run stop-loss calculate --trailing --since 2024-01-01
        uv run stop-loss calculate --atr --atr-multiplier 2.5
        uv run stop-loss calculate --week52-high --simple -p 8
        uv run stop-loss calculate -w --atr
    """
    try:
        # Load configuration
        config = Config(config_file)

        # Determine tickers
        ticker_list = tickers if tickers else config.tickers
        if not ticker_list:
            console.print(
                "[red]No tickers specified. Add them to config.toml or pass as arguments."
            )
            raise typer.Exit(1)

        # Determine percentage
        pct = percentage if percentage is not None else config.stop_loss_percentage

        # Determine calculation mode
        mode_count = sum([simple, trailing, atr])
        if mode_count > 1:
            console.print("[red]Error: Only one mode (--simple, --trailing, --atr) can be specified.[/red]")
            raise typer.Exit(1)

        # Determine which mode to use
        if atr:
            use_mode = "atr"
        elif trailing:
            use_mode = "trailing"
        elif simple:
            use_mode = "simple"
        else:
            # Default from config
            use_mode = "trailing" if config.trailing_enabled else "simple"

        # Parse since date if provided
        since_date: date | None = None
        if since:
            try:
                since_date = datetime.strptime(since, "%Y-%m-%d").date()
            except ValueError:
                console.print(f"[red]Invalid date format: {since}. Use YYYY-MM-DD[/red]")
                raise typer.Exit(1)

        # Initialize components
        fetcher = PriceFetcher()
        calculator = StopLossCalculator()
        history_db = PriceHistoryDB() if not no_history else None

        # Fetch historical data if using trailing or ATR mode and history is enabled
        if use_mode in ("trailing", "atr") and history_db:
            console.print("[cyan]Updating historical price data...[/cyan]")
            for ticker in ticker_list:
                try:
                    # Check if we have data
                    last_update = history_db.get_last_update_date(ticker)
                    if last_update:
                        # Fetch only new data since last update
                        start_date = last_update + timedelta(days=1)
                        if start_date <= date.today():
                            hist_data = fetcher.fetch_historical_data(
                                ticker, start_date=start_date
                            )
                            rows = history_db.store_history(ticker, hist_data)
                            if rows > 0:
                                console.print(
                                    f"  [dim]Added {rows} new data points for {ticker}[/dim]"
                                )
                    else:
                        # First time fetching - get enough data for ATR or trailing mode
                        # For ATR: need atr_period trading days (~3x calendar days + buffer)
                        # For trailing: 3 months default is usually enough
                        if use_mode == "atr":
                            days_needed = max(atr_period * 3, 180)
                        else:
                            days_needed = 90
                        start = since_date or (date.today() - timedelta(days=days_needed))
                        hist_data = fetcher.fetch_historical_data(ticker, start_date=start)
                        rows = history_db.store_history(ticker, hist_data)
                        console.print(
                            f"  [dim]Stored {rows} historical data points for {ticker}[/dim]"
                        )
                except Exception as e:
                    console.print(f"  [yellow]Warning: Could not fetch history for {ticker}: {e}[/yellow]")

        # Fetch current prices
        console.print(f"[cyan]Fetching current prices for {len(ticker_list)} ticker(s)...[/cyan]")
        price_results = fetcher.fetch_multiple(ticker_list, skip_errors=True)

        # Store current prices in history if enabled
        if history_db:
            for ticker, price_or_error in price_results.items():
                if not isinstance(price_or_error, Exception):
                    history_db.store_current_price(
                        ticker,
                        price_or_error.current_price,
                        price_or_error.timestamp,
                        price_or_error.week_52_high,
                        price_or_error.week_52_low,
                    )

        # Calculate 50-day SMA for all tickers
        sma_values: dict[str, float | None] = {}
        if history_db:
            for ticker in price_results.keys():
                try:
                    history_df = history_db.get_recent_history_df(ticker, 50)
                    sma_values[ticker] = float(history_df["Close"].mean())
                except ValueError:
                    # Not enough data - try to fetch it
                    try:
                        start = date.today() - timedelta(days=75)  # 50 trading days + buffer
                        hist_data = fetcher.fetch_historical_data(ticker, start_date=start)
                        history_db.store_history(ticker, hist_data)
                        history_df = history_db.get_recent_history_df(ticker, 50)
                        sma_values[ticker] = float(history_df["Close"].mean())
                    except Exception:
                        sma_values[ticker] = None
        else:
            for ticker in price_results.keys():
                sma_values[ticker] = None

        # Fetch 52-week high values if flag is set
        week_52_highs: dict[str, float | None] = {}
        if week52_high and history_db:
            for ticker in price_results.keys():
                week_52_highs[ticker] = history_db.get_latest_52week_high(ticker)
        else:
            for ticker in price_results.keys():
                week_52_highs[ticker] = None

        # Calculate stop-losses
        results: list[tuple[StockPrice | str, object]] = []
        for ticker, price_or_error in price_results.items():
            if isinstance(price_or_error, Exception):
                results.append((ticker, price_or_error))
            else:
                try:
                    # Get SMA and 52-week high for this ticker
                    sma_50 = sma_values.get(ticker)
                    base_price = week_52_highs.get(ticker) if week52_high else None

                    if use_mode == "atr":
                        # ATR mode: calculate ATR from historical data
                        if history_db:
                            try:
                                history_df = history_db.get_recent_history_df(ticker, atr_period + 1)
                                atr_value = calculator.calculate_atr(history_df, atr_period)
                                stop_loss = calculator.calculate_atr_stop_loss(
                                    price_or_error, pct, atr_value, atr_multiplier, sma_50, base_price
                                )
                            except ValueError as e:
                                # Not enough historical data - try to fetch it now
                                console.print(f"[yellow]Insufficient data for {ticker}, fetching historical data...[/yellow]")
                                try:
                                    # Fetch enough data: ATR period needs trading days, so fetch ~3x calendar days
                                    # Plus buffer for weekends/holidays (minimum 6 months for safety)
                                    days_needed = max(atr_period * 3, 180)
                                    start = date.today() - timedelta(days=days_needed)
                                    hist_data = fetcher.fetch_historical_data(ticker, start_date=start)
                                    rows = history_db.store_history(ticker, hist_data)
                                    console.print(f"  [dim]Stored {rows} historical data points for {ticker}[/dim]")

                                    # Retry calculation
                                    history_df = history_db.get_recent_history_df(ticker, atr_period + 1)
                                    atr_value = calculator.calculate_atr(history_df, atr_period)
                                    stop_loss = calculator.calculate_atr_stop_loss(
                                        price_or_error, pct, atr_value, atr_multiplier, sma_50, base_price
                                    )
                                except Exception as retry_error:
                                    results.append((price_or_error, ValueError(f"Cannot fetch enough data: {retry_error}")))
                                    continue
                        else:
                            results.append((price_or_error, ValueError("ATR mode requires historical data")))
                            continue
                    elif use_mode == "trailing":
                        # Trailing mode: get high water mark from DB
                        hwm = None
                        if history_db:
                            hwm = history_db.get_high_water_mark(ticker, since_date)
                        stop_loss = calculator.calculate_trailing(
                            price_or_error, pct, high_water_mark=hwm, sma_50=sma_50
                        )
                    else:
                        # Simple mode
                        stop_loss = calculator.calculate_simple(
                            price_or_error, pct, sma_50=sma_50, base_price=base_price
                        )

                    results.append((price_or_error, stop_loss))
                except Exception as e:
                    results.append((price_or_error, e))

        # Display results
        table = create_results_table(results)
        console.print()
        console.print(table)
        console.print()

        # Summary
        successful = sum(1 for _, result in results if not isinstance(result, Exception))
        console.print(
            f"[green]Successfully calculated {successful}/{len(ticker_list)} stop-losses[/green]"
        )

    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(
            "[yellow]Tip: Create a config.toml file or specify tickers as arguments[/yellow]"
        )
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


@app.command()
def version() -> None:
    """Show version information."""
    from trailing_stop_loss import __version__

    console.print(f"trailing-stop-loss version [green]{__version__}[/green]")


if __name__ == "__main__":
    app()
