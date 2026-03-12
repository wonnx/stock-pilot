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
    KAKAO_ACCESS_TOKEN: str = os.getenv("KAKAO_ACCESS_TOKEN", "")
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
    SCAN_INTERVAL_MINUTES: int = int(os.getenv("SCAN_INTERVAL_MINUTES", "15"))

    # Telegram bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # Instagram Graph API
    INSTAGRAM_ACCESS_TOKEN: str = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_USER_ID: str = os.getenv("INSTAGRAM_USER_ID", "")

    # YouTube Data API v3
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    YOUTUBE_OAUTH_TOKEN: str = os.getenv("YOUTUBE_OAUTH_TOKEN", "")

    # ElevenLabs TTS (optional, edge-tts used as free default)
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")

    # Content generation schedule (24h format, market close + buffer)
    CONTENT_SCHEDULE_TIME: str = os.getenv("CONTENT_SCHEDULE_TIME", "17:00")  # 4PM ET market close + 1h
    CONTENT_OUTPUT_DIR: str = os.getenv("CONTENT_OUTPUT_DIR", "output")
    CONTENT_TOP_N: int = int(os.getenv("CONTENT_TOP_N", "3"))  # top N signals per day

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
        if not cls.KAKAO_ACCESS_TOKEN:
            missing.append("KAKAO_ACCESS_TOKEN")
        if missing:
            raise OSError(f"Missing required env vars: {', '.join(missing)}")


config = Config()
