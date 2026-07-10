"""Cost-model tests: run from bot/ with `python -m unittest discover tests`."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trendline_bot.backtest import round_turn_cost, run_backtest
from trendline_bot.config import Config
from trendline_bot.data import load_csv

SAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "sample_data", "XPTUSD_H4.csv")


class TestRoundTurnCost(unittest.TestCase):
    def test_defaults_are_free(self):
        self.assertEqual(round_turn_cost(Config()), 0.0)

    def test_components_add_up(self):
        cfg = Config(spread=0.5, slippage=0.1, commission_per_lot=7.0, contract_size=10.0)
        # spread once + slippage both sides + commission per unit (7 / 10)
        self.assertAlmostEqual(round_turn_cost(cfg), 0.5 + 0.2 + 0.7)

    def test_zero_contract_size_skips_commission(self):
        cfg = Config(spread=0.5, commission_per_lot=7.0, contract_size=0.0)
        self.assertAlmostEqual(round_turn_cost(cfg), 0.5)


class TestBacktestCosts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candles = load_csv(SAMPLE)

    def test_zero_cost_matches_ideal_fills(self):
        result = run_backtest(self.candles, Config())
        self.assertGreater(result.n, 0, "sample data should produce trades")
        self.assertEqual(result.total_cost_r, 0.0)
        for t in result.trades:
            if t.outcome == "stop":
                self.assertEqual(t.r, -1.0)
            elif t.outcome == "target":
                self.assertAlmostEqual(t.r, t.signal.rr, places=3)

    def test_costs_deducted_per_trade(self):
        ideal = run_backtest(self.candles, Config())
        costed = run_backtest(self.candles, Config(spread=1.0, slippage=0.25))

        # Costs don't change which trades happen, only what they net.
        self.assertEqual([t.outcome for t in costed.trades], [t.outcome for t in ideal.trades])

        cost_price = 1.0 + 2 * 0.25
        for t in costed.trades:
            expected = round(cost_price / t.signal.risk, 3)
            self.assertAlmostEqual(t.cost_r, expected, places=3)
            self.assertGreater(t.cost_r, 0.0)

        gross = sum(t.r + t.cost_r for t in costed.trades)
        self.assertAlmostEqual(gross, ideal.total_r, places=2)
        self.assertLess(costed.total_r, ideal.total_r)


if __name__ == "__main__":
    unittest.main()
