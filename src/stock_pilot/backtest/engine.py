"""Simple vectorized backtesting engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from stock_pilot.analysis.indicators import TechnicalAnalyzer
from stock_pilot.signals.scorer import SignalDirection, SignalScorer

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp | None
    exit_price: float | None
    direction: Literal["long", "short"]
    pnl_pct: float = 0.0
    closed: bool = False


@dataclass
class BacktestResult:
    symbol: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_return_pct: float
    max_drawdown_pct: float
    avg_trade_pct: float
    trades: list[Trade] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"{self.symbol}: {self.total_trades} trades | "
            f"WR={self.win_rate:.1%} | "
            f"Ret={self.total_return_pct:.1%} | "
            f"MaxDD={self.max_drawdown_pct:.1%}"
        )


class BacktestEngine:
    """Backtest the signal-based strategy on historical OHLCV data."""

    def __init__(
        self,
        hold_days: int = 5,
        stop_loss_pct: float = 0.03,
        take_profit_pct: float = 0.06,
    ) -> None:
        self._hold_days = hold_days
        self._stop_loss = stop_loss_pct
        self._take_profit = take_profit_pct
        self._ta = TechnicalAnalyzer()
        self._scorer = SignalScorer()

    def run(self, symbol: str, df: pd.DataFrame) -> BacktestResult:
        """
        Run backtest on full historical data using a rolling window.

        Strategy:
        - Compute indicators on rolling 60-day window
        - Enter long/short on BUY/SELL signals with high/medium confidence
        - Exit on stop-loss, take-profit, or hold_days
        """
        trades: list[Trade] = []
        window = 60
        n = len(df)

        i = window
        in_trade: Trade | None = None

        while i < n:
            row = df.iloc[i]
            date = df.index[i]

            # Check exit
            if in_trade and not in_trade.closed:
                price = float(row["Close"])
                entry = in_trade.entry_price
                days_held = (date - in_trade.entry_date).days

                pnl_pct = (price - entry) / entry
                if in_trade.direction == "short":
                    pnl_pct = -pnl_pct

                if (
                    pnl_pct <= -self._stop_loss
                    or pnl_pct >= self._take_profit
                    or days_held >= self._hold_days
                ):
                    in_trade.exit_date = date
                    in_trade.exit_price = price
                    in_trade.pnl_pct = pnl_pct
                    in_trade.closed = True
                    trades.append(in_trade)
                    in_trade = None

            # Generate signal on window
            if in_trade is None:
                window_df = df.iloc[i - window : i]
                tech = self._ta.compute(symbol, window_df)
                if tech:
                    signal = self._scorer.score(tech)
                    entry_price = float(row["Open"])  # Enter next open
                    if signal.direction == SignalDirection.BUY and signal.confidence in ("high", "medium"):
                        in_trade = Trade(
                            entry_date=date,
                            entry_price=entry_price,
                            exit_date=None,
                            exit_price=None,
                            direction="long",
                        )
                    elif signal.direction == SignalDirection.SELL and signal.confidence in ("high", "medium"):
                        in_trade = Trade(
                            entry_date=date,
                            entry_price=entry_price,
                            exit_date=None,
                            exit_price=None,
                            direction="short",
                        )
            i += 1

        # Close any open trade at last price
        if in_trade and not in_trade.closed:
            last_price = float(df["Close"].iloc[-1])
            pnl_pct = (last_price - in_trade.entry_price) / in_trade.entry_price
            if in_trade.direction == "short":
                pnl_pct = -pnl_pct
            in_trade.exit_date = df.index[-1]
            in_trade.exit_price = last_price
            in_trade.pnl_pct = pnl_pct
            in_trade.closed = True
            trades.append(in_trade)

        return self._compute_stats(symbol, trades)

    def _compute_stats(self, symbol: str, trades: list[Trade]) -> BacktestResult:
        if not trades:
            return BacktestResult(
                symbol=symbol,
                total_trades=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                total_return_pct=0.0,
                max_drawdown_pct=0.0,
                avg_trade_pct=0.0,
            )

        wins = [t for t in trades if t.pnl_pct > 0]
        losses = [t for t in trades if t.pnl_pct <= 0]
        pnls = [t.pnl_pct for t in trades]

        # Cumulative return (compound)
        total_return = 1.0
        for p in pnls:
            total_return *= 1 + p
        total_return -= 1.0

        # Max drawdown
        equity = [1.0]
        for p in pnls:
            equity.append(equity[-1] * (1 + p))
        peak = equity[0]
        max_dd = 0.0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak
            max_dd = max(max_dd, dd)

        return BacktestResult(
            symbol=symbol,
            total_trades=len(trades),
            wins=len(wins),
            losses=len(losses),
            win_rate=len(wins) / len(trades) if trades else 0.0,
            total_return_pct=total_return,
            max_drawdown_pct=max_dd,
            avg_trade_pct=sum(pnls) / len(pnls) if pnls else 0.0,
            trades=trades,
        )


engine = BacktestEngine()
