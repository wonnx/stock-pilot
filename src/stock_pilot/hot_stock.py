"""Hot stock auto-selection module.

Uses yfinance real-time data to automatically select the most notable US stock.
Criteria: composite score of price change % + volume spike ratio (industry-standard 20-day avg volume).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

# Scan universe (S&P 500 representatives + popular thematic stocks)
SCAN_UNIVERSE: list[str] = [
    # Large-cap tech
    "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "GOOG",
    "AMD", "INTC", "QCOM", "AVGO", "ORCL", "CRM", "SNOW", "PLTR",
    # Fintech / Biotech / AI
    "SOFI", "HOOD", "COIN", "MRNA", "BNTX", "LLY", "ABBV", "PFE",
    # ETFs (including leveraged)
    "SPY", "QQQ", "TQQQ", "SQQQ", "ARKK",
    # Energy / Materials
    "XOM", "CVX", "FCX", "NEM",
    # Consumer / Entertainment
    "NFLX", "DIS", "SBUX", "NKE", "UBER", "LYFT",
]

# Minimum data rows needed for 20-day average volume calculation
_MIN_ROWS = 2
# Average volume calculation window (industry standard)
_VOL_AVG_WINDOW = 20


@dataclass
class HotStockResult:
    symbol: str
    price: float
    prev_close: float
    change_pct: float
    volume: int
    avg_volume: int
    volume_ratio: float  # current volume / 20-day average volume
    hot_score: float     # composite hot score (0-100)
    direction: str       # "rising" | "falling" | "flat"


def _score(change_pct: float, volume_ratio: float) -> float:
    """Calculate hot score from price change % and volume ratio (0-100).

    - Price score: max 50 points based on absolute value (5%+ = max)
    - Volume spike score: max 50 points (3x+ = max, below 1x = 0)
    """
    price_score = min(abs(change_pct) / 5.0 * 50, 50)
    vol_score = min((volume_ratio - 1.0) / 2.0 * 50, 50) if volume_ratio > 1.0 else 0
    return round(price_score + vol_score, 2)


def _build_results(raw: pd.DataFrame, symbols: list[str]) -> list[HotStockResult]:
    """Build HotStockResult list from yfinance download results."""
    results: list[HotStockResult] = []
    single = len(symbols) == 1

    for sym in symbols:
        try:
            if single:
                df = raw
            else:
                # yfinance MultiIndex: (ticker, price_type)
                if sym not in raw.columns.get_level_values(0):
                    continue
                df = raw[sym]

            if df is None or df.empty or len(df) < _MIN_ROWS:
                continue

            df = df.dropna(subset=["Close", "Volume"])
            if len(df) < _MIN_ROWS:
                continue

            close_today = float(df["Close"].iloc[-1])
            close_prev = float(df["Close"].iloc[-2])
            vol_today = int(df["Volume"].iloc[-1])

            # 20-day average volume (excluding today) — standard volume baseline
            vol_series = df["Volume"].iloc[:-1]  # exclude today
            avg_vol = int(vol_series.tail(_VOL_AVG_WINDOW).mean()) if len(vol_series) > 0 else int(df["Volume"].mean())

            if close_prev <= 0 or avg_vol <= 0:
                continue

            change_pct = (close_today - close_prev) / close_prev * 100
            vol_ratio = vol_today / avg_vol
            score = _score(change_pct, vol_ratio)
            direction = "rising" if change_pct > 0 else ("falling" if change_pct < 0 else "flat")

            results.append(
                HotStockResult(
                    symbol=sym,
                    price=close_today,
                    prev_close=close_prev,
                    change_pct=round(change_pct, 2),
                    volume=vol_today,
                    avg_volume=avg_vol,
                    volume_ratio=round(vol_ratio, 2),
                    hot_score=score,
                    direction=direction,
                )
            )
        except Exception as e:
            logger.debug("Failed to process symbol %s: %s", sym, e)

    return results


def _download(symbols: list[str]) -> pd.DataFrame | None:
    """yfinance bulk download. Fetches 1 month of data for 20-day average volume."""
    try:
        return yf.download(
            symbols,
            period="1mo",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            threads=True,
            progress=False,
        )
    except Exception as e:
        logger.error("yfinance bulk download failed: %s", e)
        return None


def select_hot_stock(universe: list[str] | None = None) -> HotStockResult | None:
    """Select the hottest stock from the scan universe.

    Args:
        universe: List of symbols to scan. Defaults to SCAN_UNIVERSE.

    Returns:
        HotStockResult or None if insufficient data.
    """
    top = select_top_n(n=1, universe=universe)
    return top[0] if top else None


def select_top_n(n: int = 5, universe: list[str] | None = None) -> list[HotStockResult]:
    """Return the top N stocks by hot score from the scan universe.

    Args:
        n: Number of stocks to return.
        universe: List of symbols to scan. Defaults to SCAN_UNIVERSE.

    Returns:
        List of HotStockResult (descending by score). Empty list if no results.
    """
    symbols = universe or SCAN_UNIVERSE
    logger.info("Hot stock scan started: %d symbols (selecting top %d)", len(symbols), n)

    raw = _download(symbols)
    if raw is None or raw.empty:
        logger.warning("Download failed or empty result")
        return []

    results = _build_results(raw, symbols)

    if not results:
        logger.warning("No scan results")
        return []

    results.sort(key=lambda r: r.hot_score, reverse=True)

    top = results[:n]
    for i, r in enumerate(top, 1):
        logger.info(
            "[%d] %s | change %+.2f%% | vol ratio %.1fx | score %.1f",
            i, r.symbol, r.change_pct, r.volume_ratio, r.hot_score,
        )

    return top
