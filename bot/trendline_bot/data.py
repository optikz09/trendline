"""Candle model + CSV loading, plus ATR and swing-pivot helpers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


_TIME_KEYS = ("time", "date", "datetime", "timestamp")
_FMTS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y.%m.%d %H:%M",       # MT4 export format
    "%Y.%m.%d %H:%M:%S",
    "%Y-%m-%d",
)


def _parse_time(raw: str) -> datetime:
    raw = raw.strip()
    # epoch seconds?
    if raw.isdigit():
        return datetime.fromtimestamp(int(raw), tz=timezone.utc)
    for fmt in _FMTS:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised time format: {raw!r}")


def load_csv(path: str) -> List[Candle]:
    """Load OHLC(V) rows from a CSV with a header.

    Accepts columns time/date/datetime/timestamp + open/high/low/close (+ optional volume/tick_volume).
    Rows are returned sorted ascending by time.
    """
    candles: List[Candle] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = {c.lower().strip(): c for c in (reader.fieldnames or [])}
        tkey = next((cols[k] for k in _TIME_KEYS if k in cols), None)
        if tkey is None:
            raise ValueError(f"No time column in {path}; got {reader.fieldnames}")

        def col(*names: str) -> Optional[str]:
            for n in names:
                if n in cols:
                    return cols[n]
            return None

        okey = col("open", "o")
        hkey = col("high", "h")
        lkey = col("low", "l")
        ckey = col("close", "c")
        vkey = col("volume", "vol", "tick_volume", "tickvol")
        if not all([okey, hkey, lkey, ckey]):
            raise ValueError(f"Missing OHLC columns in {path}; got {reader.fieldnames}")

        for row in reader:
            candles.append(
                Candle(
                    time=_parse_time(row[tkey]),
                    open=float(row[okey]),
                    high=float(row[hkey]),
                    low=float(row[lkey]),
                    close=float(row[ckey]),
                    volume=float(row[vkey]) if vkey and row.get(vkey) else 0.0,
                )
            )
    candles.sort(key=lambda c: c.time)
    return candles


def infer_timeframe_minutes(candles: List[Candle]) -> Optional[float]:
    """Median spacing between candles, in minutes (None if <2 candles)."""
    if len(candles) < 2:
        return None
    gaps = sorted(
        (candles[i + 1].time - candles[i].time).total_seconds() / 60.0
        for i in range(len(candles) - 1)
    )
    return gaps[len(gaps) // 2]


def atr(candles: List[Candle], end: int, period: int) -> float:
    """Wilder-ish ATR over `period` bars ending at index `end` (simple mean of true range)."""
    if end <= 0:
        return abs(candles[end].high - candles[end].low) or 1e-9
    start = max(1, end - period + 1)
    trs = []
    for i in range(start, end + 1):
        h, l, pc = candles[i].high, candles[i].low, candles[i - 1].close
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return (sum(trs) / len(trs)) if trs else 1e-9


def swing_highs(candles: List[Candle], left: int, right: int, upto: Optional[int] = None) -> List[int]:
    """Indices of confirmed swing highs (fractals). Only pivots with `right` bars after them
    are returned, so nothing here uses future data relative to `upto`."""
    end = (len(candles) - 1) if upto is None else min(upto, len(candles) - 1)
    out = []
    for i in range(left, end - right + 1):
        piv = candles[i].high
        if all(candles[i - j].high <= piv for j in range(1, left + 1)) and all(
            candles[i + j].high <= piv for j in range(1, right + 1)
        ):
            out.append(i)
    return out


def swing_lows(candles: List[Candle], left: int, right: int, upto: Optional[int] = None) -> List[int]:
    end = (len(candles) - 1) if upto is None else min(upto, len(candles) - 1)
    out = []
    for i in range(left, end - right + 1):
        piv = candles[i].low
        if all(candles[i - j].low >= piv for j in range(1, left + 1)) and all(
            candles[i + j].low >= piv for j in range(1, right + 1)
        ):
            out.append(i)
    return out
