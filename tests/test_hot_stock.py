"""Tests for hot stock selection module."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd

from stock_pilot.hot_stock import (
    HotStockResult,
    _build_results,
    _score,
    select_hot_stock,
    select_top_n,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_price_series(n: int, start: float, end: float) -> np.ndarray:
    return np.linspace(start, end, n)


def make_single_ohlcv(
    n: int = 25,
    close_start: float = 100.0,
    close_end: float = 110.0,
    vol_spike_last: bool = False,
) -> pd.DataFrame:
    """Synthetic single-ticker OHLCV DataFrame."""
    close = make_price_series(n, close_start, close_end)
    volume = np.full(n, 1_000_000.0)
    if vol_spike_last:
        volume[-1] = 3_500_000.0

    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "Open": close - 0.5,
            "High": close + 1.0,
            "Low": close - 1.0,
            "Close": close,
            "Volume": volume,
        },
        index=idx,
    )


def make_multi_ohlcv(
    symbols: list[str],
    n: int = 25,
) -> pd.DataFrame:
    """Synthetic multi-ticker MultiIndex DataFrame mimicking yfinance group_by='ticker'."""
    frames = {}
    for i, sym in enumerate(symbols):
        start = 100.0 + i * 10
        end = start * (1 + (i + 1) * 0.02)  # each ticker has increasing change
        df = make_single_ohlcv(n, close_start=start, close_end=end, vol_spike_last=(i == len(symbols) - 1))
        frames[sym] = df

    combined = pd.concat(frames, axis=1)
    # combined.columns is MultiIndex: (ticker, price_col)
    return combined


# ---------------------------------------------------------------------------
# Unit tests: _score
# ---------------------------------------------------------------------------

class TestScore:
    def test_zero_change_zero_vol_ratio(self) -> None:
        assert _score(0.0, 1.0) == 0.0

    def test_five_pct_change_gives_50_price_score(self) -> None:
        score = _score(5.0, 1.0)
        assert score == 50.0  # price_score=50 (capped at 50), vol_score=0 (ratio=1.0 → no bonus)

    def test_negative_change_uses_abs(self) -> None:
        assert _score(-5.0, 1.0) == _score(5.0, 1.0)

    def test_vol_ratio_3x_gives_50_vol_score(self) -> None:
        # price=0, vol: (3-1)/2 * 50 = 50
        assert _score(0.0, 3.0) == 50.0

    def test_max_score_is_100(self) -> None:
        score = _score(100.0, 100.0)
        assert score == 100.0

    def test_vol_below_average_gives_zero_vol_score(self) -> None:
        # volume_ratio = 0.5 (below average) — no vol bonus
        assert _score(0.0, 0.5) == 0.0

    def test_partial_change_and_vol(self) -> None:
        # 2.5% → price_score = 25; vol_ratio=2 → (2-1)/2*50=25; total=50
        assert _score(2.5, 2.0) == 50.0


# ---------------------------------------------------------------------------
# Unit tests: _build_results
# ---------------------------------------------------------------------------

class TestBuildResults:
    def test_single_ticker_returns_result(self) -> None:
        df = make_single_ohlcv(25)
        results = _build_results(df, ["TEST"])
        assert len(results) == 1
        r = results[0]
        assert r.symbol == "TEST"
        assert r.price > 0
        assert r.prev_close > 0
        assert r.avg_volume > 0
        assert 0.0 <= r.hot_score <= 100.0

    def test_multi_ticker_returns_all(self) -> None:
        symbols = ["AAPL", "MSFT", "NVDA"]
        raw = make_multi_ohlcv(symbols)
        results = _build_results(raw, symbols)
        assert len(results) == len(symbols)
        syms = {r.symbol for r in results}
        assert syms == set(symbols)

    def test_volume_spike_increases_score(self) -> None:
        df_normal = make_single_ohlcv(25, vol_spike_last=False)
        df_spike = make_single_ohlcv(25, vol_spike_last=True)

        r_normal = _build_results(df_normal, ["TEST"])[0]
        r_spike = _build_results(df_spike, ["TEST"])[0]

        assert r_spike.hot_score > r_normal.hot_score
        assert r_spike.volume_ratio > r_normal.volume_ratio

    def test_rising_stock_direction_is_상승(self) -> None:
        df = make_single_ohlcv(25, close_start=100, close_end=115)
        results = _build_results(df, ["UP"])
        assert results[0].direction == "상승"
        assert results[0].change_pct > 0

    def test_falling_stock_direction_is_하락(self) -> None:
        df = make_single_ohlcv(25, close_start=115, close_end=100)
        results = _build_results(df, ["DOWN"])
        assert results[0].direction == "하락"
        assert results[0].change_pct < 0

    def test_insufficient_data_skipped(self) -> None:
        df = make_single_ohlcv(1)  # only 1 row — not enough
        results = _build_results(df, ["TEST"])
        assert results == []

    def test_avg_volume_excludes_today(self) -> None:
        """avg_volume should be based on prior days, not today's spike."""
        df = make_single_ohlcv(25, vol_spike_last=True)
        results = _build_results(df, ["TEST"])
        r = results[0]
        # today's volume is 3.5M, avg of prior 20 days should be ~1M
        assert r.avg_volume < 2_000_000
        assert r.volume > r.avg_volume


