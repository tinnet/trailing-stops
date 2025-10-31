"""Configuration loading for trailing stop loss."""

import tomllib
from pathlib import Path
from typing import Any


class Config:
    """Configuration for stop-loss calculations."""

    def __init__(self, config_path: Path | str = "config.toml") -> None:
        """Initialize configuration from TOML file.

        Args:
            config_path: Path to the TOML configuration file.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If config file is invalid.
        """
        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from TOML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse config file: {e}") from e

    @property
    def tickers(self) -> list[str]:
        """Get list of ticker symbols to track."""
        return self._config.get("tickers", [])

    @property
    def stop_loss_percentage(self) -> float:
        """Get default stop-loss percentage (0-100)."""
        return self._config.get("stop_loss_percentage", 5.0)

    @property
    def trailing_enabled(self) -> bool:
        """Check if trailing stop-loss is enabled by default."""
        return self._config.get("trailing_enabled", False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key."""
        return self._config.get(key, default)
