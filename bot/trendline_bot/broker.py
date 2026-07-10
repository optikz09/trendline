"""Broker adapters.

The strategy emits Signals; a Broker turns a Signal into an order. Swap the adapter to go
from paper trading to live HugosWay / PRO4-MT4 without touching the strategy.

- PaperBroker      : logs orders, tracks nothing live. For dry runs.
- FileBridgeBroker : writes a JSON command file that the MQL4 EA (mt4/TrendLineTradingBridge.mq4)
                     polls inside the PRO4/MT4 terminal to place real orders on HugosWay.
"""

from __future__ import annotations

import json
import math
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from .config import Config
from .strategy import Signal


def position_size(cfg: Config, signal: Signal, balance: Optional[float] = None) -> float:
    """Lots so that hitting the stop loses risk_per_trade of the account (rulebook §7)."""
    bal = balance if balance is not None else cfg.account_balance
    risk_cash = bal * cfg.risk_per_trade
    risk_per_lot = signal.risk * cfg.contract_size
    if risk_per_lot <= 0:
        return 0.0
    raw = risk_cash / risk_per_lot
    steps = math.floor(raw / cfg.lot_step) * cfg.lot_step
    return max(cfg.min_lot, min(cfg.max_lot, round(steps, 2)))


class Broker(ABC):
    @abstractmethod
    def place(self, signal: Signal, lots: float) -> str:
        """Submit an order; return a broker/command id."""


class PaperBroker(Broker):
    def __init__(self) -> None:
        self.orders = []

    def place(self, signal: Signal, lots: float) -> str:
        oid = f"paper-{len(self.orders) + 1}"
        self.orders.append((oid, signal, lots))
        print(
            f"[PAPER] {oid} {signal.side.upper()} {lots} {signal.symbol} "
            f"@ {signal.entry:.2f} SL {signal.stop:.2f} TP {signal.target:.2f} "
            f"({signal.setup}, {signal.rr:.2f}R)"
        )
        return oid


class FileBridgeBroker(Broker):
    """Append orders to a JSON-lines command file the MT4 EA consumes.

    Protocol (one JSON object per line):
        {"id","action":"OPEN","symbol","side","lots","entry","sl","tp","setup","ts"}
    The EA marks each processed id in <bridge_dir>/acks.jsonl. We never delete the command
    file, so restarts stay idempotent (the EA skips ids it already acked).
    """

    def __init__(self, bridge_dir: str) -> None:
        self.bridge_dir = bridge_dir
        os.makedirs(bridge_dir, exist_ok=True)
        self.cmd_path = os.path.join(bridge_dir, "commands.jsonl")
        self._seq = self._resume_seq()

    def _resume_seq(self) -> int:
        if not os.path.exists(self.cmd_path):
            return 0
        n = 0
        with open(self.cmd_path, "r", encoding="utf-8") as fh:
            for _ in fh:
                n += 1
        return n

    def place(self, signal: Signal, lots: float) -> str:
        self._seq += 1
        oid = f"cmd-{self._seq}"
        cmd = {
            "id": oid,
            "action": "OPEN",
            "symbol": signal.symbol,
            "side": signal.side,
            "lots": lots,
            "entry": round(signal.entry, 5),
            "sl": round(signal.stop, 5),
            "tp": round(signal.target, 5),
            "setup": signal.setup,
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(self.cmd_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(cmd) + "\n")
        print(f"[MT4] queued {oid}: {signal.side.upper()} {lots} {signal.symbol} -> {self.cmd_path}")
        return oid


def make_broker(name: str, cfg: Config, bridge_dir: str) -> Broker:
    name = (name or "paper").lower()
    if name == "paper":
        return PaperBroker()
    if name in ("mt4", "file", "bridge"):
        return FileBridgeBroker(bridge_dir)
    raise ValueError(f"Unknown broker {name!r} (use 'paper' or 'mt4')")
