"""Main scanner: orchestrates data → analysis → signals → alerts."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from stock_pilot.alerts.kakao import KakaoAlerter
from stock_pilot.analysis.indicators import TechnicalAnalyzer
from stock_pilot.data.fetcher import MarketDataFetcher
from stock_pilot.data.watchlist import Watchlist
from stock_pilot.news.collector import NewsCollector
from stock_pilot.news.sentiment import SentimentAnalyzer
from stock_pilot.signals.scorer import SignalScorer, TradeSignal

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    signals: list[TradeSignal]
    errors: list[str]
    alerts_sent: int


class Scanner:
    """Full scan pipeline for all watchlist symbols."""

    def __init__(
        self,
        watchlist: Watchlist | None = None,
        fetcher: MarketDataFetcher | None = None,
        analyzer: TechnicalAnalyzer | None = None,
        news_collector: NewsCollector | None = None,
        sentiment_analyzer: SentimentAnalyzer | None = None,
        scorer: SignalScorer | None = None,
        alerter: KakaoAlerter | None = None,
        skip_news: bool = False,
    ) -> None:
        from stock_pilot.alerts.kakao import alerter as default_alerter
        from stock_pilot.data.fetcher import fetcher as default_fetcher
        from stock_pilot.data.watchlist import watchlist as default_watchlist

        self._watchlist = watchlist or default_watchlist
        self._fetcher = fetcher or default_fetcher
        self._analyzer = analyzer or TechnicalAnalyzer()
        self._news = news_collector or NewsCollector()
        self._sentiment = sentiment_analyzer or SentimentAnalyzer()
        self._scorer = scorer or SignalScorer()
        self._alerter = alerter or default_alerter
        self._skip_news = skip_news

    def run_sync(self, send_alerts: bool = True) -> ScanResult:
        return asyncio.run(self.run(send_alerts=send_alerts))

    async def run(self, send_alerts: bool = True) -> ScanResult:
        """Run a full scan of all watchlist symbols."""
        symbols = self._watchlist.symbols
        logger.info("Starting scan for %d symbols", len(symbols))

        signals: list[TradeSignal] = []
        errors: list[str] = []

        for symbol in symbols:
            try:
                signal = await self._scan_symbol(symbol)
                if signal:
                    signals.append(signal)
                    logger.info(
                        "%s: %s (score=%.2f, confidence=%s)",
                        symbol,
                        signal.direction.value,
                        signal.score,
                        signal.confidence,
                    )
            except Exception as e:
                logger.exception("Error scanning %s", symbol)
                errors.append(f"{symbol}: {e}")

        ranked = self._scorer.rank(signals)

        alerts_sent = 0
        if send_alerts and ranked:
            alerts_sent = self._alerter.send_batch(ranked)

        return ScanResult(signals=ranked, errors=errors, alerts_sent=alerts_sent)

    async def _scan_symbol(self, symbol: str) -> TradeSignal | None:
        df = self._fetcher.get_ohlcv(symbol, period="1y", interval="1d")
        if df.empty or len(df) < 50:
            logger.warning("%s: insufficient data", symbol)
            return None

        tech = self._analyzer.compute(symbol, df)
        if not tech:
            return None

        sentiment = None
        if not self._skip_news:
            news_items = self._news.fetch_for_symbol(symbol)
            sentiment = self._sentiment.analyze(symbol, news_items)

        return self._scorer.score(tech, sentiment)


scanner = Scanner()
