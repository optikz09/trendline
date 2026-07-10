"""Signal generation: Bounce + Break setups with entry / stop / target and a >=2R filter.

All detection uses only data up to the evaluated bar (no lookahead), so backtest and live
behave identically. See docs/PLATINUM_TRENDLINE_RULES.md §3-6.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional

from .config import Config
from .data import Candle, atr, swing_highs, swing_lows
from .trendlines import Trendline, find_valid_trendlines


@dataclass
class Signal:
    time: datetime
    symbol: str
    side: str            # "long" | "short"
    setup: str           # "bounce" | "break"
    entry: float
    stop: float
    target: float
    atr: float
    reason: str

    @property
    def risk(self) -> float:
        return abs(self.entry - self.stop)

    @property
    def rr(self) -> float:
        r = self.risk
        return abs(self.target - self.entry) / r if r else 0.0

    def as_dict(self) -> dict:
        d = asdict(self)
        d["time"] = self.time.strftime("%Y-%m-%d %H:%M:%S")
        d["risk"] = round(self.risk, 6)
        d["rr"] = round(self.rr, 3)
        return d


def _nearest_target(levels: List[float], entry: float, stop: float, side: str, min_rr: float) -> Optional[float]:
    """Closest real S/R level in the trade direction that still yields >= min_rr."""
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    if side == "long":
        cands = sorted(l for l in levels if l >= entry + min_rr * risk)
        return cands[0] if cands else None
    cands = sorted((l for l in levels if l <= entry - min_rr * risk), reverse=True)
    return cands[0] if cands else None


def generate_signal(candles: List[Candle], index: int, cfg: Config) -> Optional[Signal]:
    """Evaluate the candle at `index` for a bounce or break setup. Returns the best-RR signal."""
    if index < cfg.pivot_left + cfg.pivot_right + cfg.min_tap_gap:
        return None

    cur = candles[index]
    a = atr(candles, index, cfg.atr_period)
    tap_tol = cfg.tap_tol_atr * a
    break_tol = cfg.break_tol_atr * a
    buf = cfg.stop_buffer_atr * a

    lines = find_valid_trendlines(candles, index, cfg)
    if not lines:
        return None

    # Real S/R levels for targets = confirmed swing highs/lows.
    hi_idx = swing_highs(candles, cfg.pivot_left, cfg.pivot_right, upto=index)
    lo_idx = swing_lows(candles, cfg.pivot_left, cfg.pivot_right, upto=index)
    res_levels = [candles[i].high for i in hi_idx]
    sup_levels = [candles[i].low for i in lo_idx]

    lo = max(0, index - cfg.safety_lookback)
    recent_high = max(c.high for c in candles[lo:index + 1])
    recent_low = min(c.low for c in candles[lo:index + 1])

    candidates: List[Signal] = []

    for ln in lines:
        line_val = ln.value_at(index)

        if ln.kind == "support":
            # --- Bounce long: tag the line and reject upward ---
            touched = abs(cur.low - line_val) <= tap_tol
            if touched and cur.close > cur.open and cur.close > line_val:
                entry = cur.close
                stop = min(cur.low, line_val) - buf
                tgt = _nearest_target(res_levels, entry, stop, "long", cfg.min_rr)
                if tgt is not None:
                    candidates.append(Signal(cur.time, cfg.symbol, "long", "bounce", entry, stop, tgt, a,
                                             f"Bounce off support (slope {ln.slope:+.4f}, {len(ln.taps)} taps)"))

            # --- Break short: close decisively below support ---
            if cur.close < line_val - break_tol:
                entry = cur.close
                stop = recent_high + buf          # opposing "safety" structure
                tgt = _nearest_target(sup_levels, entry, stop, "short", cfg.min_rr)
                if tgt is not None:
                    candidates.append(Signal(cur.time, cfg.symbol, "short", "break", entry, stop, tgt, a,
                                             f"Break below support (slope {ln.slope:+.4f}, {len(ln.taps)} taps)"))

        else:  # resistance
            # --- Bounce short: tag the line and reject downward ---
            touched = abs(cur.high - line_val) <= tap_tol
            if touched and cur.close < cur.open and cur.close < line_val:
                entry = cur.close
                stop = max(cur.high, line_val) + buf
                tgt = _nearest_target(sup_levels, entry, stop, "short", cfg.min_rr)
                if tgt is not None:
                    candidates.append(Signal(cur.time, cfg.symbol, "short", "bounce", entry, stop, tgt, a,
                                             f"Bounce off resistance (slope {ln.slope:+.4f}, {len(ln.taps)} taps)"))

            # --- Break long: close decisively above resistance ---
            if cur.close > line_val + break_tol:
                entry = cur.close
                stop = recent_low - buf
                tgt = _nearest_target(res_levels, entry, stop, "long", cfg.min_rr)
                if tgt is not None:
                    candidates.append(Signal(cur.time, cfg.symbol, "long", "break", entry, stop, tgt, a,
                                             f"Break above resistance (slope {ln.slope:+.4f}, {len(ln.taps)} taps)"))

    if not candidates:
        return None
    # Prefer the highest reward:risk, then the tighter (lower-risk) setup.
    candidates.sort(key=lambda s: (s.rr, -s.risk), reverse=True)
    return candidates[0]
