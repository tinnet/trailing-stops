"""Price history storage and retrieval using SQLite."""

import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd


class PriceHistoryDB:
    """Manage historical price data in SQLite."""

    def __init__(self, db_path: Path | str = ".data/price_history.db") -> None:
        """Initialize the price history database.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    ticker TEXT NOT NULL,
                    date DATE NOT NULL,
                    open REAL,
                    high REAL NOT NULL,
                    low REAL,
                    close REAL NOT NULL,
                    volume INTEGER,
                    PRIMARY KEY (ticker, date)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticker_date
                ON price_history(ticker, date)
            """)
            conn.commit()

    def store_history(self, ticker: str, history_df: pd.DataFrame) -> int:
        """Store historical price data from a DataFrame.

        Args:
            ticker: Stock ticker symbol.
            history_df: DataFrame with columns: Open, High, Low, Close, Volume
                       and DatetimeIndex.

        Returns:
            Number of rows inserted (duplicates are ignored).
        """
        if history_df.empty:
            return 0

        # Prepare data for insertion
        records = []
        for date_val, row in history_df.iterrows():
            # Convert pandas Timestamp to date string
            date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else str(date_val)
            records.append(
                (
                    ticker.upper(),
                    date_str,
                    float(row.get("Open", 0)) or None,
                    float(row["High"]),
                    float(row.get("Low", 0)) or None,
                    float(row["Close"]),
                    int(row.get("Volume", 0)) if pd.notna(row.get("Volume")) else None,
                )
            )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.executemany(
                """
                INSERT OR IGNORE INTO price_history
                (ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )
            conn.commit()
            return cursor.rowcount

    def store_current_price(
        self, ticker: str, price: float, timestamp: datetime | None = None
    ) -> bool:
        """Store current price as today's data point.

        Args:
            ticker: Stock ticker symbol.
            price: Current price (used as high, low, and close).
            timestamp: Timestamp of the price (defaults to now).

        Returns:
            True if inserted, False if already exists for today.
        """
        if timestamp is None:
            timestamp = datetime.now()

        date_str = timestamp.strftime("%Y-%m-%d")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO price_history
                (ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, NULL)
                """,
                (ticker.upper(), date_str, price, price, price, price),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_high_water_mark(
        self, ticker: str, since_date: date | str | None = None
    ) -> float | None:
        """Get the highest price for a ticker since a given date.

        Args:
            ticker: Stock ticker symbol.
            since_date: Start date for calculation. If None, uses all available data.

        Returns:
            Maximum high price, or None if no data exists.
        """
        query = "SELECT MAX(high) FROM price_history WHERE ticker = ?"
        params: tuple = (ticker.upper(),)

        if since_date:
            query += " AND date >= ?"
            date_str = since_date if isinstance(since_date, str) else since_date.strftime("%Y-%m-%d")
            params = (ticker.upper(), date_str)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else None

    def get_last_update_date(self, ticker: str) -> date | None:
        """Get the most recent date for which we have data.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Most recent date, or None if no data exists.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT MAX(date) FROM price_history WHERE ticker = ?",
                (ticker.upper(),),
            )
            result = cursor.fetchone()
            if result and result[0]:
                return datetime.strptime(result[0], "%Y-%m-%d").date()
            return None

    def has_data(self, ticker: str) -> bool:
        """Check if we have any historical data for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            True if data exists, False otherwise.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM price_history WHERE ticker = ?",
                (ticker.upper(),),
            )
            result = cursor.fetchone()
            return result[0] > 0 if result else False

    def delete_ticker_history(self, ticker: str) -> int:
        """Delete all historical data for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Number of rows deleted.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM price_history WHERE ticker = ?",
                (ticker.upper(),),
            )
            conn.commit()
            return cursor.rowcount

    def get_history(
        self, ticker: str, since_date: date | str | None = None
    ) -> list[dict[str, str | float | int | None]]:
        """Retrieve historical price data for a ticker.

        Args:
            ticker: Stock ticker symbol.
            since_date: Start date for retrieval. If None, gets all data.

        Returns:
            List of price records as dictionaries.
        """
        query = """
            SELECT ticker, date, open, high, low, close, volume
            FROM price_history
            WHERE ticker = ?
        """
        params: tuple = (ticker.upper(),)

        if since_date:
            query += " AND date >= ?"
            date_str = since_date if isinstance(since_date, str) else since_date.strftime("%Y-%m-%d")
            params = (ticker.upper(), date_str)

        query += " ORDER BY date ASC"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            columns = ["ticker", "date", "open", "high", "low", "close", "volume"]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