# ---------------------------------------------------------------------------
# Integration tests: select_hot_stock / select_top_n (with mocked download)
# ---------------------------------------------------------------------------

class TestSelectHotStock:
    def _mock_download_single(self) -> pd.DataFrame:
        return make_single_ohlcv(25, close_start=100, close_end=110, vol_spike_last=True)

    def test_returns_hot_stock_result(self) -> None:
        with patch("stock_pilot.hot_stock._download", return_value=self._mock_download_single()):
            result = select_hot_stock(universe=["NVDA"])
        assert result is not None
        assert isinstance(result, HotStockResult)
        assert result.symbol == "NVDA"

    def test_returns_none_on_download_failure(self) -> None:
        with patch("stock_pilot.hot_stock._download", return_value=None):
            result = select_hot_stock(universe=["AAPL"])
        assert result is None

    def test_returns_none_on_empty_dataframe(self) -> None:
        with patch("stock_pilot.hot_stock._download", return_value=pd.DataFrame()):
            result = select_hot_stock(universe=["AAPL"])
        assert result is None


class TestSelectTopN:
    def _mock_download_multi(self, symbols: list[str]) -> pd.DataFrame:
        return make_multi_ohlcv(symbols)

    def test_top_n_returns_n_results(self) -> None:
        symbols = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD"]
        raw = make_multi_ohlcv(symbols)
        with patch("stock_pilot.hot_stock._download", return_value=raw):
            results = select_top_n(n=3, universe=symbols)
        assert len(results) == 3

    def test_results_sorted_by_score_descending(self) -> None:
        symbols = ["AAPL", "MSFT", "NVDA"]
        raw = make_multi_ohlcv(symbols)
        with patch("stock_pilot.hot_stock._download", return_value=raw):
            results = select_top_n(n=3, universe=symbols)
        scores = [r.hot_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_top_n_larger_than_universe(self) -> None:
        symbols = ["AAPL", "MSFT"]
        raw = make_multi_ohlcv(symbols)
        with patch("stock_pilot.hot_stock._download", return_value=raw):
            results = select_top_n(n=10, universe=symbols)
        # Can't return more than available symbols
        assert len(results) <= len(symbols)

    def test_empty_on_download_failure(self) -> None:
        with patch("stock_pilot.hot_stock._download", return_value=None):
            results = select_top_n(n=5, universe=["AAPL"])
        assert results == []

    def test_select_hot_stock_uses_top_1(self) -> None:
        symbols = ["AAPL", "MSFT", "NVDA"]
        raw = make_multi_ohlcv(symbols)
        with patch("stock_pilot.hot_stock._download", return_value=raw):
            top1 = select_hot_stock(universe=symbols)
            top_n = select_top_n(n=1, universe=symbols)
        assert top1 is not None
        assert len(top_n) == 1
        assert top1.symbol == top_n[0].symbol
        assert top1.hot_score == top_n[0].hot_score
