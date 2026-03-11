"""Telegram alert bot for trade signals."""

from __future__ import annotations

import asyncio
import logging

from telegram import Bot
from telegram.error import TelegramError

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


def format_signal_message(signal: TradeSignal) -> str:
    """Format a trade signal into a readable Telegram message."""
    dir_emoji = DIRECTION_EMOJI.get(signal.direction, "")
    conf_emoji = CONFIDENCE_EMOJI.get(signal.confidence, "")

    lines = [
        f"{dir_emoji} *{signal.symbol}* — {signal.direction.value}",
        f"Strength: {signal.strength:.0%} {conf_emoji} ({signal.confidence})",
        f"Price: ${signal.close:.2f}",
        f"Support: ${signal.support:.2f} | Resistance: ${signal.resistance:.2f}",
        "",
        "*Reasons:*",
    ]

    for reason in signal.reasons[:5]:
        lines.append(f"• {reason}")

    if signal.warnings:
        lines.append("")
        lines.append("*Warnings:*")
        for warning in signal.warnings[:3]:
            lines.append(f"• {warning}")

    lines.append(f"\nScore: {signal.score:+.2f}")
    return "\n".join(lines)


class TelegramAlerter:
    """Send trade signal alerts via Telegram bot."""

    def __init__(self) -> None:
        self._bot: Bot | None = None

    def _get_bot(self) -> Bot:
        if self._bot is None:
            if not config.TELEGRAM_BOT_TOKEN:
                raise ValueError("TELEGRAM_BOT_TOKEN not configured")
            self._bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        return self._bot

    async def send_signal(self, signal: TradeSignal) -> bool:
        """Send a signal alert. Returns True on success."""
        if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
            logger.warning("Telegram not configured, skipping alert for %s", signal.symbol)
            return False

        message = format_signal_message(signal)
        try:
            bot = self._get_bot()
            await bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID,
                text=message,
                parse_mode="Markdown",
            )
            logger.info("Sent Telegram alert for %s (%s)", signal.symbol, signal.direction.value)
            return True
        except TelegramError as e:
            logger.error("Telegram send failed for %s: %s", signal.symbol, e)
            return False

    async def send_batch(self, signals: list[TradeSignal]) -> int:
        """Send multiple signals. Returns count of successful sends."""
        actionable = [s for s in signals if s.is_actionable]
        if not actionable:
            logger.info("No actionable signals to send")
            return 0

        count = 0
        for signal in actionable:
            ok = await self.send_signal(signal)
            if ok:
                count += 1
        return count

    def send_signal_sync(self, signal: TradeSignal) -> bool:
        return asyncio.run(self.send_signal(signal))

    def send_batch_sync(self, signals: list[TradeSignal]) -> int:
        return asyncio.run(self.send_batch(signals))


alerter = TelegramAlerter()
