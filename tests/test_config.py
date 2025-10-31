"""Tests for configuration loading."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from trailing_stop_loss.config import Config


def test_config_loading() -> None:
    """Test loading a valid config file."""
    config_content = """
tickers = ["AAPL", "GOOGL"]
stop_loss_percentage = 7.5
trailing_enabled = true
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config_path = Path(f.name)

    try:
        config = Config(config_path)
        assert config.tickers == ["AAPL", "GOOGL"]
        assert config.stop_loss_percentage == 7.5
        assert config.trailing_enabled is True
    finally:
        config_path.unlink()


def test_config_defaults() -> None:
    """Test default values when fields are missing."""
    config_content = """
# Minimal config
"""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config_path = Path(f.name)

    try:
        config = Config(config_path)
        assert config.tickers == []
        assert config.stop_loss_percentage == 5.0
        assert config.trailing_enabled is False
    finally:
        config_path.unlink()


def test_config_file_not_found() -> None:
    """Test error when config file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        Config("nonexistent.toml")


def test_config_invalid_toml() -> None:
    """Test error when config file is invalid TOML."""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("invalid [ toml content")
        f.flush()
        config_path = Path(f.name)

    try:
        with pytest.raises(ValueError):
            Config(config_path)
    finally:
        config_path.unlink()
