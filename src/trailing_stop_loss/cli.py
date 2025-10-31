"""Beautiful CLI interface using typer and rich."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from trailing_stop_loss.calculator import StopLossCalculator
from trailing_stop_loss.config import Config
from trailing_stop_loss.fetcher import PriceFetcher, StockPrice

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
    table = Table(title="Stop-Loss Calculator Results", show_header=True, header_style="bold cyan")

    table.add_column("Ticker", style="bold", justify="left")
    table.add_column("Current Price", justify="right")
    table.add_column("Stop-Loss Price", justify="right")
    table.add_column("Type", justify="center")
    table.add_column("Percentage", justify="right")
    table.add_column("Risk/Share", justify="right")

    for stock_price, result in results:
        from trailing_stop_loss.calculator import StopLossResult

        if isinstance(result, Exception):
            table.add_row(
                stock_price.ticker if hasattr(stock_price, "ticker") else "?",
                "[red]ERROR[/red]",
                "[red]N/A[/red]",
                "[red]N/A[/red]",
                "[red]N/A[/red]",
                f"[red]{str(result)[:30]}[/red]",
            )
        elif isinstance(result, StopLossResult):
            type_str = "🔄 Trailing" if result.stop_loss_type.value == "trailing" else "📊 Simple"
            price_color = "green" if result.current_price > result.stop_loss_price else "red"

            table.add_row(
                result.ticker,
                f"{result.currency} {result.current_price:.2f}",
                f"[{price_color}]{result.currency} {result.stop_loss_price:.2f}[/{price_color}]",
                type_str,
                result.formatted_percentage,
                result.formatted_risk,
            )

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
        bool | None,
        typer.Option(
            "--trailing/--simple", "-t/-s", help="Use trailing stop-loss (overrides config)"
        ),
    ] = None,
) -> None:
    """Calculate stop-loss prices for configured tickers.

    Examples:
        stop-loss calculate
        stop-loss calculate AAPL GOOGL MSFT
        stop-loss calculate --percentage 7.5 --trailing
        stop-loss calculate TSLA -p 10 --simple
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

        # Determine trailing mode
        use_trailing = trailing if trailing is not None else config.trailing_enabled

        # Initialize components
        fetcher = PriceFetcher()
        calculator = StopLossCalculator()

        # Fetch prices
        console.print(f"[cyan]Fetching prices for {len(ticker_list)} ticker(s)...[/cyan]")
        price_results = fetcher.fetch_multiple(ticker_list, skip_errors=True)

        # Calculate stop-losses
        results: list[tuple[StockPrice | str, object]] = []
        for ticker, price_or_error in price_results.items():
            if isinstance(price_or_error, Exception):
                results.append((ticker, price_or_error))
            else:
                try:
                    stop_loss = calculator.calculate(price_or_error, pct, use_trailing)
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
