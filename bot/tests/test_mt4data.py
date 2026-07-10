"""HST reader + broker-spec override tests. Run from bot/ with `python -m unittest discover tests`."""

import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trendline_bot.config import Config
from trendline_bot.live import apply_broker_spec
from trendline_bot.mt4data import read_hst


def _make_hst_401(path, symbol="XPTUSD", period=240, digits=2, bars=()):
    """bars: iterable of (epoch, o, h, l, c, vol, spread_points)."""
    hdr = struct.pack("<i", 401)
    hdr += b"test".ljust(64, b"\x00")
    hdr += symbol.encode().ljust(12, b"\x00")
    hdr += struct.pack("<ii", period, digits)
    hdr += b"\x00" * (148 - len(hdr))
    rec = struct.Struct("<q4dqiq")
    with open(path, "wb") as fh:
        fh.write(hdr)
        for t, o, h, l, c, vol, spread in bars:
            fh.write(rec.pack(t, o, h, l, c, vol, spread, 0))


class TestReadHst(unittest.TestCase):
    def test_v401_roundtrip(self):
        bars = [
            (1729800000, 1000.0, 1010.0, 995.0, 1005.0, 120, 45),
            (1729814400, 1005.0, 1015.0, 1002.0, 1012.0, 90, 55),
        ]
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "XPTUSD240.hst")
            _make_hst_401(path, bars=bars)
            hst = read_hst(path)

        self.assertEqual(hst.version, 401)
        self.assertEqual(hst.symbol, "XPTUSD")
        self.assertEqual(hst.period, 240)
        self.assertEqual(hst.digits, 2)
        self.assertEqual(len(hst.candles), 2)
        c = hst.candles[0]
        self.assertEqual((c.open, c.high, c.low, c.close, c.volume), (1000.0, 1010.0, 995.0, 1005.0, 120.0))

        stats = hst.spread_stats()
        self.assertEqual(stats["bars"], 2)
        self.assertAlmostEqual(stats["median_price"], 0.55)   # 55 points at 2 digits
        self.assertAlmostEqual(stats["mean_price"], 0.50)

    def test_zero_spreads_mean_no_stats(self):
        bars = [(1729800000, 1.0, 2.0, 0.5, 1.5, 10, 0)]
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "X1.hst")
            _make_hst_401(path, symbol="X", period=1, bars=bars)
            self.assertIsNone(read_hst(path).spread_stats())


class TestBrokerSpec(unittest.TestCase):
    def test_spec_overrides_sizing_fields(self):
        cfg = Config()  # contract_size defaults to the demo-only 1.0
        spec = {"symbol": "XPTUSD", "contract_size": 100.0, "min_lot": 0.01, "lot_step": 0.01,
                "max_lot": 50.0, "spread": 0.85, "account_balance": 2500.0,
                "account_currency": "USD", "digits": 2}
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "XPTUSD_spec.json"), "w", encoding="utf-8") as fh:
                json.dump(spec, fh)
            loaded = apply_broker_spec(cfg, td)

        self.assertIsNotNone(loaded)
        self.assertEqual(cfg.contract_size, 100.0)   # broker truth beat the 1.0 footgun
        self.assertEqual(cfg.max_lot, 50.0)
        self.assertEqual(cfg.spread, 0.85)
        self.assertEqual(cfg.account_balance, 2500.0)

    def test_missing_spec_leaves_config_alone(self):
        cfg = Config()
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(apply_broker_spec(cfg, td))
        self.assertEqual(cfg.contract_size, 1.0)


if __name__ == "__main__":
    unittest.main()
