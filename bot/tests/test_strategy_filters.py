"""Trend-filter + large-line gate tests. Run from bot/ with `python -m unittest discover tests`."""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trendline_bot.config import Config
from trendline_bot.data import Candle
from trendline_bot.strategy import _line_is_large, trend_direction
from trendline_bot.trendlines import Trendline


def _daily_candles(closes):
    t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [Candle(t0 + timedelta(days=i), c, c + 1, c - 1, c) for i, c in enumerate(closes)]


class TestTrendDirection(unittest.TestCase):
    def setUp(self):
        # Daily bars so bars_per_day == 1 and the maths is easy to eyeball.
        self.cfg = Config(timeframe_minutes=1440, trend_filter_days=5)

    def test_uptrend(self):
        candles = _daily_candles(range(100, 120))
        self.assertEqual(trend_direction(candles, len(candles) - 1, self.cfg), 1)

    def test_downtrend(self):
        candles = _daily_candles(range(120, 100, -1))
        self.assertEqual(trend_direction(candles, len(candles) - 1, self.cfg), -1)

    def test_warmup_has_no_opinion(self):
        candles = _daily_candles(range(100, 103))   # only 3 bars < 5-day period
        self.assertEqual(trend_direction(candles, len(candles) - 1, self.cfg), 0)

    def test_disabled(self):
        self.cfg.trend_filter_days = 0
        candles = _daily_candles(range(100, 120))
        self.assertEqual(trend_direction(candles, len(candles) - 1, self.cfg), 0)


class TestLineIsLarge(unittest.TestCase):
    def setUp(self):
        self.candles = _daily_candles([100] * 40)
        # taps at day 0, 10, 30 -> 3 taps spanning 30 days
        self.line = Trendline("support", 0.0, 99.0, [0, 10, 30], 1.0)

    def test_default_accepts_any_valid_line(self):
        self.assertTrue(_line_is_large(self.candles, self.line, Config()))

    def test_span_gate(self):
        self.assertTrue(_line_is_large(self.candles, self.line, Config(break_min_span_days=30)))
        self.assertFalse(_line_is_large(self.candles, self.line, Config(break_min_span_days=31)))

    def test_taps_gate(self):
        self.assertTrue(_line_is_large(self.candles, self.line, Config(break_min_taps=3)))
        self.assertFalse(_line_is_large(self.candles, self.line, Config(break_min_taps=4)))


if __name__ == "__main__":
    unittest.main()
