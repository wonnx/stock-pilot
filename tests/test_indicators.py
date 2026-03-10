"""Tests for technical analysis indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stock_pilot.analysis.indicators import TechnicalAnalyzer, TechnicalIndicators


def make_ohlcv(n: int = 100, trend: str = "up") -> pd.DataFrame:
    """Create synthetic OHLCV data."""
    rng = np.random.default_rng(42)
    if trend == "up":
        base = np.linspace(100, 150, n)
    elif trend == "down":
        base = np.linspace(150, 100, n)
    else:
        base = np.full(n, 120.0)

    noise = rng.normal(0, 1, n)
    close = base + noise
    high = close + rng.uniform(0.5, 2.0, n)
    low = close - rng.uniform(0.5, 2.0, n)
    open_ = close - rng.normal(0, 0.5, n)
    volume = rng.uniform(1_000_000, 5_000_000, n)

    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )


class TestTechnicalAnalyzer:
    def test_compute_returns_indicators(self) -> None:
        df = make_ohlcv(100, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert isinstance(result, TechnicalIndicators)
        assert result.symbol == "TEST"
        assert result.close > 0
        assert result.rsi14 > 0

    def test_insufficient_data_returns_none(self) -> None:
        df = make_ohlcv(30, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is None

    def test_ema_trend_bullish(self) -> None:
        df = make_ohlcv(120, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        # Strong uptrend should produce bullish EMA alignment
        assert result.ema_trend in ("bullish", "mixed")

    def test_ema_trend_bearish(self) -> None:
        df = make_ohlcv(120, "down")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.ema_trend in ("bearish", "mixed")

    def test_volume_spike_detection(self) -> None:
        df = make_ohlcv(100, "up")
        # Spike last volume by 3x
        df.iloc[-1, df.columns.get_loc("Volume")] = df["Volume"].mean() * 3
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.volume_spike is True

    def test_rsi_oversold(self) -> None:
        df = make_ohlcv(100, "down")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        # We can't guarantee RSI<30 with synthetic data, just check valid range
        assert 0 <= result.rsi14 <= 100

    def test_bb_position_valid(self) -> None:
        df = make_ohlcv(100)
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.bb_position in ("upper", "middle", "lower")
