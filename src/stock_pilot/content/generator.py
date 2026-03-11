from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
import json, logging
import anthropic
from stock_pilot.news.collector import NewsItem
from stock_pilot.utils.config import config

if TYPE_CHECKING:
    from stock_pilot.analysis.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


@dataclass
class ContentPackage:
    symbol: str
    price: float
    change_pct: float
    direction: str
    script: str
    card_title: str
    card_subtitle: str
    card_body: str
    caption: str
    # Quant analysis data (for Remotion template)
    rsi: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    volume_ratio: float = 1.0
    bb_position: str = "middle"  # "upper" | "middle" | "lower"
    ema_trend: str = "mixed"     # "bullish" | "bearish" | "mixed"
    quant_summary: str = ""      # Quant analysis summary text
    # Forecast text (Quant Analyst output)
    forecast: str = ""           # Short forecast for video ending (1-2 lines)
    forecast_detail: str = ""    # Detailed forecast for caption (3-5 lines)
    # Chart data points (last 20 days close prices, for Remotion animation)
    chart_data: list[float] = field(default_factory=list)


class ContentGenerator:
    def __init__(self):
        self._client: Optional[anthropic.Anthropic] = None

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        return self._client

    def generate(
        self,
        symbol: str,
        price: float,
        prev_close: float,
        news_items: list[NewsItem],
        sentiment_summary: str = "",
        tech: "TechnicalIndicators | None" = None,
        chart_data: list[float] | None = None,
    ) -> Optional[ContentPackage]:
        # Calculate change
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
        direction = "rising" if change_pct > 0 else ("falling" if change_pct < 0 else "flat")

        # Format news
        news_text = "\n".join(
            f"- {item.title}" for item in news_items[:5]
        ) if news_items else "(No recent major news)"

        # Quant analysis text (including extended indicators)
        quant_text = ""
        if tech:
            rsi_zone = tech.rsi_zone
            ema_trend = tech.ema_trend
            sma_trend = tech.sma_trend
            bb_pos = tech.bb_position
            vol_spike = "Volume spike detected" if tech.volume_spike else "Normal volume"
            trend_dir = tech.trendline.direction if tech.trendline else "flat"
            trend_r2 = tech.trendline.r_squared if tech.trendline else 0.0
            quant_text = f"""
Quant Analysis:
- RSI(14): {tech.rsi14:.1f} ({rsi_zone})
- MACD: {tech.macd:.3f} / Signal: {tech.macd_signal:.3f} (Histogram: {tech.macd_hist:.3f})
- Bollinger Bands: {bb_pos} ({tech.bb_lower:.2f} ~ {tech.bb_upper:.2f}){" [Squeeze]" if tech.bb_squeeze else ""}
- Moving Averages: SMA5={tech.sma5:.2f} / SMA20={tech.sma20:.2f} / SMA60={tech.sma60:.2f} -> {sma_trend} ({"Golden Cross" if tech.golden_cross else "Death Cross"})
- EMA Trend: {ema_trend} (EMA9={tech.ema9:.2f} / EMA21={tech.ema21:.2f} / EMA50={tech.ema50:.2f})
- {vol_spike}
- 20-day Trendline: {trend_dir} (R2={trend_r2:.2f})
- Pivot Points: P={tech.pivot:.2f} / R1={tech.pivot_r1:.2f} / S1={tech.pivot_s1:.2f}
- Support: {tech.support:.2f} / Resistance: {tech.resistance:.2f}"""

        prompt = f"""You are a quant analyst and content creator for a professional finance short-form channel.

Stock Info:
- Symbol: {symbol}
- Current Price: ${price:.2f}
- Change: {change_pct:+.2f}%
- Direction: {direction}
- Today's Key News:
{news_text}
{f"- Market Analysis: {sentiment_summary}" if sentiment_summary else ""}
{quant_text}

Generate content in the following JSON format (pure JSON, no markdown):
{{
  "script": "30-second short-form video narration (under 200 chars). Natural, impactful English. Mention quant indicators naturally. Include 1-2 line forecast at the end. Minimize AI-like tone. End with 'This content is not investment advice.'",
  "card_title": "Card news headline (under 15 words, impactful)",
  "card_subtitle": "Subtitle (under 30 words, core reason)",
  "card_body": "Card news body, 3 lines. Focus on numbers and facts. Include quant indicators.",
  "caption": "Social media post (Instagram/YouTube). Use emojis appropriately. Combine news analysis + quant outlook in detail (6-8 lines). Include 5 relevant hashtags. End with 'This content is not investment advice.'",
  "quant_summary": "2-3 line quant perspective summary. RSI overbought/oversold, MACD trend, Bollinger Band position, MA alignment — professional analysis.",
  "forecast": "Short-term outlook (1-2 lines, for video ending). Technical indicator-based direction. Use cautious language like 'likely to...', 'watch for...'. No investment advice.",
  "forecast_detail": "Detailed outlook (3-5 lines, for caption). Technical basis (SMA/EMA/RSI/pivot) + news flow + short-term scenarios (bull/bear). Professional, cautious tone. No investment advice."
}}

Write in a professional, impactful finance channel style."""

        try:
            client = self._get_client()
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            # Extract JSON block (may be wrapped in ```json ... ```)
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())

            return ContentPackage(
                symbol=symbol,
                price=price,
                change_pct=change_pct,
                direction=direction,
                script=data.get("script", ""),
                card_title=data.get("card_title", f"{symbol} {direction}"),
                card_subtitle=data.get("card_subtitle", f"{change_pct:+.2f}%"),
                card_body=data.get("card_body", ""),
                caption=data.get("caption", ""),
                quant_summary=data.get("quant_summary", ""),
                forecast=data.get("forecast", ""),
                forecast_detail=data.get("forecast_detail", ""),
                rsi=tech.rsi14 if tech else 0.0,
                macd=tech.macd if tech else 0.0,
                macd_signal=tech.macd_signal if tech else 0.0,
                volume_ratio=(tech.volume / tech.volume_sma20) if (tech and tech.volume_sma20 > 0) else 1.0,
                bb_position=tech.bb_position if tech else "middle",
                ema_trend=tech.ema_trend if tech else "mixed",
                chart_data=chart_data or [],
            )
        except Exception:
            logger.exception("Content generation failed for %s", symbol)
            return None


generator = ContentGenerator()
