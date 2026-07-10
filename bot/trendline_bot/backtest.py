"""A simple, honest event-driven backtest.

Walk the series bar by bar. When flat, ask the strategy for a signal on the just-closed bar
and enter at its close. While in a trade, exit on the first bar whose range hits the stop or
the target (stop checked first — the conservative assumption). One position at a time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .config import Config
from .data import Candle
from .strategy import Signal, generate_signal


@dataclass
class Trade:
    signal: Signal
    exit_time: str
    exit_price: float
    outcome: str      # "target" | "stop" | "open"
    r: float          # realised R multiple


@dataclass
class BacktestResult:
    trades: List[Trade]

    @property
    def n(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> int:
        return sum(1 for t in self.trades if t.r > 0)

    @property
    def win_rate(self) -> float:
        return (self.wins / self.n * 100.0) if self.n else 0.0

    @property
    def total_r(self) -> float:
        return sum(t.r for t in self.trades)

    @property
    def expectancy(self) -> float:
        return (self.total_r / self.n) if self.n else 0.0

    def summary(self) -> str:
        lines = [
            "── Backtest summary ─────────────────────────",
            f" trades       : {self.n}",
            f" win rate     : {self.win_rate:.1f}%  ({self.wins}W / {self.n - self.wins}L)",
            f" total R      : {self.total_r:+.2f}",
            f" expectancy   : {self.expectancy:+.2f} R / trade",
        ]
        return "\n".join(lines)


def run_backtest(candles: List[Candle], cfg: Config) -> BacktestResult:
    trades: List[Trade] = []
    open_sig: Optional[Signal] = None

    for i in range(len(candles)):
        if open_sig is None:
            sig = generate_signal(candles, i, cfg)
            if sig is not None:
                open_sig = sig
            continue

        # Manage the open trade on this bar (entry bar already passed).
        bar = candles[i]
        long = open_sig.side == "long"
        hit_stop = bar.low <= open_sig.stop if long else bar.high >= open_sig.stop
        hit_tgt = bar.high >= open_sig.target if long else bar.low <= open_sig.target

        if hit_stop:
            trades.append(Trade(open_sig, bar.time.strftime("%Y-%m-%d %H:%M"), open_sig.stop, "stop", -1.0))
            open_sig = None
        elif hit_tgt:
            trades.append(Trade(open_sig, bar.time.strftime("%Y-%m-%d %H:%M"), open_sig.target, "target",
                                round(open_sig.rr, 3)))
            open_sig = None

    if open_sig is not None:
        last = candles[-1]
        r = ((last.close - open_sig.entry) if open_sig.side == "long" else (open_sig.entry - last.close))
        trades.append(Trade(open_sig, last.time.strftime("%Y-%m-%d %H:%M"), last.close, "open",
                            round(r / open_sig.risk, 3) if open_sig.risk else 0.0))

    return BacktestResult(trades)
