"""TrendLine Trading bot — a dependency-light, price-action swing engine.

Implements the Tori-Trades-style trendline method (see docs/PLATINUM_TRENDLINE_RULES.md)
for hourly-and-above timeframes. Pure standard library, so it runs anywhere Python 3.9+
is installed. A broker seam (trendline_bot.broker) lets the same signals drive a paper
account today and a live HugosWay / PRO4-MT4 account via the file bridge + MQL4 EA.
"""

from .config import Config
from .data import Candle, load_csv
from .strategy import Signal, generate_signal

__all__ = ["Config", "Candle", "load_csv", "Signal", "generate_signal"]
