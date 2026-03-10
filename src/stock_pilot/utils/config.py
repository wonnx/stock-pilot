"""Configuration management using environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")


class Config:
    """Centralized configuration from environment variables."""

    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    SCAN_INTERVAL_MINUTES: int = int(os.getenv("SCAN_INTERVAL_MINUTES", "15"))

    # Default watchlist of US stocks (short/swing trading candidates)
    DEFAULT_WATCHLIST: list[str] = [
        "AAPL", "MSFT", "NVDA", "TSLA", "AMZN",
        "META", "GOOGL", "AMD", "PLTR", "SOFI",
        "SPY", "QQQ", "SQQQ", "TQQQ",
    ]

    @classmethod
    def validate(cls) -> None:
        """Raise if required keys are missing."""
        missing = []
        if not cls.ANTHROPIC_API_KEY:
            missing.append("ANTHROPIC_API_KEY")
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not cls.TELEGRAM_CHAT_ID:
            missing.append("TELEGRAM_CHAT_ID")
        if missing:
            raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")


config = Config()
