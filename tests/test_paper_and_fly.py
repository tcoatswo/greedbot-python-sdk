"""
Unit tests for InstitutionalPaperBroker and DrosophilaConnectomeTrader in GreedBot SDK.
"""

import os
import tempfile
import unittest
import numpy as np

from greedbot.paper_engine import InstitutionalPaperBroker, PaperPosition
from greedbot.fly_trader import DrosophilaConnectomeTrader, ConnectomeSensoryInput, FlyMotorDecision
from greedbot.models import Side, OrderIntent


class TestPaperAndFlyTrader(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.broker = InstitutionalPaperBroker(
            starting_cash=100000.0,
            db_path=self.temp_db.name,
            slippage_coeff=0.05,
            half_spread_bps=2.0,
        )

    def tearDown(self):
        try:
            os.remove(self.temp_db.name)
        except OSError:
            pass

    # -------------------------------------------------------------
    # 1. Institutional Paper Broker Tests
    # -------------------------------------------------------------
    def test_broker_initialization_and_cash(self):
        self.assertEqual(self.broker.cash, 100000.0)
        self.assertEqual(len(self.broker.positions), 0)
        self.assertEqual(self.broker.total_portfolio_value, 100000.0)

    def test_realistic_slippage_and_buy_order(self):
        fill = self.broker.execute_order(
            ticker="SPY",
            side=Side.BUY,
            quantity=10.0,
            mid_price=580.0,
        )
        self.assertGreater(fill.price, 580.0)  # Spread + Slippage penalty applied
        self.assertGreater(fill.fees, 0.0)
        self.assertEqual(self.broker.positions["spy"], 10.0)
        self.assertLess(self.broker.cash, 100000.0 - 5800.0)

    def test_sell_order_and_realized_pnl(self):
        self.broker.execute_order(ticker="NVDA", side=Side.BUY, quantity=20.0, mid_price=100.0)
        
        # Price increases
        self.broker.update_market_price("NVDA", 120.0)
        fill = self.broker.execute_order(ticker="NVDA", side=Side.SELL, quantity=20.0, mid_price=120.0)
        
        self.assertGreater(fill.price, 100.0)
        self.assertGreater(self.broker.realized_pnl, 0.0)
        self.assertEqual(len(self.broker.positions), 0)

    def test_sqlite_snapshot_logging(self):
        snapshot = self.broker.record_snapshot()
        self.assertIn("portfolio_value", snapshot)
        self.assertIn("timestamp", snapshot)
        self.assertEqual(snapshot["portfolio_value"], 100000.0)

    # -------------------------------------------------------------
    # 2. Drosophila Fly Trader Tests
    # -------------------------------------------------------------
    def test_fly_trader_initialization(self):
        fly = DrosophilaConnectomeTrader(broker=self.broker)
        self.assertEqual(fly.W_sensory_to_kc.shape, (4, 2000))
        self.assertEqual(fly.W_kc_to_mbon.shape, (2000, 24))
        self.assertEqual(fly.W_mbon_to_motor.shape, (24, 4))

    def test_fly_sensory_motor_decision(self):
        fly = DrosophilaConnectomeTrader(broker=self.broker)
        sensor = ConnectomeSensoryInput(
            ticker="BTC",
            price=78000.0,
            price_velocity_5m=1.85,    # Strong upward momentum
            bid_ask_delta=0.65,        # Heavy buying pressure
            net_gex_regime=-1.0,       # Short gamma volatility
            iv_skew=0.35,              # High IV skew
        )
        decision = fly.process_tick(sensor)
        self.assertIsInstance(decision, FlyMotorDecision)
        self.assertIn(decision.action, ["BUY", "SELL", "HOLD", "SPREAD"])
        self.assertTrue(0.0 <= decision.confidence <= 1.0)
        self.assertGreater(decision.target_dollars, 0.0)

    def test_dopamine_synaptic_plasticity(self):
        fly = DrosophilaConnectomeTrader(broker=self.broker)
        init_pam = fly.pam_dopamine_reward
        
        # Positive PnL reward
        fly.learn_from_pnl(realized_pnl=500.0)
        self.assertGreater(fly.pam_dopamine_reward, init_pam)
        
        # Negative PnL punishment
        fly.learn_from_pnl(realized_pnl=-300.0)
        self.assertGreater(fly.ppl1_dopamine_punish, 0.0)


if __name__ == "__main__":
    unittest.main()
