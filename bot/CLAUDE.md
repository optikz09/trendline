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
- `config.contract_size` defaults to `1.0` (demo-only). In live the EA's `<symbol>_spec.json`
  overrides it with broker truth; in backtests it comes from config. Backtest costs
  (`spread`/`slippage`/`commission_per_lot`) default to 0 = ideal fills.
- **No proven edge yet**: on real HugosWay H4 data (`bot/data/XPTUSD240.csv`) the strategy is
  break-even before costs; most losses fight the HTF trend. Do not suggest going live.
- The user's HugosWay terminal data folder on this machine:
  `%APPDATA%\MetaQuotes\Terminal\0F19E7A51481BB64C858CDD0D2A04C81` (server `Hugosway-Live`).
  `run.py importhst` auto-discovers `.hst` history there.

## Top backlog (see HANDOFF.md §6)
HTF trend filter (top priority — see HANDOFF §5.2) → trade management (trailing/BE/partials) →
break-and-retest entry → unit tests for trendlines/strategy
(run `python -m unittest discover tests` from `bot/`).
