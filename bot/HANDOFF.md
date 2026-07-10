# TrendLine Trading — Handoff / Continuity Export

Everything needed to continue this project locally (or in a fresh Claude session). This is the
single source of truth for *what was built, why, and what's left*.

- **Repo:** https://github.com/optikz09/trendline (standalone; migrated out of the old PPTtoSVG repo)
- **Default branch:** `main`
- **Project name:** TrendLine Trading
- **Goal:** a simple, live-capable swing bot trading **Platinum (XPTUSD)** on **hourly-and-up**
  timeframes, executing on a **HugosWay PRO4 / MT4** leveraged account.

## 0. Pull it locally

```bash
git clone https://github.com/optikz09/trendline
cd trendline/bot
python3 run.py backtest --data sample_data/XPTUSD_H4.csv -v   # confirm it runs (stdlib only)
```

No dependencies to install — pure Python 3.9+ standard library.

## 1. What exists

| Path | Purpose |
|------|---------|
| `docs/PLATINUM_TRENDLINE_RULES.md` | The trading rulebook (Tori-Trades trendline method, adapted to Platinum). Source of every rule the bot encodes. |
| `bot/trendline_bot/config.py` | All tunables — strategy, risk, bridge. Edit here or via a JSON config. |
| `bot/trendline_bot/data.py` | `Candle`, CSV loader (incl. MT4 time format), ATR, swing-pivot detection. |
| `bot/trendline_bot/trendlines.py` | Fits valid "A+" trendlines. |
| `bot/trendline_bot/strategy.py` | Bounce + Break signal engine. **The core logic.** |
| `bot/trendline_bot/backtest.py` | Event-driven walk-forward backtester. |
| `bot/trendline_bot/broker.py` | Position sizing + `PaperBroker` + `FileBridgeBroker` (MT4). |
| `bot/trendline_bot/live.py` | Live poll loop; folds the EA's `<symbol>_spec.json` (broker truth) into the config. |
| `bot/trendline_bot/mt4data.py` | Reads MT4 `.hst` history files directly from the terminal — real broker data for backtests. |
| `bot/run.py` | CLI: `scan` / `backtest` / `live` / `importhst` / `gensample`. |
| `bot/data/XPTUSD240.csv` | Real HugosWay-Live platinum H4 (2024-10 .. 2026-02), imported via `importhst`. |
| `bot/gen_sample.py` | Regenerates the deterministic demo dataset. |
| `bot/sample_data/XPTUSD_H4.csv` | Committed demo series (contains bounce + break setups). |
| `bot/config.example.json` | Copy to `config.json` (git-ignored) and edit for live. |
| `bot/tests/` | Unit tests (stdlib `unittest`) — `python -m unittest discover tests` from `bot/`. |
| `mt4/TrendLineTradingBridge.mq4` | Expert Advisor: exports rates + executes queued orders inside PRO4/MT4. |

## 2. The strategy in one screen (encoded rules)

Detection uses **only data up to the evaluated bar** (no lookahead) so backtest == live.

**Valid "A+" trendline** (`trendlines.py`): ≥3 taps · taps ≥6 candles apart · spans ≥3 weeks ·
`|slope|` under `max_norm_slope` ATRs/candle (an ATR-normalised stand-in for the visual "<45°"
rule) · a support line may not sit above any low (resistance: below any high) beyond `tap_tol_atr`.

**Two setups** (`strategy.py`):
- **Bounce** — price tags the line (`low`/`high` within `tap_tol_atr`) and closes back with a
  same-direction candle. Stop just past the line; target = nearest real S/R giving ≥ `min_rr` (2R).
- **Break** — a candle *closes* through the line by more than `break_tol_atr`. Stop on the opposing
  "safety" structure (recent swing over `safety_lookback`); target = nearest S/R giving ≥ 2R.

If no real S/R target reaches 2R, **the signal is skipped**. Among all candidates on a bar the
engine takes the highest-RR one (`strategy.generate_signal` → sort by `(rr, -risk)`).

**Sizing** (`broker.position_size`): `lots = (balance × risk_per_trade) / (stop_distance × contract_size)`,
snapped to `lot_step`, clamped to `[min_lot, max_lot]`.

## 3. Live architecture (file bridge, no broker API)

```
MT4 EA  --writes-->  <bridge>/XPTUSD_240_rates.csv   --read by--> bot live loop
MT4 EA  --writes-->  <bridge>/XPTUSD_spec.json       --read by--> bot (broker truth, ~1/min)
bot     --writes-->  <bridge>/commands.jsonl         --read by--> MT4 EA (OrderSend)
MT4 EA  --writes-->  <bridge>/acks.jsonl             (fill/error status, one per id)
```

`spec.json` carries the broker's real contract size, lot limits, running average spread, and
account balance. The live loop overrides the matching config fields with it every cycle, so
sizing-critical numbers are never hand-typed (this retires the `contract_size` footgun in live —
it still matters for offline backtest configs).

- `<bridge>` is the terminal's `MQL4/Files/trendline_bridge` folder (EA creates it).
- Command protocol: one JSON object per line in `commands.jsonl`
  (`{id, action:"OPEN", symbol, side, lots, entry, sl, tp, setup, ts}`).
- Idempotent by design: the EA tracks processed ids and never re-fills; the bot resumes its
  command sequence from the existing file. Restart either side safely.
