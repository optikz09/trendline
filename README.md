# TrendLine Trading

A price-action swing-trading system for **Platinum (XPTUSD)** on **hourly-and-up** timeframes,
built to run **live** against a HugosWay **PRO4 / MT4** leveraged account.

- **Strategy rulebook:** [`docs/PLATINUM_TRENDLINE_RULES.md`](docs/PLATINUM_TRENDLINE_RULES.md)
  — a Tori-Trades-style trendline method (bounce + break setups, ≥2R, fixed-% risk), adapted to Platinum.
- **The bot:** [`bot/`](bot/) — a dependency-light (pure Python 3.9+ stdlib) engine that detects
  setups, backtests them, and trades live. See [`bot/README.md`](bot/README.md).
- **MT4 bridge:** [`mt4/TrendLineTradingBridge.mq4`](mt4/TrendLineTradingBridge.mq4) — an Expert
  Advisor that exports rates and executes the bot's orders inside PRO4/MT4.
- **Continuity notes:** [`bot/HANDOFF.md`](bot/HANDOFF.md) — design decisions, architecture,
  limitations, and the backlog.

## Quick start

```bash
cd bot
python3 run.py backtest --data sample_data/XPTUSD_H4.csv -v   # walk-forward stats
python3 run.py scan     --data sample_data/XPTUSD_H4.csv      # signal on the latest bar
```

## ⚠️ Before risking real money

Set `contract_size` in your config to the broker's real platinum contract size (the `1.0` default is
demo-only), add a spread/commission cost model, and forward-test on a demo/cent account first. The
included sample data is synthetic — it validates mechanics, not profitability. Not financial advice.

## Layout

```
bot/                       Python engine (strategy, backtest, live loop, brokers, CLI)
mt4/                       MetaTrader 4 Expert Advisor (live bridge)
docs/                      Strategy rulebook
```
