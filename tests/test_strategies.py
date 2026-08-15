"""
Unit tests for GreedBot Investment Strategies.
"""

import unittest
from unittest.mock import MagicMock
from greedbot.client import GreedBotClient
from greedbot.models import Side
from greedbot.strategies import (
    BotFleetFollower,
    EarningsRadarStrategy,
    ETFBarbellStrategy,
    MacroRegimeMatrix,
    OptionKellyEngine,
    QualitativeOverlayEngine,
    SectorLongShortStrategy,
    SoloTacticalStrategy,
)


class TestStrategies(unittest.TestCase):

    def setUp(self):
        self.mock_client = MagicMock(spec=GreedBotClient)

    def test_etf_barbell_strategy(self):
        self.mock_client.get_parity.return_value = {
            "df": {"ticker": ["schp", "vglt", "vt", "pdbc", "iau"], "parity": [0.2, 0.2, 0.2, 0.2, 0.2]}
        }
        self.mock_client.get_kelly.return_value = {
            "df": {"ticker": ["schp", "vglt", "vt", "pdbc", "iau"], "kelly": [0.3, 0.1, 0.4, 0.1, 0.1]}
        }
        self.mock_client.get_rebalance.return_value = {
            "trades": [{"ticker": "vt", "shares": 10}],
            "summary": {"gross_target": 10000.0},
        }

        strat = ETFBarbellStrategy()
        res = strat.run(self.mock_client, capital_usd=10000.0)
        self.assertEqual(len(res.target_dollars), 5)
        self.assertTrue(len(res.intents) > 0)
        self.assertEqual(res.intents[0].side, Side.BUY)

    def test_solo_tactical_strategy_in(self):
        self.mock_client.get_targets.return_value = {
            "df": {"ticker": ["nvda"], "algos": [0.45]}
        }
        self.mock_client.get_rebalance.return_value = {
            "trades": [{"ticker": "nvda", "shares": 50}],
            "summary": {},
        }

        strat = SoloTacticalStrategy(ticker="NVDA", min_signal=0.05)
        res = strat.run(self.mock_client, capital_usd=10000.0)
        self.assertEqual(res.target_dollars["nvda"], 10000.0)
        self.assertEqual(len(res.intents), 1)
        self.assertEqual(res.intents[0].side, Side.BUY)

    def test_solo_tactical_strategy_flat(self):
        self.mock_client.get_targets.return_value = {
            "df": {"ticker": ["nvda"], "algos": [0.01]}  # below min_signal
        }
        self.mock_client.get_rebalance.return_value = {"trades": [], "summary": {}}

        strat = SoloTacticalStrategy(ticker="NVDA", min_signal=0.05)
        res = strat.run(self.mock_client, capital_usd=10000.0)
        self.assertEqual(res.target_dollars["nvda"], 0.0)
        self.assertEqual(len(res.intents), 0)

    def test_sector_long_short_strategy(self):
        self.mock_client.get_pizza.return_value = {
            "pizza": {
                "df": {
                    "ticker": ["xle", "xlf", "xlk", "xlv"],
                    "pizza_slice": [0.1, 0.3, 0.8, 0.9],
                }
            }
        }
        self.mock_client.get_rebalance.side_effect = [
            {"trades": [{"ticker": "xlv", "shares": 5}, {"ticker": "xlk", "shares": 5}], "summary": {}},  # long leg
            {"trades": [{"ticker": "xle", "shares": 10}, {"ticker": "xlf", "shares": 10}], "summary": {}},  # short leg
        ]

        strat = SectorLongShortStrategy(
            sector_universe=["xle", "xlf", "xlk", "xlv"],
            gross_fraction=0.20,
            per_name_cap=0.05,
            n_long=2,
            n_short=2,
        )
        res = strat.run(self.mock_client, capital_usd=10000.0)
        self.assertIn("xlv", res.target_dollars)
        self.assertIn("xlk", res.target_dollars)
        self.assertIn("xle", res.target_dollars)
        self.assertIn("xlf", res.target_dollars)

        # Check that short legs are typed as SHORT_SELL
        short_intents = [i for i in res.intents if i.side == Side.SHORT_SELL]
        self.assertEqual(len(short_intents), 2)
        short_tickers = {i.ticker for i in short_intents}
        self.assertEqual(short_tickers, {"xle", "xlf"})

        long_intents = [i for i in res.intents if i.side == Side.BUY]
        self.assertEqual(len(long_intents), 2)
        long_tickers = {i.ticker for i in long_intents}
        self.assertEqual(long_tickers, {"xlv", "xlk"})

    def test_option_kelly_engine(self):
        self.mock_client.get_kelly.return_value = {
            "df": {"ticker": ["nvda"], "kelly": [0.80]}
        }
        self.mock_client.get_hub_earnings_expected_move.return_value = {
            "ticker": "NVDA", "expected_move_pct": 7.5
        }

        strat = OptionKellyEngine(default_ticker="nvda")
        sizing = strat.calculate_sizing(self.mock_client, "nvda", portfolio_size=10000.0)
        self.assertEqual(sizing["direction"], "CALL")
        self.assertAlmostEqual(sizing["expected_move_pct"], 7.5)
        self.assertTrue(sizing["max_risk_budget"] > 0)

    def test_macro_regime_matrix(self):
        self.mock_client.get_hub_macro.return_value = {
            "regime": "BULL_MOMENTUM", "opinion": "Strong Expansion"
        }
        strat = MacroRegimeMatrix()
        alloc = strat.get_regime_allocations(self.mock_client, capital_usd=50000.0)
        self.assertEqual(alloc["active_regime"], "BULL_MOMENTUM")
        self.assertIn("QQQ", alloc["allocations"])

    def test_qualitative_overlay_engine(self):
        self.mock_client.get_hub_earnings_expected_move.return_value = {
            "expected_move_pct": 5.0
        }
        strat = QualitativeOverlayEngine()
        res = strat.evaluate_divergence(
            client_or_ticker=self.mock_client,
            ticker="NVDA",
            qualitative_sentiment=0.90,
            conviction=0.90,
        )
        self.assertEqual(res["assessment"], "ASYMMETRIC_UNDERPRICED_VOLATILITY")
        self.assertTrue(res["asymmetry_delta_pct"] > 2.0)

    def test_bot_follower(self):
        self.mock_client.get_bots.return_value = {
            "bots": [
                {"id": "bot_alpha", "expectancy_r": 0.45, "e_value": 10.5, "retired": False},
                {"id": "bot_beta", "expectancy_r": 0.10, "e_value": 2.1, "retired": False},
            ]
        }
        self.mock_client.get_bot_book.return_value = {
            "open_positions": [
                {"ticker": "NVDA", "direction": "long"},
                {"ticker": "AAPL", "direction": "long"},
            ]
        }

        follower = BotFleetFollower()
        res = follower.run(self.mock_client, capital_usd=10000.0)
        self.assertEqual(len(res.intents), 2)
        self.assertIn("nvda", res.target_dollars)
        self.assertIn("aapl", res.target_dollars)


if __name__ == "__main__":
    unittest.main()