- The live loop evaluates the **second-to-last** row (the last *closed* bar), de-duped by bar time.

## 4. Design decisions (the "why")

- **Pure stdlib, no pandas/numpy** — keeps it trivially portable and easy to run inside any MT4
  host box. Line-fitting is O(pivots²), fine for hourly+ history.
- **File bridge over a socket/ZeroMQ/DLL** — simplest thing that works, no MT4 DLL imports, robust
  to restarts, and easy to inspect/debug by eye. Can be upgraded to ZeroMQ later if latency matters
  (it doesn't for H1+ swing trading).
- **Broker seam (`Broker` ABC)** — strategy emits `Signal`s; swapping `PaperBroker`↔`FileBridgeBroker`
  is the only change from dry-run to live. A native HugosWay/MT5 adapter could slot in here.
- **Stop-before-target in backtest** — when a bar's range spans both, assume the stop hit first
  (conservative; avoids flattering results).
- **`contract_size` is a config knob, not hardcoded** — because it's the #1 live-sizing footgun.

## 5. Known limitations / risks (READ before trading real money)

1. **`contract_size` default `1.0` is demo-only.** In live the EA's `spec.json` overrides it with
   broker truth automatically (watch for the `[LIVE] broker spec:` log line before trusting lots);
   for backtests/scans it still comes from config. Verify lots on a demo/cent account first.
2. **No proven edge.** On real HugosWay H4 data (2024-10..2026-02, `bot/data/XPTUSD240.csv`) the
   strategy is break-even before costs: 17 trades, 35% win rate, +0.02R/trade — i.e. losing after
   spread. Most losers are break-shorts fighting the 2025 platinum uptrend; the HTF trend filter
   (backlog) is the obvious next lever. Do not trade this live yet.
3. **`max_norm_slope` "45°" filter is an approximation** of a visual rule; tune per instrument.
4. **No trade management yet** — no trailing stop, break-even move, or partial take-profit. One
   position at a time; entry at bar close.
5. **Cost defaults are zero.** The backtest models spread/slippage/commission (config `spread`,
   `slippage`, `commission_per_lot`) but they default to 0 = ideal fills. Measure HugosWay's real
   platinum spread and set them before trusting expectancy — on the synthetic sample, a $1 spread
   alone flips the result from break-even to negative.
6. **The live loop assumes the last CSV row may be a forming bar.** If the EA only ever writes
   closed bars, the loop is one bar late — acceptable for swing trading, but note it.

## 6. Open next steps (suggested backlog)

- [x] **Cost model** in the backtest (spread + commission + slippage) — config `spread`/`slippage`/
      `commission_per_lot`, charged as a flat R deduction per round turn; tests in `bot/tests/`.
- [ ] **Trade management**: break-even at 1R, ATR trailing stop, optional partial at 2R (rulebook §6).
- [ ] **Break-and-retest entry** variant (higher win-rate than raw break; rulebook §4).
- [ ] **Unit tests** for `trendlines.py` and `strategy.py` (pin behaviour on the sample data;
      cost-model tests exist — run `python -m unittest discover tests` from `bot/`).
- [ ] **Higher-timeframe trend filter** (only take longs when Daily/Weekly trend is up, etc.) —
      *promoted to top priority*: on real data most losses are break-shorts against the 2025 uptrend.
- [x] **Real historical Platinum data** — `run.py importhst` reads the terminal's `.hst` files
      directly (`bot/data/XPTUSD240.csv`, HugosWay-Live H4 2024-10..2026-02). Open the XPTUSD chart
      and scroll back in MT4 to deepen history, then re-run `importhst`.
- [x] **Broker spec bridge** — EA exports `<symbol>_spec.json` (contract size, lot limits, live
      average spread, balance); live loop folds it into the config every cycle.
- [ ] **acks.jsonl consumption** in the bot (surface fills/errors back into the live log).
- [x] Migrated to its own repo (`optikz09/trendline`), out of the legacy PPTtoSVG repo.

## 7. Common commands

```bash
cd bot
python3 run.py backtest --data sample_data/XPTUSD_H4.csv -v      # stats + every trade
python3 run.py scan     --data sample_data/XPTUSD_H4.csv         # latest-bar signal
python3 run.py --config config.json live --bridge "<MQL4/Files/trendline_bridge>" --broker paper
python3 run.py --config config.json live --bridge "<...>"        --broker mt4     # sends orders
python3 run.py gensample --out sample_data/XPTUSD_H4.csv         # regenerate demo data
python3 run.py importhst                                          # pull real MT4 history -> data/
python3 -m unittest discover tests                                # unit tests
```

## 8. Go-live checklist (HugosWay / PRO4)

1. Copy `mt4/TrendLineTradingBridge.mq4` → terminal `MQL4/Experts/`, compile in MetaEditor.
2. Attach EA to one chart of your Platinum symbol at the H1+ TF you'll trade. Enable AutoTrading +
   "Allow live trading".
3. `config.json`: set `symbol` to the exact broker symbol, `timeframe_minutes` to the chart TF,
   `contract_size` to the broker's platinum contract size, `account_balance` + `risk_per_trade`.
4. Run with `--broker paper` first; confirm signals look sane in the log.
5. Switch to `--broker mt4` on a **demo/cent** account; confirm orders appear with correct lots/SL/TP.
6. Only then consider a small live account. Set real costs in the config (`spread`, `slippage`,
   `commission_per_lot`) and add trade management first.
