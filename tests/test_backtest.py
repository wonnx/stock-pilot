"""Tests for the backtesting engine."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stock_pilot.backtest.engine import BacktestEngine, BacktestResult


def make_trending_ohlcv(n: int = 200, trend: str = "up") -> pd.DataFrame:
    rng = np.random.default_rng(0)
    if trend == "up":
        base = np.linspace(100, 200, n)
    else:
        base = np.linspace(200, 100, n)
    close = base + rng.normal(0, 2, n)
    high = close + rng.uniform(0.5, 3, n)
    low = close - rng.uniform(0.5, 3, n)
    open_ = close - rng.normal(0, 1, n)
    volume = rng.uniform(500_000, 2_000_000, n)
    idx = pd.date_range("2023-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )


class TestBacktestEngine:
    def test_run_returns_result(self) -> None:
        df = make_trending_ohlcv(200)
        result = BacktestEngine().run("TEST", df)
        assert isinstance(result, BacktestResult)
        assert result.symbol == "TEST"

    def test_win_rate_between_0_and_1(self) -> None:
        df = make_trending_ohlcv(200)
        result = BacktestEngine().run("TEST", df)
        assert 0.0 <= result.win_rate <= 1.0

    def test_no_trades_on_short_data(self) -> None:
        df = make_trending_ohlcv(50)  # less than window (60)
        result = BacktestEngine().run("TEST", df)
        assert result.total_trades == 0

    def test_wins_plus_losses_equals_total(self) -> None:
        df = make_trending_ohlcv(200)
        result = BacktestEngine().run("TEST", df)
        assert result.wins + result.losses == result.total_trades

    def test_max_drawdown_non_negative(self) -> None:
        df = make_trending_ohlcv(200)
        result = BacktestEngine().run("TEST", df)
        assert result.max_drawdown_pct >= 0
