"""Technical analysis indicators using pandas-ta."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import pandas_ta as ta  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


@dataclass
class TrendLine:
    """Linear trendline fitted to price data."""

    slope: float       # price change per day (positive = uptrend)
    intercept: float   # price at index 0
    r_squared: float   # goodness of fit (0-1)
    direction: str     # "up" | "down" | "flat"


@dataclass
class TechnicalIndicators:
    """Computed technical indicators for a symbol."""

    symbol: str
    close: float
    # EMAs
    ema9: float
    ema21: float
    ema50: float
    # SMAs (MA 5/20/60)
    sma5: float
    sma20: float
    sma60: float
    # RSI
    rsi14: float
    # MACD
    macd: float
    macd_signal: float
    macd_hist: float
    # Bollinger Bands
    bb_upper: float
    bb_mid: float
    bb_lower: float
    # Volume
    volume: float
    volume_sma20: float
    # Support / Resistance
    support: float
    resistance: float
    # Pivot points (classic)
    pivot: float = 0.0
    pivot_r1: float = 0.0
    pivot_r2: float = 0.0
    pivot_s1: float = 0.0
    pivot_s2: float = 0.0
    # Trendline (20-day)
    trendline: TrendLine | None = None
    extra: dict[str, float] = field(default_factory=dict)

    # ── derived properties ──────────────────────────────────────────────────

    @property
    def ema_trend(self) -> str:
        """Bullish if 9 > 21 > 50, bearish otherwise."""
        if self.ema9 > self.ema21 > self.ema50:
            return "bullish"
        if self.ema9 < self.ema21 < self.ema50:
            return "bearish"
        return "mixed"

    @property
    def sma_trend(self) -> str:
        """MA 5/20/60 alignment: bullish if 5 > 20 > 60."""
        if self.sma5 > self.sma20 > self.sma60:
            return "bullish"
        if self.sma5 < self.sma20 < self.sma60:
            return "bearish"
        return "mixed"

    @property
    def golden_cross(self) -> bool:
        """True if SMA5 > SMA20 (short-term bullish crossover)."""
        return self.sma5 > self.sma20

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
    def bb_squeeze(self) -> bool:
        """True if band width < 5% of mid price (volatility compression)."""
        if self.bb_mid <= 0:
            return False
        return (self.bb_upper - self.bb_lower) / self.bb_mid < 0.05

    @property
    def rsi_zone(self) -> str:
        if self.rsi14 >= 70:
            return "overbought"
        if self.rsi14 <= 30:
            return "oversold"
        return "neutral"

    def to_script_dict(self) -> dict[str, object]:
        """Return a flat dict suitable for video script / Remotion template data."""
        return {
            "symbol": self.symbol,
            "close": round(self.close, 2),
            # MAs
            "sma5": round(self.sma5, 2),
            "sma20": round(self.sma20, 2),
            "sma60": round(self.sma60, 2),
            "ema9": round(self.ema9, 2),
            "ema21": round(self.ema21, 2),
            "ema50": round(self.ema50, 2),
            "sma_trend": self.sma_trend,
            "ema_trend": self.ema_trend,
            "golden_cross": self.golden_cross,
            # RSI
            "rsi14": round(self.rsi14, 1),
            "rsi_zone": self.rsi_zone,
            # MACD
            "macd": round(self.macd, 4),
            "macd_signal": round(self.macd_signal, 4),
            "macd_hist": round(self.macd_hist, 4),
            "macd_bullish": self.macd_hist > 0,
            # Bollinger Bands
            "bb_upper": round(self.bb_upper, 2),
            "bb_mid": round(self.bb_mid, 2),
            "bb_lower": round(self.bb_lower, 2),
            "bb_position": self.bb_position,
            "bb_squeeze": self.bb_squeeze,
            # Volume
            "volume": int(self.volume),
            "volume_sma20": int(self.volume_sma20),
            "volume_spike": self.volume_spike,
            "volume_ratio": round(self.volume / self.volume_sma20, 2) if self.volume_sma20 > 0 else 1.0,
            # Support / Resistance
            "support": round(self.support, 2),
            "resistance": round(self.resistance, 2),
            # Pivot points
            "pivot": round(self.pivot, 2),
            "pivot_r1": round(self.pivot_r1, 2),
            "pivot_r2": round(self.pivot_r2, 2),
            "pivot_s1": round(self.pivot_s1, 2),
            "pivot_s2": round(self.pivot_s2, 2),
            # Trendline
            "trend_direction": self.trendline.direction if self.trendline else "flat",
            "trend_slope": round(self.trendline.slope, 4) if self.trendline else 0.0,
            "trend_r2": round(self.trendline.r_squared, 3) if self.trendline else 0.0,
        }


def _fit_trendline(prices: pd.Series, window: int = 20) -> TrendLine:
    """Fit a linear trendline to the last `window` closing prices."""
    y = prices.iloc[-window:].values.astype(float)
    x = np.arange(len(y), dtype=float)
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = float(coeffs[0]), float(coeffs[1])
    y_hat = slope * x + intercept
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    if slope > 0.05 * (y.mean() / len(y)):
        direction = "up"
    elif slope < -0.05 * (y.mean() / len(y)):
        direction = "down"
    else:
        direction = "flat"

    return TrendLine(slope=slope, intercept=intercept, r_squared=max(0.0, r_squared), direction=direction)


def _compute_pivot_points(high: float, low: float, close: float) -> tuple[float, float, float, float, float]:
    """Classic pivot point calculation from the previous period H/L/C."""
    pivot = (high + low + close) / 3.0
    r1 = 2 * pivot - low
    r2 = pivot + (high - low)
    s1 = 2 * pivot - high
    s2 = pivot - (high - low)
    return pivot, r1, r2, s1, s2


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
        if len(df) < 60:
            logger.warning("%s: not enough rows (%d < 60)", symbol, len(df))
            return None

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # EMAs
        ema9 = ta.ema(close, length=9)
        ema21 = ta.ema(close, length=21)
        ema50 = ta.ema(close, length=50)

        # SMAs (MA 5/20/60)
        sma5 = ta.sma(close, length=5)
        sma20 = ta.sma(close, length=20)
        sma60 = ta.sma(close, length=60)

        # RSI
        rsi = ta.rsi(close, length=14)

        # MACD
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)

        # Bollinger Bands
        bb_df = ta.bbands(close, length=20, std=2)

        # Volume SMA
        vol_sma = ta.sma(volume, length=20)

        # Support / Resistance: rolling 20-day low/high
        support = float(low.rolling(window=20).min().iloc[-1])
        resistance = float(high.rolling(window=20).max().iloc[-1])

        # Pivot points (using previous day's H/L/C)
        prev_high = float(high.iloc[-2]) if len(df) >= 2 else float(high.iloc[-1])
        prev_low = float(low.iloc[-2]) if len(df) >= 2 else float(low.iloc[-1])
        prev_close = float(close.iloc[-2]) if len(df) >= 2 else float(close.iloc[-1])
        pivot, r1, r2, s1, s2 = _compute_pivot_points(prev_high, prev_low, prev_close)

        # Trendline (20-day)
        trendline: TrendLine | None = None
        if len(df) >= 20:
            trendline = _fit_trendline(close, window=20)

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
            sma5=last(sma5),
            sma20=last(sma20),
            sma60=last(sma60),
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
            pivot=pivot,
            pivot_r1=r1,
            pivot_r2=r2,
            pivot_s1=s1,
            pivot_s2=s2,
            trendline=trendline,
        )


analyzer = TechnicalAnalyzer()
