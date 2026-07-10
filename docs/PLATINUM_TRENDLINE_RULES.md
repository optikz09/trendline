# Platinum Trendline Trading Rules

A mechanical, price-action-only swing-trading rulebook for **Platinum (XPTUSD / PL futures)**,
adapted from the trendline method taught by **Tori Trades** ([youtube.com/@tori.trades](https://www.youtube.com/@tori.trades),
[toritradez.com](https://toritradez.com/)).

> **Educational only — not financial advice.** Platinum is a thin, volatile market. Backtest and
> forward-test on a demo account before risking real capital. Rules are synthesized from Tori Trades'
> publicly documented method and adapted to Platinum's characteristics.

---

## 0. Core philosophy

- **No indicators.** Only price action and hand-drawn trendlines.
- **Swing trading**, not scalping. Trades play out over days to weeks.
- **Two setups only:** the **Bounce** and the **Break**. Nothing else is traded.
- Every trade is governed by two lines:
  - **Action Line** — tells you *where to enter*.
  - **Safety Line** — tells you *where to exit if you're wrong*.

---

## 1. Timeframes (top-down)

| Timeframe | Purpose |
|-----------|---------|
| **Weekly / Daily** | Establish the dominant trend direction and mark major horizontal support/resistance. Trade *with* the higher-timeframe bias where possible. |
| **4-Hour (primary)** | Draw trendlines, count taps, find setups, place entries, stops, and targets. **All execution happens here.** |

The 4H chart catches clean swing moves and filters out the noise of lower timeframes. Do **not** drop below 4H for entries.

---

## 2. What makes a valid ("A+") trendline

Zoom the 4H chart out to show **~3 months** of price action, then require **all** of the following:

1. **≥ 3 taps** — the line must be touched/respected at least three times.
2. **≥ 6 candles between taps** — touches spaced closely together don't count; taps must be at least six 4H candles apart.
3. **≥ 3 weeks of duration** — the line must span at least three weeks of price.
4. **Slope < 45°** — with 3 months on screen, the line should be shallow. A steep (>45°) line is fragile and is rejected.

If a line fails **any** of these four, it is **not** tradeable. Do not force it.

---

## 3. Setup A — The Bounce (lowest risk)

**Idea:** Price returns to a valid trendline and respects it, continuing in the trend direction.

- **Action Line = Safety Line** (the same trendline does both jobs).
- **Entry:** Price taps the valid trendline and shows a **confirmation candle** (bullish/bearish engulfing or doji rejection) closing back in the trend direction. Enter on/after that confirmation close.
- **Stop / invalidation:** If a 4H candle **closes through** the trendline, the setup is dead — exit immediately.
- **Why lowest risk:** Invalidation is instant and the stop sits right at the line, so the stop distance is small.

**Bounce checklist**
- [ ] Higher-timeframe trend agrees with the bounce direction
- [ ] Trendline meets all four A+ rules
- [ ] Price tapped the line (didn't just approach it)
- [ ] Confirmation candle closed in the trend direction
- [ ] Nearest opposing S/R gives **≥ 2R** before it's hit

---

## 4. Setup B — The Break (trend reversal)

**Idea:** A valid trendline finally gives way, signalling a change of trend.

- **Action Line:** the trendline being broken. **Entry trigger = a full 4H candle CLOSE past the line** (not a wick poke).
- **Safety Line:** draw a **new opposing trendline** to protect the trade. This becomes your stop reference.
- **Stop placement (mechanical):** place the stop where the **4th candle after the break** would intersect the opposing safety line. This standardizes stop distance instead of eyeballing it.
- **Optional higher-probability entry — Break & Retest:** after the break, wait for price to pull **back to the broken line** and reject it (retest holds as new support/resistance), then enter. Tighter stop, better R, fewer false breaks.

**Break checklist**
- [ ] Broken line was itself a valid A+ trendline
- [ ] A **4H candle closed** fully beyond the line (confirmed break, not a wick)
- [ ] Opposing safety line drawn for stop reference
- [ ] (Preferred) price retested the broken line and rejected it
- [ ] Target S/R gives **≥ 2R**

---

## 5. Stop loss — rules of thumb

- **Bounce:** stop just beyond the trendline; exit on a 4H close through it.
- **Break:** stop on the opposing **safety line**, mechanically at the **4th-candle-after-break** intersection.
- Never widen a stop once placed. If price says you're wrong, you're wrong.

---

## 6. Take profit & risk-reward

- **Minimum 2R.** Do not take a setup whose nearest logical target is under 2R.
- **Target = the first horizontal support/resistance level** (a price zone where the market previously reacted) that offers **2R or more**.
- Mark these S/R zones on the Daily/Weekly *before* entering so the target is pre-defined.
- **Partial-scaling (optional):** take partial profit at 2R, move stop to breakeven, and trail the remainder along a fresh trendline / safety line as the swing extends.

---

## 7. Risk management (non-negotiable)

- **Risk a fixed small % of the account per trade** (commonly **0.5%–1%**). Never size by "feel."
- Position size is derived from stop distance:
  `size = (account × risk%) ⁄ (entry-to-stop distance)`.
- One clean setup at a time; avoid stacking correlated metal positions (Platinum + Gold + Silver) — they move together and multiply real risk.
- Predefine max daily/weekly loss and stop trading when hit.

---

## 8. Platinum-specific adjustments

Platinum is **not** gold — respect its quirks:

- **Higher, spikier volatility.** Platinum is more volatile than gold, with a smaller, thinner market and sharp moves driven by *both* precious-metal sentiment **and** industrial demand (autos, mining supply shocks). Give stops a little more room than you would on gold, and let position size (not a tight stop) absorb the volatility.
- **Trade the liquid window.** Best liquidity and cleanest structure come during the **London–New York overlap (~8am–12pm ET / ~2–6pm CET)**. Breaks that occur inside this window are more trustworthy than thin-hours breaks.
- **Beware thin-session fakeouts.** Asian-session and rollover moves can spike through trendlines on low volume. Prefer break confirmations whose 4H candle **closes during liquid hours**.
- **Watch the fundamentals.** Auto-sector demand news, mine-supply disruptions (South Africa/Russia concentration), and broad USD/precious-metal moves can override chart structure. Avoid fresh entries right before major macro/USD events.
- **Wider "clean trend" phases suit this method.** When Platinum trends, candles are big and breakouts are clean — ideal for the Break setup. In choppy ranges, stand aside.

---

## 9. The one-page trade filter

Before **any** Platinum entry, all of these must be true:

1. ✅ Higher-timeframe (D/W) trend context is clear
2. ✅ The trendline passes all **four** A+ rules (3 taps · 6+ candles apart · 3+ weeks · <45°)
3. ✅ It's a clean **Bounce** (confirmation candle) or **Break** (4H close through, ideally retested)
4. ✅ Action Line and Safety Line are both defined
5. ✅ Stop is placed mechanically and won't be moved wider
6. ✅ Nearest logical S/R target gives **≥ 2R**
7. ✅ Risk is a fixed small % of the account
8. ✅ Entry lands in Platinum's liquid session, with no major news imminent

If even one is missing — **no trade.**

---

## Sources

- [Tori Trades — YouTube (@tori.trades)](https://www.youtube.com/@tori.trades)
- [Tori Tradez — official site](https://toritradez.com/)
- [How to Trade Breaks, Retests & Bounces w/ Structure — toritradez.com blog](https://toritradez.com/blog/all/low-risk-trend-line-trading-break-retest-bounce)
- [Tori Trades Trendlines Strategy — FX Replay](https://fxreplay.com/strategies/tori-trades-trendlines-strategy)
- [Tori's Trendline Trading Strategy — Tradezella](https://www.tradezella.com/strategies/trendline-strategy)
- [Tori's Trendline Trading Playbook — Chart Fanatics](https://www.chartfanatics.com/strategies/trendline-strategy)
- [Platinum Overview — CME Group](https://www.cmegroup.com/markets/metals/precious/platinum.html)
- [XPTUSD — TradingView](https://www.tradingview.com/symbols/XPTUSD/)
