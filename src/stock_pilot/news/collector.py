"""News collection from RSS feeds and free financial news APIs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import feedparser  # type: ignore[import-untyped]
import httpx

from stock_pilot.utils.config import config

logger = logging.getLogger(__name__)

# Free financial RSS feeds
RSS_FEEDS: dict[str, str] = {
    "yahoo_finance": "https://finance.yahoo.com/rss/",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "reuters_business": "https://feeds.reuters.com/reuters/businessNews",
    "benzinga": "https://www.benzinga.com/feed",
}

FINNHUB_NEWS_URL = "https://finnhub.io/api/v1/company-news"
ALPHA_VANTAGE_NEWS_URL = "https://www.alphavantage.co/query"
SEC_EDGAR_RSS = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=20&search_text=&output=atom"


@dataclass
class NewsItem:
    """A single news article."""

    title: str
    summary: str
    url: str
    published: datetime
    source: str
    symbols: list[str]


class NewsCollector:
    """Collect relevant news for tracked symbols."""

    def __init__(self, lookback_hours: int = 24) -> None:
        self._lookback = timedelta(hours=lookback_hours)

    def fetch_for_symbol(self, symbol: str, max_items: int = 10) -> list[NewsItem]:
        """Fetch recent news articles mentioning a symbol."""
        items: list[NewsItem] = []
        cutoff = datetime.now(tz=UTC) - self._lookback

        # 1) Finnhub company news (primary, most reliable)
        items.extend(self._fetch_finnhub(symbol, cutoff, max_items))

        # 2) Alpha Vantage news sentiment
        if len(items) < max_items:
            items.extend(self._fetch_alpha_vantage(symbol, cutoff, max_items - len(items)))

        # 3) RSS feeds (fallback)
        if len(items) < max_items:
            items.extend(self._fetch_rss_for_symbol(symbol, cutoff, max_items - len(items)))

        return items[:max_items]

    def fetch_market_news(self, max_items: int = 20) -> list[NewsItem]:
        """Fetch general market news and SEC filings."""
        items: list[NewsItem] = []
        cutoff = datetime.now(tz=UTC) - self._lookback

        # SEC EDGAR 8-K filings (material events)
        items.extend(self._fetch_sec_edgar(cutoff, max_items // 2))

        # RSS feeds
        for source, url in RSS_FEEDS.items():
            if len(items) >= max_items:
                break
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    published = self._parse_date(entry)
                    if published and published < cutoff:
                        continue
                    items.append(
                        NewsItem(
                            title=entry.get("title", ""),
                            summary=entry.get("summary", "")[:500],
                            url=entry.get("link", ""),
                            published=published or datetime.now(tz=UTC),
                            source=source,
                            symbols=[],
                        )
                    )
                    if len(items) >= max_items:
                        return items
            except Exception:
                logger.debug("Failed to fetch RSS feed: %s", source)

        return items

    def _fetch_finnhub(self, symbol: str, cutoff: datetime, max_items: int) -> list[NewsItem]:
        """Fetch news from Finnhub API."""
        if not config.FINNHUB_API_KEY:
            return []
        try:
            from_date = cutoff.strftime("%Y-%m-%d")
            to_date = datetime.now(tz=UTC).strftime("%Y-%m-%d")
            resp = httpx.get(
                FINNHUB_NEWS_URL,
                params={"symbol": symbol, "from": from_date, "to": to_date, "token": config.FINNHUB_API_KEY},
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            items = []
            for article in resp.json()[:max_items]:
                published = datetime.fromtimestamp(article.get("datetime", 0), tz=UTC)
                if published < cutoff:
                    continue
                items.append(
                    NewsItem(
                        title=article.get("headline", ""),
                        summary=article.get("summary", "")[:500],
                        url=article.get("url", ""),
                        published=published,
                        source="finnhub",
                        symbols=[symbol],
                    )
                )
            return items
        except Exception as e:
            logger.debug("Finnhub fetch failed for %s: %s", symbol, e)
            return []

    def _fetch_alpha_vantage(self, symbol: str, cutoff: datetime, max_items: int) -> list[NewsItem]:
        """Fetch news from Alpha Vantage News & Sentiments API."""
        if not config.ALPHA_VANTAGE_API_KEY:
            return []
        try:
            resp = httpx.get(
                ALPHA_VANTAGE_NEWS_URL,
                params={
                    "function": "NEWS_SENTIMENT",
                    "tickers": symbol,
                    "apikey": config.ALPHA_VANTAGE_API_KEY,
                    "limit": max_items,
                },
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            feed = data.get("feed", [])
            items = []
            for article in feed[:max_items]:
                time_str = article.get("time_published", "")
                try:
                    published = datetime.strptime(time_str, "%Y%m%dT%H%M%S").replace(tzinfo=UTC)
                except ValueError:
                    published = datetime.now(tz=UTC)
                if published < cutoff:
                    continue
                items.append(
                    NewsItem(
                        title=article.get("title", ""),
                        summary=article.get("summary", "")[:500],
                        url=article.get("url", ""),
                        published=published,
                        source="alpha_vantage",
                        symbols=[symbol],
                    )
                )
            return items
        except Exception as e:
            logger.debug("Alpha Vantage fetch failed for %s: %s", symbol, e)
            return []

    def _fetch_sec_edgar(self, cutoff: datetime, max_items: int) -> list[NewsItem]:
        """Fetch recent SEC 8-K filings from EDGAR."""
        try:
            feed = feedparser.parse(SEC_EDGAR_RSS)
            items = []
            for entry in feed.entries[:max_items]:
                published = self._parse_date(entry)
                if published and published < cutoff:
                    continue
                title = entry.get("title", "")
                items.append(
                    NewsItem(
                        title=title,
                        summary=entry.get("summary", "")[:500],
                        url=entry.get("link", ""),
                        published=published or datetime.now(tz=UTC),
                        source="sec_edgar",
                        symbols=[],
                    )
                )
            return items
        except Exception as e:
            logger.debug("SEC EDGAR fetch failed: %s", e)
            return []

    def _fetch_rss_for_symbol(self, symbol: str, cutoff: datetime, max_items: int) -> list[NewsItem]:
        """Fetch news from RSS feeds filtered by symbol mention."""
        items: list[NewsItem] = []
        for source, url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    title = entry.get("title", "")
                    summary = entry.get("summary", entry.get("description", ""))
                    link = entry.get("link", "")

                    text = (title + " " + summary).upper()
                    if symbol.upper() not in text:
                        continue

                    published = self._parse_date(entry)
                    if published and published < cutoff:
                        continue

                    items.append(
                        NewsItem(
                            title=title,
                            summary=summary[:500],
                            url=link,
                            published=published or datetime.now(tz=UTC),
                            source=source,
                            symbols=[symbol],
                        )
                    )
                    if len(items) >= max_items:
                        return items
            except Exception:
                logger.debug("Failed to fetch RSS feed: %s", source)

        return items

    @staticmethod
    def _parse_date(entry: dict) -> datetime | None:  # type: ignore[type-arg]
        import time
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if parsed:
            try:
                ts = time.mktime(parsed)
                return datetime.fromtimestamp(ts, tz=UTC)
            except Exception:
                pass
        return None


collector = NewsCollector()
