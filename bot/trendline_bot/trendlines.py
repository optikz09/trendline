"""Fit valid ("A+") trendlines from swing pivots, per rulebook §2.

A support line rides under the swing lows; a resistance line rides over the swing highs.
A line is only tradeable when it has >=3 taps, taps >=6 candles apart, spans >=3 weeks,
and is shallow enough (|slope| under max_norm_slope ATRs per candle).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .config import Config
from .data import Candle, atr, swing_highs, swing_lows


@dataclass
class Trendline:
    kind: str            # "support" or "resistance"
    slope: float         # price change per candle-index
    intercept: float     # price at index 0
    taps: List[int]      # candle indices that touch the line
    atr_at_fit: float

    def value_at(self, index: int) -> float:
        return self.slope * index + self.intercept


def _price(c: Candle, kind: str) -> float:
    return c.low if kind == "support" else c.high


def _fit_kind(candles: List[Candle], pivots: List[int], kind: str, cfg: Config, a: float) -> List[Trendline]:
    tol = cfg.tap_tol_atr * a
    pts = [(i, _price(candles[i], kind)) for i in pivots]
    lines: List[Trendline] = []

    for x in range(len(pts)):
        for y in range(x + 1, len(pts)):
            i1, p1 = pts[x]
            i2, p2 = pts[y]
            if i2 == i1:
                continue
            slope = (p2 - p1) / (i2 - i1)
            intercept = p1 - slope * i1

            # A support line may not sit above any low (and vice-versa) by more than tol.
            valid = True
            taps: List[int] = []
            for i, p in pts:
                diff = p - (slope * i + intercept)
                if kind == "support":
                    if diff < -tol:            # a low pierces well below -> not a real support
                        valid = False
                        break
                else:
                    if diff > tol:             # a high pokes well above -> not a real resistance
                        valid = False
                        break
                if abs(diff) <= tol:
                    taps.append(i)
            if not valid or len(taps) < cfg.min_taps:
                continue

            taps = sorted(set(taps))
            if any(taps[k + 1] - taps[k] < cfg.min_tap_gap for k in range(len(taps) - 1)):
                continue
            span_days = (candles[taps[-1]].time - candles[taps[0]].time).total_seconds() / 86400.0
            if span_days < cfg.min_span_days:
                continue
            if abs(slope) > cfg.max_norm_slope * a:
                continue

            lines.append(Trendline(kind, slope, intercept, taps, a))

    return _dedupe(lines)


def _dedupe(lines: List[Trendline]) -> List[Trendline]:
    """Keep the strongest line per near-duplicate (most taps, then most recent last tap)."""
    kept: List[Trendline] = []
    for ln in sorted(lines, key=lambda l: (len(l.taps), l.taps[-1]), reverse=True):
        dup = False
        for k in kept:
            if k.kind != ln.kind:
                continue
            # similar if slope and current intercept are within a tap tolerance band
            if abs(k.slope - ln.slope) <= 0.2 * k.atr_at_fit and set(ln.taps) & set(k.taps):
                dup = True
                break
        if not dup:
            kept.append(ln)
    return kept


def find_valid_trendlines(candles: List[Candle], upto: int, cfg: Config) -> List[Trendline]:
    """All currently-valid trendlines using only data confirmed at or before `upto`."""
    a = atr(candles, upto, cfg.atr_period)
    highs = swing_highs(candles, cfg.pivot_left, cfg.pivot_right, upto=upto)
    lows = swing_lows(candles, cfg.pivot_left, cfg.pivot_right, upto=upto)
    return _fit_kind(candles, lows, "support", cfg, a) + _fit_kind(candles, highs, "resistance", cfg, a)
