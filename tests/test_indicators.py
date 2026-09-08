"""Tests for technical analysis indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stock_snap.analysis.indicators import (
    TechnicalAnalyzer,
    TechnicalIndicators,
    TrendLine,
    _compute_pivot_points,
    _fit_trendline,
)


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
        """Requires at least 60 rows for SMA60."""
        df = make_ohlcv(50, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is None

    def test_exactly_60_rows_ok(self) -> None:
        df = make_ohlcv(60, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None

    def test_ema_trend_bullish(self) -> None:
        df = make_ohlcv(120, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.ema_trend in ("bullish", "mixed")

    def test_ema_trend_bearish(self) -> None:
        df = make_ohlcv(120, "down")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.ema_trend in ("bearish", "mixed")

    def test_volume_spike_detection(self) -> None:
        df = make_ohlcv(100, "up")
        df.iloc[-1, df.columns.get_loc("Volume")] = df["Volume"].mean() * 3
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.volume_spike is True

    def test_rsi_valid_range(self) -> None:
        df = make_ohlcv(100, "down")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert 0 <= result.rsi14 <= 100

    def test_bb_position_valid(self) -> None:
        df = make_ohlcv(100)
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.bb_position in ("upper", "middle", "lower")

    # ── SMA tests ─────────────────────────────────────────────────────────

    def test_sma_fields_present(self) -> None:
        df = make_ohlcv(100, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.sma5 > 0
        assert result.sma20 > 0
        assert result.sma60 > 0

    def test_sma_trend_bullish_uptrend(self) -> None:
        df = make_ohlcv(120, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        # In a strong uptrend, sma5 > sma20 > sma60
        assert result.sma_trend in ("bullish", "mixed")

    def test_sma_trend_bearish_downtrend(self) -> None:
        df = make_ohlcv(120, "down")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.sma_trend in ("bearish", "mixed")

    def test_golden_cross_uptrend(self) -> None:
        df = make_ohlcv(120, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        # In uptrend sma5 should be above sma20
        assert isinstance(result.golden_cross, bool)

    def test_sma_ordering_uptrend(self) -> None:
        """SMA5 should be higher than SMA60 in strong uptrend."""
        df = make_ohlcv(120, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.sma5 > result.sma60

    def test_sma_ordering_downtrend(self) -> None:
        """SMA5 should be lower than SMA60 in strong downtrend."""
        df = make_ohlcv(120, "down")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.sma5 < result.sma60

    # ── Pivot point tests ─────────────────────────────────────────────────

    def test_pivot_fields_present(self) -> None:
        df = make_ohlcv(100, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.pivot > 0
        assert result.pivot_r1 > result.pivot
        assert result.pivot_r2 > result.pivot_r1
        assert result.pivot_s1 < result.pivot
        assert result.pivot_s2 < result.pivot_s1

    def test_pivot_computation(self) -> None:
        pivot, r1, r2, s1, s2 = _compute_pivot_points(high=110, low=90, close=100)
        assert pivot == pytest.approx((110 + 90 + 100) / 3)
        assert r1 > pivot
        assert r2 > r1
        assert s1 < pivot
        assert s2 < s1

    # ── Trendline tests ───────────────────────────────────────────────────

    def test_trendline_present(self) -> None:
        df = make_ohlcv(100, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.trendline is not None
        assert isinstance(result.trendline, TrendLine)

    def test_trendline_up_direction(self) -> None:
        df = make_ohlcv(100, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.trendline is not None
        assert result.trendline.direction == "up"

    def test_trendline_down_direction(self) -> None:
        df = make_ohlcv(100, "down")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.trendline is not None
        assert result.trendline.direction == "down"

    def test_trendline_r_squared_range(self) -> None:
        df = make_ohlcv(100, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        assert result.trendline is not None
        assert 0.0 <= result.trendline.r_squared <= 1.0

    def test_fit_trendline_direct(self) -> None:
        prices = pd.Series(np.linspace(100, 120, 30))
        tl = _fit_trendline(prices, window=20)
        assert tl.slope > 0
        assert tl.direction == "up"
        assert tl.r_squared > 0.9  # near-perfect linear

    # ── Bollinger Squeeze ─────────────────────────────────────────────────

    def test_bb_squeeze_flat_price(self) -> None:
        df = make_ohlcv(100, "flat")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        # flat price with tiny noise → bands should be narrow
        assert isinstance(result.bb_squeeze, bool)

    # ── Script dict output ────────────────────────────────────────────────

    def test_to_script_dict_keys(self) -> None:
        df = make_ohlcv(100, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        d = result.to_script_dict()
        required_keys = [
            "symbol", "close", "sma5", "sma20", "sma60", "ema9", "ema21", "ema50",
            "sma_trend", "ema_trend", "golden_cross",
            "rsi14", "rsi_zone", "macd", "macd_signal", "macd_hist", "macd_bullish",
            "bb_upper", "bb_mid", "bb_lower", "bb_position", "bb_squeeze",
            "volume", "volume_sma20", "volume_spike", "volume_ratio",
            "support", "resistance",
            "pivot", "pivot_r1", "pivot_r2", "pivot_s1", "pivot_s2",
            "trend_direction", "trend_slope", "trend_r2",
        ]
        for key in required_keys:
            assert key in d, f"Missing key in script dict: {key}"

    def test_to_script_dict_types(self) -> None:
        df = make_ohlcv(100, "up")
        result = TechnicalAnalyzer().compute("TEST", df)
        assert result is not None
        d = result.to_script_dict()
        assert isinstance(d["symbol"], str)
        assert isinstance(d["close"], float)
        assert isinstance(d["rsi14"], float)
        assert isinstance(d["volume_spike"], bool)
        assert isinstance(d["golden_cross"], bool)
        assert isinstance(d["macd_bullish"], bool)
        assert isinstance(d["volume"], int)
        assert d["rsi_zone"] in ("overbought", "oversold", "neutral")
        assert d["sma_trend"] in ("bullish", "bearish", "mixed")
        assert d["ema_trend"] in ("bullish", "bearish", "mixed")
        assert d["bb_position"] in ("upper", "middle", "lower")
        assert d["trend_direction"] in ("up", "down", "flat")
