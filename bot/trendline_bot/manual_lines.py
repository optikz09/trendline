"""Trade the user's own hand-drawn trendlines.

The EA exports every trendline object on the chart to <bridge>/<symbol>_lines.csv
(name, two anchor points). The rule is exactly as simple as it sounds: when a bar
CLOSES across one of those lines, trade in the direction of the cross — up = buy,
down = sell. Stop goes past the recent swing (safety_lookback + stop_buffer_atr);
target is a fixed `min_rr` multiple of the risk. Nothing else.

When a lines file is present with at least one line, the live loop uses this INSTEAD
of the auto-fitted trendlines.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .config import Config
from .data import Candle, atr, _parse_time
from .strategy import Signal


@dataclass
class ManualLine:
    name: str
    t1: datetime
    p1: float
    t2: datetime
    p2: float

    def value_at(self, when: datetime) -> Optional[float]:
        """Price of the (rightward-extended) line at `when`. None for degenerate lines."""
        dt = (self.t2 - self.t1).total_seconds()
        if dt == 0:
            return None
        slope = (self.p2 - self.p1) / dt
        return self.p1 + slope * (when - self.t1).total_seconds()


def load_lines(path: str) -> List[ManualLine]:
    if not os.path.exists(path):
        return []
    lines: List[ManualLine] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                lines.append(ManualLine(
                    name=row["name"].strip(),
                    t1=_parse_time(row["time1"]), p1=float(row["price1"]),
                    t2=_parse_time(row["time2"]), p2=float(row["price2"]),
                ))
            except (KeyError, ValueError):
                continue   # skip malformed rows, keep watching the rest
    return lines


def cross_signal(candles: List[Candle], index: int, lines: List[ManualLine],
                 cfg: Config) -> Optional[Signal]:
    """Did the bar at `index` CLOSE across any of the user's lines? First cross wins."""
    if index < 1 or not lines:
        return None
    prev, cur = candles[index - 1], candles[index]
    a = atr(candles, index, cfg.atr_period)
    buf = cfg.stop_buffer_atr * a
    lo = max(0, index - cfg.safety_lookback)
    recent_high = max(c.high for c in candles[lo:index + 1])
    recent_low = min(c.low for c in candles[lo:index + 1])

    for ln in lines:
        v_prev = ln.value_at(prev.time)
        v_cur = ln.value_at(cur.time)
        if v_prev is None or v_cur is None:
            continue

        crossed_up = prev.close <= v_prev and cur.close > v_cur
        crossed_down = prev.close >= v_prev and cur.close < v_cur
        if not (crossed_up or crossed_down):
            continue

        side = "long" if crossed_up else "short"
        entry = cur.close
        stop = (recent_low - buf) if crossed_up else (recent_high + buf)
        risk = abs(entry - stop)
        if risk <= 0:
            continue
        target = entry + cfg.min_rr * risk if crossed_up else entry - cfg.min_rr * risk
        return Signal(cur.time, cfg.symbol, side, "manual-break", entry, stop, target, a,
                      f"Close crossed {'above' if crossed_up else 'below'} drawn line '{ln.name}'")
    return None
