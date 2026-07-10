# TrendLine Trading bot — context for Claude

You are working on a swing-trading bot for **Platinum (XPTUSD)** on **hourly-and-up** timeframes,
built to execute on a **HugosWay PRO4 / MT4** account. Full continuity notes are in
[`HANDOFF.md`](./HANDOFF.md) — read it before making non-trivial changes.

## Orientation
- **Rules the code encodes:** `../docs/PLATINUM_TRENDLINE_RULES.md` (Tori-Trades trendline method).
- **Core logic:** `trendline_bot/strategy.py` (Bounce + Break) and `trendline_bot/trendlines.py`.
- **All tunables:** `trendline_bot/config.py` (or a JSON config passed with `--config`).
- **Live bridge:** bot ↔ `mt4/TrendLineTradingBridge.mq4` exchange CSV/JSONL files in MT4's
  `MQL4/Files/trendline_bridge` folder. See HANDOFF.md §3.

## Conventions
- **Pure Python 3.9+ standard library — do not add pip dependencies** without asking.
- Signal detection must use **only data up to the evaluated bar** (no lookahead) so backtest == live.
- This bot trades **H1 and above only**; keep the sub-hourly guard in `data.py`/`live.py`.
- Verify changes with `python3 run.py backtest --data sample_data/XPTUSD_H4.csv` before committing.

## Live-trading footguns (state these when relevant)
- `config.contract_size` defaults to `1.0` (demo-only) — must match the broker's platinum contract
  size or sizing is wrong. Backtest costs (`spread`/`slippage`/`commission_per_lot`) default to 0 =
  ideal fills; set them from real HugosWay quotes before trusting expectancy.

## Top backlog (see HANDOFF.md §6)
Trade management (trailing/BE/partials) → break-and-retest entry → unit tests for
trendlines/strategy (cost-model tests exist: `python -m unittest discover tests` from `bot/`).
