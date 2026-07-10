"""Live loop.

Reads a rates CSV that the MT4 EA continuously exports for `symbol` at the configured
timeframe, evaluates the most recently *closed* bar, and routes any signal to the broker.
De-dupes so each closed bar fires at most one order.

Data flow (file bridge):
    MT4 EA  --writes-->  <bridge>/<symbol>_<tf>_rates.csv   --read by--> this loop
    this loop --writes--> <bridge>/commands.jsonl           --read by--> MT4 EA (executes)
"""

from __future__ import annotations

import os
import time
from typing import Optional

from .broker import Broker, position_size
from .config import Config
from .data import Candle, infer_timeframe_minutes, load_csv
from .strategy import generate_signal


def rates_filename(cfg: Config) -> str:
    return f"{cfg.symbol}_{cfg.timeframe_minutes}_rates.csv"


def _guard_timeframe(candles, cfg: Config) -> None:
    tf = infer_timeframe_minutes(candles)
    if tf is not None and tf < 59:  # allow tiny jitter under 60
        raise SystemExit(
            f"Refusing to run: data spacing ~{tf:.0f}m is below the hourly minimum. "
            "This bot only trades hourly-and-up timeframes."
        )


def run_live(cfg: Config, broker: Broker, bridge_dir: str, once: bool = False) -> None:
    rates_path = os.path.join(bridge_dir, rates_filename(cfg))
    last_bar_time: Optional[str] = None
    print(f"[LIVE] watching {rates_path} every {cfg.poll_seconds}s for {cfg.symbol} "
          f"@ {cfg.timeframe_minutes}m")

    while True:
        try:
            if os.path.exists(rates_path):
                candles = load_csv(rates_path)
                if len(candles) >= 2:
                    _guard_timeframe(candles, cfg)
                    # Evaluate the last CLOSED bar (assume the final row may still be forming).
                    closed = len(candles) - 2
                    stamp = candles[closed].time.strftime("%Y-%m-%d %H:%M")
                    if stamp != last_bar_time:
                        last_bar_time = stamp
                        sig = generate_signal(candles, closed, cfg)
                        if sig is None:
                            print(f"[LIVE] {stamp}  no setup")
                        else:
                            lots = position_size(cfg, sig)
                            oid = broker.place(sig, lots)
                            print(f"[LIVE] {stamp}  SIGNAL {sig.side} {sig.setup} "
                                  f"{sig.rr:.2f}R -> {oid}")
            else:
                print(f"[LIVE] waiting for rates file: {rates_path}")
        except SystemExit:
            raise
        except Exception as exc:  # keep the loop alive; log and retry
            print(f"[LIVE] error: {exc}")

        if once:
            return
        time.sleep(cfg.poll_seconds)
