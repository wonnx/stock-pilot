"""Market data fetcher using yfinance."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class MarketDataFetcher:
    """Fetches OHLCV data for US stocks via yfinance."""

    def __init__(self, cache_ttl_minutes: int = 5) -> None:
        self._cache: dict[str, tuple[datetime, pd.DataFrame]] = {}
        self._cache_ttl = timedelta(minutes=cache_ttl_minutes)

    def get_ohlcv(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol.

        Args:
            symbol: Stock ticker (e.g., 'AAPL')
            period: yfinance period string ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y')
            interval: yfinance interval ('1m', '5m', '15m', '30m', '60m', '1d', '1wk')
            force_refresh: Bypass cache

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
        """
        cache_key = f"{symbol}:{period}:{interval}"
        now = datetime.now(tz=UTC)

        if not force_refresh and cache_key in self._cache:
            cached_at, df = self._cache[cache_key]
            if now - cached_at < self._cache_ttl:
                logger.debug("Cache hit for %s", cache_key)
                return df

        logger.info("Fetching %s (period=%s, interval=%s)", symbol, period, interval)
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)

        if df.empty:
            logger.warning("No data returned for %s", symbol)
            return df

        df.index = pd.to_datetime(df.index, utc=True)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(inplace=True)

        self._cache[cache_key] = (now, df)
        return df

    def get_bulk_ohlcv(
        self,
        symbols: list[str],
        period: str = "1y",
        interval: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """Fetch OHLCV data for multiple symbols."""
        result: dict[str, pd.DataFrame] = {}
        for sym in symbols:
            try:
                df = self.get_ohlcv(sym, period=period, interval=interval)
                if not df.empty:
                    result[sym] = df
            except Exception:
                logger.exception("Failed to fetch %s", sym)
        return result

    def get_realtime_quote(self, symbol: str) -> dict[str, float | str]:
        """Get latest price and basic quote info."""
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        return {
            "symbol": symbol,
            "price": float(getattr(info, "last_price", 0) or 0),
            "prev_close": float(getattr(info, "previous_close", 0) or 0),
            "volume": float(getattr(info, "three_month_average_volume", 0) or 0),
        }

    def get_earnings_dates(self, symbol: str) -> pd.DataFrame | None:
        """Fetch upcoming earnings dates."""
        try:
            ticker = yf.Ticker(symbol)
            cal = ticker.calendar
            if cal is not None and not cal.empty:
                return cal
        except Exception:
            logger.debug("No earnings data for %s", symbol)
        return None


# Module-level singleton
fetcher = MarketDataFetcher()
