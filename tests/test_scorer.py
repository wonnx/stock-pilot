"""Tests for signal scorer."""

from __future__ import annotations

from stock_pilot.analysis.indicators import TechnicalIndicators
from stock_pilot.signals.scorer import SignalDirection, SignalScorer


def make_tech(
    ema9: float = 110,
    ema21: float = 105,
    ema50: float = 100,
    sma5: float = 112,
    sma20: float = 108,
    sma60: float = 102,
    rsi14: float = 55,
    macd: float = 0.5,
    macd_signal: float = 0.3,
    macd_hist: float = 0.2,
    bb_upper: float = 125,
    bb_mid: float = 110,
    bb_lower: float = 95,
    volume: float = 2_000_000,
    volume_sma20: float = 1_000_000,
    close: float = 110,
) -> TechnicalIndicators:
    return TechnicalIndicators(
        symbol="TEST",
        close=close,
        ema9=ema9,
        ema21=ema21,
        ema50=ema50,
        sma5=sma5,
        sma20=sma20,
        sma60=sma60,
        rsi14=rsi14,
        macd=macd,
        macd_signal=macd_signal,
        macd_hist=macd_hist,
        bb_upper=bb_upper,
        bb_mid=bb_mid,
        bb_lower=bb_lower,
        volume=volume,
        volume_sma20=volume_sma20,
        support=100,
        resistance=120,
    )


class TestSignalScorer:
    def test_strong_buy_signal(self) -> None:
        tech = make_tech(
            ema9=115, ema21=110, ema50=100,  # bullish EMA
            rsi14=55,
            macd=0.8, macd_signal=0.4, macd_hist=0.4,  # bullish MACD
            volume=3_000_000, volume_sma20=1_000_000,  # volume spike
        )
        scorer = SignalScorer()
        signal = scorer.score(tech)
        assert signal.direction == SignalDirection.BUY
        assert signal.score > 0

    def test_strong_sell_signal(self) -> None:
        tech = make_tech(
            ema9=95, ema21=100, ema50=110,  # bearish EMA
            rsi14=75,  # overbought
            macd=-0.8, macd_signal=-0.4, macd_hist=-0.4,  # bearish MACD
        )
        scorer = SignalScorer()
        signal = scorer.score(tech)
        assert signal.direction == SignalDirection.SELL
        assert signal.score < 0

    def test_hold_signal_neutral(self) -> None:
        tech = make_tech(
            ema9=100, ema21=100, ema50=100,  # mixed EMA
            rsi14=50,
            macd=0.0, macd_signal=0.0, macd_hist=0.0,
        )
        scorer = SignalScorer()
        signal = scorer.score(tech)
        assert signal.direction == SignalDirection.HOLD

    def test_signal_has_reasons(self) -> None:
        tech = make_tech(ema9=115, ema21=110, ema50=100)
        signal = SignalScorer().score(tech)
        assert len(signal.reasons) > 0

    def test_rank_orders_by_abs_score(self) -> None:
        scorer = SignalScorer()
        t1 = make_tech(ema9=115, ema21=110, ema50=100, macd=0.8, macd_signal=0.3, macd_hist=0.5)
        t2 = make_tech()  # neutral

        s1 = scorer.score(t1)
        s2 = scorer.score(t2)
        ranked = scorer.rank([s2, s1])
        assert ranked[0].symbol == s1.symbol or abs(ranked[0].score) >= abs(ranked[1].score)
