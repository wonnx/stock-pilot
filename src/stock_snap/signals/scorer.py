"""Signal scoring: combine technical + sentiment into a trade signal."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum

from stock_snap.analysis.indicators import TechnicalIndicators
from stock_snap.news.sentiment import SentimentResult

logger = logging.getLogger(__name__)


class SignalDirection(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TradeSignal:
    """Aggregated trading signal for a symbol."""

    symbol: str
    direction: SignalDirection
    strength: float            # 0.0 – 1.0
    confidence: str            # "high", "medium", "low"
    score: float               # raw composite score (-10 to +10)
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    close: float = 0.0
    support: float = 0.0
    resistance: float = 0.0

    @property
    def is_actionable(self) -> bool:
        return self.direction != SignalDirection.HOLD and self.confidence in ("high", "medium")


class SignalScorer:
    """Score and rank trade signals using confluence of indicators."""

    # Weights for each scoring component
    WEIGHTS = {
        "ema_trend": 2.0,
        "macd": 1.5,
        "rsi": 1.5,
        "bb_position": 1.0,
        "volume_spike": 1.0,
        "sentiment": 2.0,
        "earnings_risk": -1.5,
    }

    def score(
        self,
        tech: TechnicalIndicators,
        sentiment: SentimentResult | None = None,
    ) -> TradeSignal:
        """Compute a composite trade signal."""
        score = 0.0
        reasons: list[str] = []
        warnings: list[str] = []

        # --- EMA trend ---
        if tech.ema_trend == "bullish":
            score += self.WEIGHTS["ema_trend"]
            reasons.append(f"EMA bullish (9={tech.ema9:.2f} > 21={tech.ema21:.2f} > 50={tech.ema50:.2f})")
        elif tech.ema_trend == "bearish":
            score -= self.WEIGHTS["ema_trend"]
            reasons.append(f"EMA bearish (9={tech.ema9:.2f} < 21={tech.ema21:.2f} < 50={tech.ema50:.2f})")

        # --- MACD ---
        if tech.macd_hist > 0 and tech.macd > tech.macd_signal:
            score += self.WEIGHTS["macd"]
            reasons.append(f"MACD bullish crossover (hist={tech.macd_hist:.3f})")
        elif tech.macd_hist < 0 and tech.macd < tech.macd_signal:
            score -= self.WEIGHTS["macd"]
            reasons.append(f"MACD bearish crossover (hist={tech.macd_hist:.3f})")

        # --- RSI ---
        if tech.rsi_zone == "oversold":
            score += self.WEIGHTS["rsi"] * 0.8
            reasons.append(f"RSI oversold ({tech.rsi14:.1f})")
        elif tech.rsi_zone == "overbought":
            score -= self.WEIGHTS["rsi"] * 0.8
            warnings.append(f"RSI overbought ({tech.rsi14:.1f})")
        elif 45 <= tech.rsi14 <= 60:
            score += self.WEIGHTS["rsi"] * 0.3

        # --- Bollinger Band position ---
        if tech.bb_position == "lower":
            score += self.WEIGHTS["bb_position"]
            reasons.append("Price at lower Bollinger Band (potential bounce)")
        elif tech.bb_position == "upper":
            score -= self.WEIGHTS["bb_position"] * 0.5
            warnings.append("Price at upper Bollinger Band (potential rejection)")

        # --- Volume spike ---
        if tech.volume_spike:
            vol_ratio = tech.volume / tech.volume_sma20 if tech.volume_sma20 > 0 else 1.0
            multiplier = self.WEIGHTS["volume_spike"] * min(vol_ratio / 2.0, 2.0)
            if score > 0:
                score += multiplier
                reasons.append(f"Volume spike ({vol_ratio:.1f}x average) confirms move")
            else:
                score -= multiplier
                warnings.append(f"Volume spike ({vol_ratio:.1f}x average) on down move")

        # --- Sentiment ---
        if sentiment:
            sent_contribution = sentiment.score * self.WEIGHTS["sentiment"]
            score += sent_contribution
            if abs(sentiment.score) >= 0.3:
                reasons.append(
                    f"News sentiment: {sentiment.sentiment} ({sentiment.score:+.2f}) — {sentiment.summary[:80]}"
                )
            if sentiment.has_earnings:
                score += self.WEIGHTS["earnings_risk"]
                warnings.append("Earnings event detected — elevated volatility risk")

        # --- Map to direction ---
        max_score = sum(abs(v) for v in self.WEIGHTS.values())
        strength = min(abs(score) / max_score, 1.0)

        if score >= 2.5:
            direction = SignalDirection.BUY
        elif score <= -2.5:
            direction = SignalDirection.SELL
        else:
            direction = SignalDirection.HOLD

        if strength >= 0.6:
            confidence = "high"
        elif strength >= 0.35:
            confidence = "medium"
        else:
            confidence = "low"

        return TradeSignal(
            symbol=tech.symbol,
            direction=direction,
            strength=strength,
            confidence=confidence,
            score=score,
            reasons=reasons,
            warnings=warnings,
            close=tech.close,
            support=tech.support,
            resistance=tech.resistance,
        )

    def rank(self, signals: list[TradeSignal]) -> list[TradeSignal]:
        """Sort signals by absolute score descending."""
        return sorted(signals, key=lambda s: abs(s.score), reverse=True)


scorer = SignalScorer()
