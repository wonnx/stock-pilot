"""News sentiment analysis using Claude API."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import anthropic

from stock_snap.news.collector import NewsItem
from stock_snap.utils.config import config

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """Claude's sentiment analysis of a set of news items."""

    symbol: str
    sentiment: str  # "positive", "negative", "neutral", "mixed"
    score: float    # -1.0 (very negative) to +1.0 (very positive)
    impact: str     # "high", "medium", "low"
    summary: str
    key_factors: list[str]
    has_earnings: bool = False
    has_fda_event: bool = False


class SentimentAnalyzer:
    """Use Claude to assess news sentiment impact on a stock."""

    def __init__(self) -> None:
        self._client: anthropic.Anthropic | None = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        return self._client

    def analyze(self, symbol: str, news_items: list[NewsItem]) -> SentimentResult | None:
        """Analyze sentiment of news items for a symbol using Claude."""
        if not news_items:
            return SentimentResult(
                symbol=symbol,
                sentiment="neutral",
                score=0.0,
                impact="low",
                summary="No recent news found.",
                key_factors=[],
            )

        if not config.ANTHROPIC_API_KEY:
            logger.warning("No ANTHROPIC_API_KEY — skipping sentiment analysis")
            return None

        news_text = "\n\n".join(
            f"[{item.source}] {item.title}\n{item.summary}"
            for item in news_items[:8]
        )

        prompt = f"""You are a professional stock market analyst specializing in short-term trading signals.

Analyze the following news items for {symbol} and provide a structured assessment.

News:
{news_text}

Respond in this exact JSON format (no markdown, just raw JSON):
{{
  "sentiment": "positive|negative|neutral|mixed",
  "score": <float from -1.0 to 1.0>,
  "impact": "high|medium|low",
  "summary": "<1-2 sentence summary of market impact>",
  "key_factors": ["<factor1>", "<factor2>", "<factor3>"],
  "has_earnings": <true|false>,
  "has_fda_event": <true|false>
}}

Focus on short-term (1-5 day) price impact for a swing/day trader."""

        try:
            client = self._get_client()
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            import json
            data = json.loads(raw)
            return SentimentResult(
                symbol=symbol,
                sentiment=data.get("sentiment", "neutral"),
                score=float(data.get("score", 0.0)),
                impact=data.get("impact", "low"),
                summary=data.get("summary", ""),
                key_factors=data.get("key_factors", []),
                has_earnings=bool(data.get("has_earnings", False)),
                has_fda_event=bool(data.get("has_fda_event", False)),
            )
        except Exception:
            logger.exception("Sentiment analysis failed for %s", symbol)
            return None


sentiment_analyzer = SentimentAnalyzer()
