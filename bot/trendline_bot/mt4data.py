"""Read MT4 .hst history files directly from the terminal's data folder.

The whole point of this bot is to trade through MT4, so MT4 is also the source of truth
for data: instead of synthetic samples or manual exports, pull the broker's own history
(`<terminal>/history/<server>/<SYMBOL><TF>.hst`) and convert it to the bot's CSV format.

Supports both HST layouts:
  v401 (build 600+): 148-byte header, 60-byte records incl. a per-bar spread (points)
  v400 (legacy)    : 148-byte header, 44-byte records (time, open, low, high, close, volume)

Pure stdlib, like everything else here.
"""

from __future__ import annotations

import glob
import os
import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from .data import Candle

_HEADER_SIZE = 148
_REC_401 = struct.Struct("<q4dqiq")   # time i64, OHLC f64, tick_volume i64, spread i32, real_volume i64
_REC_400 = struct.Struct("<i5d")      # time i32, open, low, high, close, volume (all f64)


@dataclass
class HstFile:
    path: str
    version: int
    symbol: str
    period: int               # timeframe in minutes
    digits: int
    candles: List[Candle]
    spreads_points: List[int] = field(default_factory=list)   # per bar, v401 only (often 0)

    @property
    def point(self) -> float:
        return 10.0 ** -self.digits

    def spread_stats(self) -> Optional[dict]:
        """Median/mean recorded spread in points and price units (None if not recorded)."""
        vals = sorted(s for s in self.spreads_points if s > 0)
        if not vals:
            return None
        median = float(vals[len(vals) // 2])
        mean = sum(vals) / len(vals)
        return {
            "bars": len(vals),
            "median_points": median,
            "mean_points": mean,
            "median_price": median * self.point,
            "mean_price": mean * self.point,
        }


def read_hst(path: str) -> HstFile:
    with open(path, "rb") as fh:
        hdr = fh.read(_HEADER_SIZE)
        if len(hdr) < _HEADER_SIZE:
            raise ValueError(f"{path}: truncated HST header")
        (version,) = struct.unpack_from("<i", hdr, 0)
        symbol = hdr[68:80].split(b"\x00")[0].decode("ascii", "replace")
        period, digits = struct.unpack_from("<ii", hdr, 80)

        candles: List[Candle] = []
        spreads: List[int] = []
        if version >= 401:
            while True:
                buf = fh.read(_REC_401.size)
                if len(buf) < _REC_401.size:
                    break
                t, o, h, l, c, vol, spread, _rvol = _REC_401.unpack(buf)
                candles.append(Candle(datetime.fromtimestamp(t, tz=timezone.utc), o, h, l, c, float(vol)))
                spreads.append(spread)
        else:
            while True:
                buf = fh.read(_REC_400.size)
                if len(buf) < _REC_400.size:
                    break
                t, o, l, h, c, vol = _REC_400.unpack(buf)   # note: v400 stores O,L,H,C
                candles.append(Candle(datetime.fromtimestamp(t, tz=timezone.utc), o, h, l, c, float(vol)))

    candles_sorted = sorted(candles, key=lambda c: c.time)
    if candles_sorted != candles:   # keep spreads aligned if we had to sort
        order = sorted(range(len(candles)), key=lambda i: candles[i].time)
        spreads = [spreads[i] for i in order] if spreads else spreads
        candles = candles_sorted
    return HstFile(path, version, symbol, period, digits, candles, spreads)


def find_hst(symbol: str, timeframe_minutes: int, appdata: Optional[str] = None) -> List[str]:
    """Locate `<SYMBOL><TF>.hst` across all installed MT4 terminals, newest first."""
    appdata = appdata or os.environ.get("APPDATA", "")
    pattern = os.path.join(appdata, "MetaQuotes", "Terminal", "*", "history", "*",
                           f"{symbol}{timeframe_minutes}.hst")
    return sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)


def write_csv(candles: List[Candle], out_path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write("time,open,high,low,close,volume\n")
        for c in candles:
            fh.write(f"{c.time:%Y-%m-%d %H:%M:%S},{c.open},{c.high},{c.low},{c.close},{c.volume:g}\n")
