#!/usr/bin/env python3
"""Generate a deterministic H4 demo series for XPTUSD.

Builds a market that (a) rides up along a clean support trendline with several taps and
bounces, then (b) breaks that line to the downside — so both setups appear. Seeded, so the
committed sample_data/XPTUSD_H4.csv is reproducible.
"""

from __future__ import annotations

import csv
import os
import random
from datetime import datetime, timedelta


def generate(out_path: str, seed: int = 7) -> None:
    rng = random.Random(seed)
    start = datetime(2025, 1, 6, 0, 0)   # a Monday
    step = timedelta(hours=4)

    rows = []
    price = 950.0
    support_base = 940.0       # support line value at bar 0
    support_slope = 0.55       # rises per bar -> shallow uptrend
    t = start

    # Phase 1: 320 bars trending up, respecting the support line with periodic taps.
    n_up = 320
    for i in range(n_up):
        line = support_base + support_slope * i
        # gentle mean-reversion toward a level well above the support line
        target = line + 22 + 6 * rng.random()
        price += (target - price) * 0.05 + rng.uniform(-3.2, 3.2)
        # every ~26 bars, dip down to tap the support line and bounce
        if i % 26 == 0 and i > 0:
            price = line + rng.uniform(0.5, 2.5)
        price = max(price, line + 0.3)   # never close below support in phase 1
        o = price + rng.uniform(-2, 2)
        c = price
        hi = max(o, c) + rng.uniform(0.5, 3.5)
        # let the low tag the line on tap bars
        lo = min(o, c) - rng.uniform(0.5, 3.5)
        if i % 26 == 0 and i > 0:
            lo = line - rng.uniform(0.0, 1.2)
        rows.append((t, o, hi, lo, c))
        t += step

    # Phase 2: 120 bars that break the support line and trend down.
    n_down = 120
    for j in range(n_down):
        i = n_up + j
        line = support_base + support_slope * i
        target = line - 18 - 8 * rng.random()   # pull below the (now broken) line
        price += (target - price) * 0.06 + rng.uniform(-3.2, 3.2)
        o = price + rng.uniform(-2, 2)
        c = price
        hi = max(o, c) + rng.uniform(0.5, 3.5)
        lo = min(o, c) - rng.uniform(0.5, 3.5)
        rows.append((t, o, hi, lo, c))
        t += step

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["time", "open", "high", "low", "close", "volume"])
        for (ts, o, h, l, c) in rows:
            w.writerow([ts.strftime("%Y-%m-%d %H:%M:%S"),
                        f"{o:.2f}", f"{h:.2f}", f"{l:.2f}", f"{c:.2f}", rng.randint(500, 5000)])


if __name__ == "__main__":
    import sys
    generate(sys.argv[1] if len(sys.argv) > 1 else "sample_data/XPTUSD_H4.csv")
    print("done")
