"""
Unit tests for the 5 newly implemented modules in GreedBot SDK:
1. Market-Maker Gamma Exposure (GEX) & Max Pain
2. Multi-Leg Options Spread Engine & P&L Profiler
3. Turnkey Broker Connectors (Alpaca & Tradier)
4. Monte Carlo Portfolio Stress-Testing & CVaR
5. Interactive Dashboard launcher
"""

import unittest
from greedbot.quant.gex import GEXEngine, OptionContractData, GEXResult
from greedbot.quant.spreads import (
    IronCondor,
    VerticalSpread,
    Straddle,
    Strangle,
    OptionLeg,
    CompositeSpreadGreeks,
)
from greedbot.quant.monte_carlo import MonteCarloEngine, MonteCarloResult
from greedbot.adapters import AlpacaBrokerAdapter, TradierBrokerAdapter
from greedbot.models import OrderIntent, Side
from greedbot.dashboard import get_streamlit_app_code


class TestNewQuantAndExecutionFeatures(unittest.TestCase):
    # -------------------------------------------------------------
    # 1. GEX & Max Pain Tests
    # -------------------------------------------------------------
    def test_gex_calculation_and_walls(self):
        spot = 580.0
        contracts = [
            OptionContractData(strike=560.0, is_call=False, open_interest=10000, dte=30, iv=0.25),
            OptionContractData(strike=570.0, is_call=False, open_interest=8000, dte=30, iv=0.22),
            OptionContractData(strike=580.0, is_call=True, open_interest=15000, dte=30, iv=0.20),
            OptionContractData(strike=590.0, is_call=True, open_interest=20000, dte=30, iv=0.18),
            OptionContractData(strike=600.0, is_call=True, open_interest=25000, dte=30, iv=0.16),
        ]
        engine = GEXEngine(spot=spot)
        res = engine.calculate_gex(contracts)

        self.assertIsInstance(res, GEXResult)
        self.assertEqual(res.spot, 580.0)
        self.assertGreater(res.call_gex_dollars, 0)
        self.assertGreater(res.put_gex_dollars, 0)
        self.assertIsNotNone(res.call_wall)
        self.assertIsNotNone(res.put_wall)
        self.assertGreater(res.max_pain, 0.0)
        self.assertIn("Market Maker Gamma Exposure", res.summary())

    def test_max_pain_exact_strike(self):
        spot = 100.0
        contracts = [
            OptionContractData(strike=90.0, is_call=False, open_interest=100, dte=10),
            OptionContractData(strike=100.0, is_call=True, open_interest=500, dte=10),
            OptionContractData(strike=110.0, is_call=True, open_interest=1000, dte=10),
        ]
        engine = GEXEngine(spot=spot)
        max_pain = engine.calculate_max_pain(contracts)
        self.assertTrue(90.0 <= max_pain <= 110.0)

    # -------------------------------------------------------------
    # 2. Multi-Leg Spreads Tests
    # -------------------------------------------------------------
    def test_iron_condor_greeks_and_break_evens(self):
        spot = 580.0
        ic = IronCondor(
            spot=spot,
            put_wing=550.0,
            put_short=565.0,
            call_short=595.0,
            call_wing=610.0,
            dte=30.0,
            iv=0.20,
        )
        greeks = ic.get_net_greeks(spot)
        self.assertIsInstance(greeks, CompositeSpreadGreeks)
        # Iron condor near center should have delta near 0 and positive theta
        self.assertTrue(-0.15 < greeks.net_delta < 0.15)
        self.assertGreater(greeks.net_theta, 0.0)
        self.assertIsNotNone(greeks.max_profit)
        self.assertIsNotNone(greeks.max_loss)
        self.assertTrue(len(greeks.break_even_points) >= 2)

    def test_vertical_spread_payoff_curve(self):
        spot = 580.0
        vert = VerticalSpread(spot=spot, long_strike=575.0, short_strike=590.0, dte=30.0, is_call=True)
        greeks = vert.get_net_greeks(spot)
        self.assertGreater(greeks.net_delta, 0.0)  # Bull call has positive delta

        curve = vert.generate_payoff_curve(spot, price_range_pct=0.15, points=20)
        self.assertEqual(len(curve), 20)
        self.assertIn("spot", curve[0])
        self.assertIn("pnl", curve[0])

    def test_straddle_and_strangle(self):
        spot = 580.0
        straddle = Straddle(spot=spot, strike=580.0, dte=30.0, is_long=True)
        sgreeks = straddle.get_net_greeks(spot)
        self.assertGreater(sgreeks.net_gamma, 0.0)
        self.assertGreater(sgreeks.net_vega, 0.0)

        strangle = Strangle(spot=spot, put_strike=560.0, call_strike=600.0, dte=30.0, is_long=True)
        cgreeks = strangle.get_net_greeks(spot)
        self.assertGreater(cgreeks.net_vega, 0.0)

    # -------------------------------------------------------------
    # 3. Turnkey Broker Connectors Tests
    # -------------------------------------------------------------
    def test_alpaca_broker_adapter_mock_mode(self):
        adapter = AlpacaBrokerAdapter(api_key=None, secret_key=None, paper=True)
        acc = adapter.get_account()
        self.assertEqual(acc["status"], "MOCK_MODE")
        self.assertEqual(acc["cash"], 100000.0)
        self.assertEqual(adapter.cash, 100000.0)

        intents = [
            OrderIntent(ticker="SPY", dollars=5800.0, side=Side.BUY, limit=580.0),
            OrderIntent(ticker="QQQ", dollars=2450.0, side=Side.SELL, limit=490.0),
        ]
        fills = adapter.execute(intents)
        self.assertEqual(len(fills), 2)
        self.assertEqual(fills[0].ticker.upper(), "SPY")
        self.assertEqual(fills[0].quantity, 10.0)
        self.assertEqual(fills[1].ticker.upper(), "QQQ")

    def test_tradier_broker_adapter_mock_mode(self):
        adapter = TradierBrokerAdapter(access_token=None, account_id=None, sandbox=True)
        balances = adapter.get_balances()
        self.assertEqual(balances["status"], "MOCK_MODE")
        self.assertEqual(adapter.cash, 50000.0)

        opt_order = adapter.submit_option_order(
            symbol="SPY",
            option_symbol="SPY260918C00585000",
            side="buy_to_open",
            quantity=2,
        )
        self.assertEqual(opt_order["status"], "ok")

    # -------------------------------------------------------------
    # 4. Monte Carlo Risk & Stress-Testing Tests
    # -------------------------------------------------------------
    def test_monte_carlo_var_and_cvar(self):
        engine = MonteCarloEngine(
            portfolio_value=100000.0,
            expected_annual_return=0.10,
            annual_volatility=0.20,
            jump_intensity=1.0,
            jump_mean=-0.05,
            jump_vol=0.08,
            seed=42,
        )
        res = engine.run_simulation(days=30, num_simulations=1000)
        self.assertIsInstance(res, MonteCarloResult)
        self.assertEqual(res.initial_portfolio_value, 100000.0)
        self.assertEqual(res.time_horizon_days, 30)
        self.assertGreater(res.var_95_pct, 0.0)
        self.assertGreater(res.var_99_pct, res.var_95_pct)
        self.assertGreaterEqual(res.cvar_95_pct, res.var_95_pct)
        self.assertGreaterEqual(res.cvar_99_pct, res.var_99_pct)
        self.assertIn("Monte Carlo Risk & Stress-Test Summary", res.summary())

    # -------------------------------------------------------------
    # 5. Dashboard & UI Helpers Tests
    # -------------------------------------------------------------
    def test_streamlit_code_generation(self):
        code = get_streamlit_app_code()
        self.assertIn("st.title", code)
        self.assertIn("generate_volatility_surface", code)
        self.assertIn("GEXEngine", code)


if __name__ == "__main__":
    unittest.main()
