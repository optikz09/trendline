"""Hand-drawn line crossing tests. Run from bot/ with `python -m unittest discover tests`."""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trendline_bot.config import Config
from trendline_bot.data import Candle
from trendline_bot.manual_lines import ManualLine, cross_signal, load_lines

T0 = datetime(2026, 7, 1, tzinfo=timezone.utc)


def _candles(closes):
    out = []
    for i, c in enumerate(closes):
        t = T0 + timedelta(hours=4 * i)
        out.append(Candle(t, c, c + 2, c - 2, c))
    return out


def _flat_line(price, name="tl1"):
    return ManualLine(name, T0, price, T0 + timedelta(days=2), price)


class TestCrossSignal(unittest.TestCase):
    def setUp(self):
        self.cfg = Config(min_rr=2.0)

    def test_cross_up_is_long(self):
        candles = _candles([95, 96, 97, 96, 103])   # last close jumps above the 100 line
        sig = cross_signal(candles, len(candles) - 1, [_flat_line(100.0)], self.cfg)
        self.assertIsNotNone(sig)
        self.assertEqual((sig.side, sig.setup), ("long", "manual-break"))
        self.assertEqual(sig.entry, 103)
        self.assertLess(sig.stop, sig.entry)
        self.assertAlmostEqual(sig.target, sig.entry + 2.0 * sig.risk)
        self.assertIn("tl1", sig.reason)

    def test_cross_down_is_short(self):
        candles = _candles([105, 104, 103, 104, 97])
        sig = cross_signal(candles, len(candles) - 1, [_flat_line(100.0)], self.cfg)
        self.assertIsNotNone(sig)
        self.assertEqual(sig.side, "short")
        self.assertAlmostEqual(sig.target, sig.entry - 2.0 * sig.risk)

    def test_no_cross_no_signal(self):
        candles = _candles([95, 96, 97, 96, 98])    # stays below the line
        self.assertIsNone(cross_signal(candles, len(candles) - 1, [_flat_line(100.0)], self.cfg))

    def test_same_side_no_retrigger(self):
        # Already above the line on both bars -> not a cross.
        candles = _candles([103, 104, 105, 106, 107])
        self.assertIsNone(cross_signal(candles, len(candles) - 1, [_flat_line(100.0)], self.cfg))

    def test_sloped_line_uses_time_interpolation(self):
        # Line rises 1.0 per 4h bar: value at bar i is 100 + i.
        line = ManualLine("slope", T0, 100.0, T0 + timedelta(hours=4), 101.0)
        candles = _candles([99, 100, 101, 102, 110])  # closes track below-ish then jump over
        sig = cross_signal(candles, len(candles) - 1, [line], self.cfg)
        self.assertIsNotNone(sig)
        self.assertEqual(sig.side, "long")

    def test_degenerate_line_ignored(self):
        line = ManualLine("dot", T0, 100.0, T0, 100.0)   # zero time span
        candles = _candles([95, 96, 97, 96, 103])
        self.assertIsNone(cross_signal(candles, len(candles) - 1, [line], self.cfg))


class TestLoadLines(unittest.TestCase):
    def test_reads_ea_export_format(self):
        content = ("name,time1,price1,time2,price2\n"
                   "big support,2026.06.01 00:00,1250.00,2026.07.01 00:00,1300.00\n"
                   "malformed,not-a-time,x,y,z\n")
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "XPTUSD_lines.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            lines = load_lines(path)
        self.assertEqual(len(lines), 1)                  # malformed row skipped, not fatal
        self.assertEqual(lines[0].name, "big support")
        self.assertAlmostEqual(lines[0].p2, 1300.0)

    def test_missing_file_is_empty(self):
        self.assertEqual(load_lines(os.path.join("nope", "missing.csv")), [])


if __name__ == "__main__":
    unittest.main()
