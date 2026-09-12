import unittest
import math
from greedbot import (
    calculate_greeks,
    solve_iv,
    generate_volatility_surface,
    is_rust_accelerated,
)

class TestGreedBotQuant(unittest.TestCase):
    def test_rust_acceleration_loaded(self):
        self.assertTrue(is_rust_accelerated())

    def test_calculate_greeks_call(self):
        g = calculate_greeks(spot=580.0, strike=580.0, dte=30.0, iv=0.20, is_call=True)
        self.assertGreater(g.price, 0.0)
        self.assertTrue(0.45 < g.delta < 0.58)
        self.assertGreater(g.gamma, 0.0)
        self.assertGreater(g.vega, 0.0)
        self.assertLess(g.theta, 0.0)

    def test_calculate_greeks_put(self):
        g = calculate_greeks(spot=580.0, strike=580.0, dte=30.0, iv=0.20, is_call=False)
        self.assertGreater(g.price, 0.0)
        self.assertTrue(-0.58 < g.delta < -0.45)
        self.assertGreater(g.gamma, 0.0)
        self.assertGreater(g.vega, 0.0)

    def test_put_call_parity(self):
        spot = 580.0
        strike = 580.0
        dte = 30.0
        iv = 0.20
        rate = 0.045
        t = dte / 365.0

        call = calculate_greeks(spot=spot, strike=strike, dte=dte, iv=iv, is_call=True, rate=rate)
        put = calculate_greeks(spot=spot, strike=strike, dte=dte, iv=iv, is_call=False, rate=rate)

        # Put-Call Parity: C - P = S - K * exp(-r*T)
        lhs = call.price - put.price
        rhs = spot - strike * math.exp(-rate * t)
        self.assertAlmostEqual(lhs, rhs, places=3)

    def test_solve_implied_volatility(self):
        spot = 580.0
        strike = 585.0
        dte = 45.0
        target_iv = 0.28
        
        g = calculate_greeks(spot=spot, strike=strike, dte=dte, iv=target_iv, is_call=True)
        recovered_iv = solve_iv(spot=spot, strike=strike, dte=dte, market_price=g.price, is_call=True)
        
        self.assertAlmostEqual(recovered_iv, target_iv, places=3)

    def test_volatility_surface_generation(self):
        surface = generate_volatility_surface(spot=580.0, base_vol=0.20)
        self.assertGreater(len(surface), 0)
        first = surface[0]
        self.assertIn("strike", first)
        self.assertIn("dte", first)
        self.assertIn("iv", first)
        self.assertIn("call_delta", first)
        self.assertIn("gamma", first)

if __name__ == "__main__":
    unittest.main()
