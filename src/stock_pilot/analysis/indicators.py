"""Technical analysis indicators using pandas-ta."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd
import pandas_ta as ta  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


@dataclass
class TechnicalIndicators:
    """Computed technical indicators for a symbol."""

    symbol: str
    close: float
    ema9: float
    ema21: float
    ema50: float
    rsi14: float
    macd: float
    macd_signal: float
    macd_hist: float
    bb_upper: float
    bb_mid: float
    bb_lower: float
    volume: float
    volume_sma20: float
    support: float
    resistance: float
    extra: dict[str, float] = field(default_factory=dict)

    @property
    def ema_trend(self) -> str:
        """Bullish if 9 > 21 > 50, bearish otherwise."""
        if self.ema9 > self.ema21 > self.ema50:
            return "bullish"
        if self.ema9 < self.ema21 < self.ema50:
            return "bearish"
        return "mixed"

    @property
    def volume_spike(self) -> bool:
        """True if current volume > 2x 20-day average."""
        if self.volume_sma20 <= 0:
            return False
        return self.volume >= 2.0 * self.volume_sma20

    @property
    def bb_position(self) -> str:
        """Where price sits relative to Bollinger Bands."""
        band_width = self.bb_upper - self.bb_lower
        if band_width <= 0:
            return "middle"
        pos = (self.close - self.bb_lower) / band_width
        if pos >= 0.8:
            return "upper"
        if pos <= 0.2:
            return "lower"
        return "middle"

    @property
    def rsi_zone(self) -> str:
        if self.rsi14 >= 70:
            return "overbought"
        if self.rsi14 <= 30:
            return "oversold"
        return "neutral"


class TechnicalAnalyzer:
    """Compute technical indicators from OHLCV DataFrames."""

    def compute(self, symbol: str, df: pd.DataFrame) -> TechnicalIndicators | None:
        """
        Compute all indicators from an OHLCV DataFrame.

        Args:
            symbol: Ticker symbol
            df: DataFrame with Open, High, Low, Close, Volume columns

        Returns:
            TechnicalIndicators or None if data is insufficient
        """
        if len(df) < 50:
            logger.warning("%s: not enough rows (%d < 50)", symbol, len(df))
            return None

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # EMAs
        ema9 = ta.ema(close, length=9)
        ema21 = ta.ema(close, length=21)
        ema50 = ta.ema(close, length=50)

        # RSI
        rsi = ta.rsi(close, length=14)

        # MACD
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)

        # Bollinger Bands
        bb_df = ta.bbands(close, length=20, std=2)

        # Volume SMA
        vol_sma = ta.sma(volume, length=20)

        # Support / Resistance (rolling 20-day low/high as simple proxy)
        support = float(low.rolling(window=20).min().iloc[-1])
        resistance = float(high.rolling(window=20).max().iloc[-1])

        try:
            macd_col = [c for c in macd_df.columns if c.startswith("MACD_") and "h" not in c.lower() and "s" not in c.lower()][0]
            signal_col = [c for c in macd_df.columns if "MACDs" in c][0]
            hist_col = [c for c in macd_df.columns if "MACDh" in c][0]
            bb_upper_col = [c for c in bb_df.columns if "BBU" in c][0]
            bb_mid_col = [c for c in bb_df.columns if "BBM" in c][0]
            bb_lower_col = [c for c in bb_df.columns if "BBL" in c][0]
        except (IndexError, AttributeError) as e:
            logger.error("%s: could not find indicator columns: %s", symbol, e)
            return None

        def last(series: pd.Series) -> float:
            val = series.iloc[-1]
            return float(val) if pd.notna(val) else 0.0

        return TechnicalIndicators(
            symbol=symbol,
            close=last(close),
            ema9=last(ema9),
            ema21=last(ema21),
            ema50=last(ema50),
            rsi14=last(rsi),
            macd=last(macd_df[macd_col]),
            macd_signal=last(macd_df[signal_col]),
            macd_hist=last(macd_df[hist_col]),
            bb_upper=last(bb_df[bb_upper_col]),
            bb_mid=last(bb_df[bb_mid_col]),
            bb_lower=last(bb_df[bb_lower_col]),
            volume=last(volume),
            volume_sma20=last(vol_sma),
            support=support,
            resistance=resistance,
        )


analyzer = TechnicalAnalyzer()
