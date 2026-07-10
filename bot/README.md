# TrendLine Trading Bot

A dependency-light (pure Python 3.9+, standard library only) swing-trading bot that implements
the trendline method in [`docs/PLATINUM_TRENDLINE_RULES.md`](../docs/PLATINUM_TRENDLINE_RULES.md).
It works on **hourly-and-up** timeframes only and is wired to run **live** against a
HugosWay **PRO4 / MT4** account through a file bridge + companion Expert Advisor.

```
bot/
  run.py                     CLI: scan | backtest | live | gensample
  gen_sample.py              deterministic demo data generator
  config.example.json        copy to config.json and edit
  sample_data/XPTUSD_H4.csv  committed demo series (has bounce + break setups)
  trendline_bot/
    config.py                every tunable (strategy + risk + bridge)
    data.py                  Candle model, CSV loader, ATR, swing pivots
    trendlines.py            valid "A+" trendline detection (rulebook §2)
    strategy.py              Bounce + Break signal engine (rulebook §3-6)
    backtest.py              event-driven walk-forward backtester
    broker.py                PaperBroker + FileBridgeBroker (MT4) + position sizing
    live.py                  live poll loop
mt4/
  TrendLineTradingBridge.mq4 Expert Advisor: exports rates, executes commands on HugosWay
```

## Quick start

```bash
cd bot
python3 run.py backtest --data sample_data/XPTUSD_H4.csv -v   # see stats + every trade
python3 run.py scan     --data sample_data/XPTUSD_H4.csv      # signal on the latest bar
python3 run.py gensample --out sample_data/XPTUSD_H4.csv      # regenerate demo data
```

## What it trades

Two setups, both on valid trendlines (>=3 taps, >=6 candles apart, >=3 weeks, shallow slope):

- **Bounce** — price tags the line and rejects it with a confirmation candle. Stop just past
  the line; the same line is the invalidation.
- **Break** — a candle *closes* through the line. Stop on the opposing "safety" structure.

Every trade needs a real support/resistance target giving **>= 2R** or it is skipped. Position
size risks a fixed `risk_per_trade` (default 1%) of the account.

## Going live with HugosWay / PRO4 (MT4)

The bot never talks to the broker directly — it exchanges files with an EA running inside the
terminal, so nothing extra needs to be installed in MT4.

```
MT4 EA  --writes-->  <bridge>/XPTUSD_240_rates.csv   --read by--> bot (live loop)
bot     --writes-->  <bridge>/commands.jsonl         --read by--> MT4 EA (places orders)
MT4 EA  --writes-->  <bridge>/acks.jsonl             (fill / error status)
```

1. **Install the EA.** Copy `mt4/TrendLineTradingBridge.mq4` into the terminal's
   `MQL4/Experts/` folder, compile it in MetaEditor, and attach it to **one** chart of your
   symbol at your chosen H1+ timeframe. Enable *AutoTrading* and *Allow live trading*.
2. **Find the bridge folder.** In MT4: *File → Open Data Folder → `MQL4/Files/trendline_bridge`*
   (the EA creates it). This is the `<bridge>` directory.
3. **Match the config to the broker.** In `config.json` set `symbol` to the *exact* HugosWay
   symbol, `timeframe_minutes` to the chart TF, and — importantly — `contract_size` to the
   broker's contract size for platinum so position sizing is correct (see the warning below).
4. **Run the bot against that folder:**
   ```bash
   python3 run.py --config config.json live --bridge "/path/to/MQL4/Files/trendline_bridge" --broker mt4
   ```
   Use `--broker paper` first to watch signals without sending orders.

The command protocol is one JSON object per line in `commands.jsonl`; the EA acks each `id`
in `acks.jsonl` and never re-runs an id, so restarts on either side are safe.

## ⚠️ Before risking real money

- **Set `contract_size` correctly.** The default of `1.0` is only right for the demo. If your
  broker's 1.0 lot of platinum is 100 oz, sizing is off by 100×. Verify lots on a cent/demo
  account first.
- **This is a starting point, not a proven edge.** Backtest results on the synthetic sample are
  illustrative only. Forward-test on demo, then trade minimum size.
- The `max_norm_slope` "45°" filter is an ATR-normalised approximation of the visual rule; tune
  it per instrument.
- Not financial advice.
