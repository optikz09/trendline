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
                  f"-> {t.outcome:<6} {t.r:+.2f}R  {t.days_held:5.1f}d")
    print(result.summary())
    return 0


def cmd_live(args) -> int:
    cfg = _load_cfg(args)
    broker = make_broker(args.broker, cfg, args.bridge)
    run_live(cfg, broker, args.bridge, once=args.once)
    return 0


def cmd_importhst(args) -> int:
    from trendline_bot.mt4data import find_hst, read_hst, write_csv
    cfg = _load_cfg(args)
    symbol = args.symbol or cfg.symbol
    tf = args.timeframe or cfg.timeframe_minutes

    path = args.hst
    if not path:
        found = find_hst(symbol, tf)
        if not found:
            print(f"No {symbol}{tf}.hst found under %APPDATA%\\MetaQuotes\\Terminal.\n"
                  f"Open a {symbol} chart at that timeframe in MT4 (scroll back for more "
                  f"history), then retry — or pass --hst <path>.")
            return 1
        path = found[0]
        if len(found) > 1:
            print(f"Found {len(found)} candidates; using newest: {path}")

    hst = read_hst(path)
    if not hst.candles:
        print(f"{path}: no bars.")
        return 1
    out = args.out or os.path.join("data", f"{symbol}{tf}.csv")
    write_csv(hst.candles, out)
    first, last = hst.candles[0].time, hst.candles[-1].time
    print(f"Wrote {len(hst.candles)} bars ({first:%Y-%m-%d} .. {last:%Y-%m-%d}) -> {out}")
    print(f"  source : {path} (HST v{hst.version}, {hst.digits} digits)")

    stats = hst.spread_stats()
    if stats:
        print(f"  spread : median {stats['median_price']:.2f} / mean {stats['mean_price']:.2f} "
              f"price units over {stats['bars']} bars — set \"spread\": {stats['median_price']:.2f} "
              f"in config.json for realistic backtests")
    else:
        print("  spread : not recorded in this file — use the EA's spec.json export instead")
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

    h = sub.add_parser("importhst", help="convert MT4 .hst history (real broker data) to bot CSV")
    h.add_argument("--symbol", help="broker symbol (default: config symbol)")
    h.add_argument("--timeframe", type=int, help="minutes, e.g. 240 (default: config timeframe)")
    h.add_argument("--hst", help="explicit .hst path (default: auto-discover in %%APPDATA%%)")
    h.add_argument("--out", help="output CSV (default: data/<symbol><tf>.csv)")
    h.set_defaults(func=cmd_importhst)

    g = sub.add_parser("gensample", help="regenerate the demo dataset")
    g.add_argument("--out", default="sample_data/XPTUSD_H4.csv")
    g.set_defaults(func=cmd_gensample)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
