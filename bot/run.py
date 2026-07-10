#!/usr/bin/env python3
"""TrendLine Trading bot — command line entry point.

    python run.py scan     --data sample_data/XPTUSD_H4.csv        # latest closed-bar signal
    python run.py backtest --data sample_data/XPTUSD_H4.csv        # walk-forward stats
    python run.py live     --bridge ./bridge --broker mt4          # live loop -> MT4 EA
    python run.py gensample --out sample_data/XPTUSD_H4.csv        # regenerate demo data

Config: pass --config config.json to override any default in trendline_bot/config.py.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trendline_bot.backtest import run_backtest
from trendline_bot.broker import make_broker, position_size
from trendline_bot.config import Config
from trendline_bot.data import infer_timeframe_minutes, load_csv
from trendline_bot.live import run_live
from trendline_bot.strategy import generate_signal


def _load_cfg(args) -> Config:
    cfg = Config.from_file(args.config) if args.config else Config()
    if getattr(args, "symbol", None):
        cfg.symbol = args.symbol
    return cfg


def cmd_scan(args) -> int:
    cfg = _load_cfg(args)
    candles = load_csv(args.data)
    tf = infer_timeframe_minutes(candles)
    if tf is not None and tf < 59:
        print(f"WARNING: data spacing ~{tf:.0f}m is below the hourly minimum this bot targets.")
    idx = len(candles) - 1
    sig = generate_signal(candles, idx, cfg)
    if sig is None:
        print(f"No setup on the latest bar ({candles[idx].time}).")
        return 0
    lots = position_size(cfg, sig)
    print("SIGNAL")
    for k, v in sig.as_dict().items():
        print(f"  {k:8}: {v}")
    print(f"  {'lots':8}: {lots}  (risking {cfg.risk_per_trade*100:.1f}% of {cfg.account_balance:g})")
    return 0


def cmd_backtest(args) -> int:
    cfg = _load_cfg(args)
    candles = load_csv(args.data)
    result = run_backtest(candles, cfg)
    if args.verbose:
        for t in result.trades:
            s = t.signal
            print(f"{s.time:%Y-%m-%d %H:%M}  {s.side:<5} {s.setup:<6} "
                  f"entry {s.entry:8.2f} stop {s.stop:8.2f} tp {s.target:8.2f}  "
                  f"-> {t.outcome:<6} {t.r:+.2f}R")
    print(result.summary())
    return 0


def cmd_live(args) -> int:
    cfg = _load_cfg(args)
    broker = make_broker(args.broker, cfg, args.bridge)
    run_live(cfg, broker, args.bridge, once=args.once)
    return 0


def cmd_gensample(args) -> int:
    from gen_sample import generate  # local helper
    generate(args.out)
    print(f"Wrote sample data to {args.out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="TrendLine Trading bot")
    p.add_argument("--config", help="path to a JSON config file")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="print the signal (if any) on the latest bar")
    s.add_argument("--data", required=True)
    s.add_argument("--symbol")
    s.set_defaults(func=cmd_scan)

    b = sub.add_parser("backtest", help="walk the series and report stats")
    b.add_argument("--data", required=True)
    b.add_argument("--symbol")
    b.add_argument("-v", "--verbose", action="store_true")
    b.set_defaults(func=cmd_backtest)

    l = sub.add_parser("live", help="poll the MT4 rates file and route signals to a broker")
    l.add_argument("--bridge", default="./bridge", help="shared folder with the MT4 EA")
    l.add_argument("--broker", default="paper", choices=["paper", "mt4"])
    l.add_argument("--symbol")
    l.add_argument("--once", action="store_true", help="evaluate one cycle and exit")
    l.set_defaults(func=cmd_live)

    g = sub.add_parser("gensample", help="regenerate the demo dataset")
    g.add_argument("--out", default="sample_data/XPTUSD_H4.csv")
    g.set_defaults(func=cmd_gensample)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
