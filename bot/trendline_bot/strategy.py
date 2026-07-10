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


def trend_direction(candles: List[Candle], index: int, cfg: Config) -> int:
    """Daily-bias proxy (rulebook §1): +1 up / -1 down / 0 no opinion (off or warming up).

    Close vs the simple mean of the last `trend_filter_days` worth of bars on the trading
    timeframe — an indicator-free stand-in for "is the Daily chart pointing up or down".
    Uses only closes up to `index` (no lookahead).
    """
    if cfg.trend_filter_days <= 0:
        return 0
    bars_per_day = max(1, round(1440.0 / cfg.timeframe_minutes))
    period = max(2, int(cfg.trend_filter_days * bars_per_day))
    if index + 1 < period:
        return 0
    mean = sum(c.close for c in candles[index - period + 1: index + 1]) / period
    close = candles[index].close
    return 1 if close > mean else (-1 if close < mean else 0)


def _line_is_large(candles: List[Candle], ln: Trendline, cfg: Config) -> bool:
    """Break setups may demand a bigger line than the baseline A+ rules (rulebook §4;
    the pattern is breaks off the LARGE trendline highs/lows, not every 3-week line)."""
    if cfg.break_min_taps and len(ln.taps) < cfg.break_min_taps:
        return False
    if cfg.break_min_span_days:
        span = (candles[ln.taps[-1]].time - candles[ln.taps[0]].time).total_seconds() / 86400.0
        if span < cfg.break_min_span_days:
            return False
    return True


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

    trend = trend_direction(candles, index, cfg)
    candidates: List[Signal] = []

    for ln in lines:
        line_val = ln.value_at(index)

        if ln.kind == "support":
            # --- Bounce long: tag the line and reject upward (needs Daily bias up) ---
            touched = abs(cur.low - line_val) <= tap_tol
            if touched and trend >= 0 and cur.close > cur.open and cur.close > line_val:
                entry = cur.close
                stop = min(cur.low, line_val) - buf
                tgt = _nearest_target(res_levels, entry, stop, "long", cfg.min_rr)
                if tgt is not None:
                    candidates.append(Signal(cur.time, cfg.symbol, "long", "bounce", entry, stop, tgt, a,
                                             f"Bounce off support (slope {ln.slope:+.4f}, {len(ln.taps)} taps)"))

            # --- Break short: close decisively below a large support line ---
            if cur.close < line_val - break_tol and _line_is_large(candles, ln, cfg):
                entry = cur.close
                stop = recent_high + buf          # opposing "safety" structure
                tgt = _nearest_target(sup_levels, entry, stop, "short", cfg.min_rr)
                if tgt is not None:
                    candidates.append(Signal(cur.time, cfg.symbol, "short", "break", entry, stop, tgt, a,
                                             f"Break below support (slope {ln.slope:+.4f}, {len(ln.taps)} taps)"))

        else:  # resistance
            # --- Bounce short: tag the line and reject downward (needs Daily bias down) ---
            touched = abs(cur.high - line_val) <= tap_tol
            if touched and trend <= 0 and cur.close < cur.open and cur.close < line_val:
                entry = cur.close
                stop = max(cur.high, line_val) + buf
                tgt = _nearest_target(sup_levels, entry, stop, "short", cfg.min_rr)
                if tgt is not None:
                    candidates.append(Signal(cur.time, cfg.symbol, "short", "bounce", entry, stop, tgt, a,
                                             f"Bounce off resistance (slope {ln.slope:+.4f}, {len(ln.taps)} taps)"))

            # --- Break long: close decisively above a large resistance line ---
            if cur.close > line_val + break_tol and _line_is_large(candles, ln, cfg):
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
