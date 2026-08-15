"""
Unit tests for ChandelierExit and TrailingStopManager.
"""

import unittest
from greedbot.exits import ChandelierExit, TrailingStopManager


class TestExits(unittest.TestCase):

    def test_trailing_stop_manager_long_ratchet(self):
        manager = TrailingStopManager(
            ticker="NVDA",
            entry_price=100.0,
            initial_stop=90.0,  # 1R = $10.00
            direction="long",
        )
        self.assertEqual(manager.risk_1r, 10.0)

        # Price reaches +1.0R ($110.00) -> Stop moves to Breakeven ($100.00)
        status_1r = manager.update(110.0)
        self.assertAlmostEqual(status_1r.stop_price, 100.0)
        self.assertFalse(status_1r.is_triggered)

        # Price reaches +2.0R ($120.00) -> Stop moves to +1.0R ($110.00)
        status_2r = manager.update(120.0)
        self.assertAlmostEqual(status_2r.stop_price, 110.0)
        self.assertFalse(status_2r.is_triggered)

        # Price drops to $108.00 (below $110.00 stop) -> Triggered!
        status_drop = manager.update(108.0)
        self.assertTrue(status_drop.is_triggered)
        self.assertEqual(status_drop.trigger_reason, "TRAILING_STOP_TRIGGERED")

    def test_trailing_stop_manager_short_ratchet(self):
        manager = TrailingStopManager(
            ticker="TSLA",
            entry_price=200.0,
            initial_stop=220.0,  # 1R = $20.00
            direction="short",
        )
        # Price drops to +1R gain ($180.00) -> Stop ratchets down to $200.00
        status_1r = manager.update(180.0)
        self.assertAlmostEqual(status_1r.stop_price, 200.0)

    def test_chandelier_exit_long_ratchet(self):
        chandelier = ChandelierExit(atr_period=3, multiplier_k=2.0)
        highs = [105.0, 110.0, 115.0]
        lows = [95.0, 100.0, 105.0]
        closes = [100.0, 108.0, 112.0]

        stop_val = chandelier.update_long_stop(
            current_stop=80.0,
            highs=highs,
            lows=lows,
            closes=closes,
        )
        # Highest high is 115.0, stop must be higher than initial 80.0
        self.assertTrue(stop_val > 80.0)


if __name__ == "__main__":
    unittest.main()
