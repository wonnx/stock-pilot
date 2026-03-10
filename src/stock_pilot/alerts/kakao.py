"""KakaoTalk '나에게 보내기' alert for trade signals."""

from __future__ import annotations

import logging

import httpx

from stock_pilot.signals.scorer import SignalDirection, TradeSignal
from stock_pilot.utils.config import config

logger = logging.getLogger(__name__)

DIRECTION_EMOJI = {
    SignalDirection.BUY: "🟢",
    SignalDirection.SELL: "🔴",
    SignalDirection.HOLD: "🟡",
}

CONFIDENCE_EMOJI = {
    "high": "🔥",
    "medium": "⚡",
    "low": "💤",
}

KAKAO_SEND_ME_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


def format_signal_message(signal: TradeSignal) -> str:
    """Format a trade signal into a readable KakaoTalk message."""
    dir_emoji = DIRECTION_EMOJI.get(signal.direction, "")
    conf_emoji = CONFIDENCE_EMOJI.get(signal.confidence, "")

    lines = [
        f"{dir_emoji} {signal.symbol} — {signal.direction.value}",
        f"강도: {signal.strength:.0%} {conf_emoji} ({signal.confidence})",
        f"현재가: ${signal.close:.2f}",
        f"지지선: ${signal.support:.2f} | 저항선: ${signal.resistance:.2f}",
        "",
        "📋 근거:",
    ]

    for reason in signal.reasons[:5]:
        lines.append(f"• {reason}")

    if signal.warnings:
        lines.append("")
        lines.append("⚠️ 주의:")
        for warning in signal.warnings[:3]:
            lines.append(f"• {warning}")

    lines.append(f"\n스코어: {signal.score:+.2f}")
    return "\n".join(lines)


class KakaoAlerter:
    """Send trade signal alerts via KakaoTalk '나에게 보내기' API."""

    def send_signal(self, signal: TradeSignal) -> bool:
        """Send a signal alert. Returns True on success."""
        if not config.KAKAO_ACCESS_TOKEN:
            logger.warning("KAKAO_ACCESS_TOKEN not configured, skipping alert for %s", signal.symbol)
            return False

        message = format_signal_message(signal)
        payload = {
            "template_object": '{"object_type":"text","text":' + repr(message) + ',"link":{"web_url":"https://finance.yahoo.com/quote/' + signal.symbol + '"}}'
        }

        # Use JSON body via form-encoded as Kakao API requires
        template = {
            "object_type": "text",
            "text": message,
            "link": {"web_url": f"https://finance.yahoo.com/quote/{signal.symbol}"},
        }

        import json
        try:
            resp = httpx.post(
                KAKAO_SEND_ME_URL,
                headers={
                    "Authorization": f"Bearer {config.KAKAO_ACCESS_TOKEN}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"template_object": json.dumps(template, ensure_ascii=False)},
                timeout=10,
            )
            if resp.status_code == 200:
                logger.info("Sent KakaoTalk alert for %s (%s)", signal.symbol, signal.direction.value)
                return True
            else:
                logger.error("KakaoTalk send failed for %s: %s %s", signal.symbol, resp.status_code, resp.text)
                return False
        except httpx.HTTPError as e:
            logger.error("KakaoTalk HTTP error for %s: %s", signal.symbol, e)
            return False

    def send_batch(self, signals: list[TradeSignal]) -> int:
        """Send multiple signals. Returns count of successful sends."""
        actionable = [s for s in signals if s.is_actionable]
        if not actionable:
            logger.info("No actionable signals to send")
            return 0

        count = 0
        for signal in actionable:
            if self.send_signal(signal):
                count += 1
        return count


alerter = KakaoAlerter()
