"""News collection from RSS feeds and free financial news sources."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import feedparser  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# Free financial RSS feeds (no API key needed)
RSS_FEEDS: dict[str, str] = {
    "seekingalpha": "https://seekingalpha.com/feed.xml",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "reuters_business": "https://feeds.reuters.com/reuters/businessNews",
    "yahoo_finance": "https://finance.yahoo.com/rss/",
    "benzinga": "https://www.benzinga.com/feed",
}


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
        cutoff = datetime.now(tz=timezone.utc) - self._lookback

        for source, url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    title = entry.get("title", "")
                    summary = entry.get("summary", entry.get("description", ""))
                    link = entry.get("link", "")

                    # Filter by symbol mention
                    text = (title + " " + summary).upper()
                    if symbol.upper() not in text:
                        continue

                    # Parse date
                    published = self._parse_date(entry)
                    if published and published < cutoff:
                        continue

                    items.append(
                        NewsItem(
                            title=title,
                            summary=summary[:500],
                            url=link,
                            published=published or datetime.now(tz=timezone.utc),
                            source=source,
                            symbols=[symbol],
                        )
                    )

                    if len(items) >= max_items:
                        return items

            except Exception:
                logger.debug("Failed to fetch feed: %s", source)

        return items

    def fetch_market_news(self, max_items: int = 20) -> list[NewsItem]:
        """Fetch general market news (not symbol-specific)."""
        items: list[NewsItem] = []
        cutoff = datetime.now(tz=timezone.utc) - self._lookback

        for source, url in RSS_FEEDS.items():
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
                            published=published or datetime.now(tz=timezone.utc),
                            source=source,
                            symbols=[],
                        )
                    )
                    if len(items) >= max_items:
                        return items
            except Exception:
                logger.debug("Failed to fetch feed: %s", source)

        return items

    @staticmethod
    def _parse_date(entry: dict) -> datetime | None:  # type: ignore[type-arg]
        import time
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if parsed:
            try:
                ts = time.mktime(parsed)
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass
        return None


collector = NewsCollector()
