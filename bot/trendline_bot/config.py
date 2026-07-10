"""Strategy + risk configuration.

Every tunable lives here so the same code backtests and trades live. Load from a JSON
file with Config.from_file(); anything omitted falls back to these defaults.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, fields


@dataclass
class Config:
    # --- market / bridge ---
    symbol: str = "XPTUSD"            # Platinum. Match the exact broker symbol on HugosWay.
    timeframe_minutes: int = 240      # H4 by default. Must be >= 60 (hourly and up only).

    # --- trendline validity (see rulebook §2) ---
    pivot_left: int = 3               # bars to the left a swing must dominate
    pivot_right: int = 3              # bars to the right (also the confirmation lag)
    min_taps: int = 3                 # >= 3 touches
    min_tap_gap: int = 6              # >= 6 candles between taps
    min_span_days: float = 21.0       # >= 3 weeks from first to last tap
    max_norm_slope: float = 1.0       # |slope| per candle, in ATRs (~ the "<45 degrees" filter)
    tap_tol_atr: float = 0.25         # how close a pivot must be to count as a tap (in ATRs)

    # --- entries / exits (see rulebook §3-6) ---
    atr_period: int = 14
    break_tol_atr: float = 0.10       # close must clear the line by this (ATRs) to count as a break
    stop_buffer_atr: float = 0.50     # extra room beyond the line/structure for the stop
    safety_lookback: int = 10         # bars used to locate the opposing "safety" swing on a break
    min_rr: float = 2.0               # minimum reward:risk to take a trade

    # --- trading costs (backtest realism; defaults of 0 = ideal fills) ---
    spread: float = 0.0               # bid/ask spread in price units, paid once per round turn
    slippage: float = 0.0             # adverse slippage in price units, per side (entry and exit)
    commission_per_lot: float = 0.0   # round-turn commission per 1.0 lot, in account currency

    # --- risk / sizing (see rulebook §7) ---
    account_balance: float = 1000.0   # used for position sizing when the broker can't report it
    risk_per_trade: float = 0.01      # 1% of account risked per trade
    contract_size: float = 1.0        # units per 1.0 lot (set to broker's contract size for platinum)
    min_lot: float = 0.01
    lot_step: float = 0.01
    max_lot: float = 100.0

    # --- live loop ---
    poll_seconds: int = 30            # how often the live loop checks for a fresh bar

    @classmethod
    def from_file(cls, path: str) -> "Config":
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)
