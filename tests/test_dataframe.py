"""
Unit tests for DataFrame parsing and extraction helpers.
"""

import unittest
from greedbot.dataframe import (
    extract_signal,
    map_from_df,
    ranking_from_pizza,
    to_dataframe,
)


class TestDataFrameHelpers(unittest.TestCase):

    def test_map_from_df(self):
        payload = {
            "df": {
                "ticker": ["AAPL", "msft", "NVDA"],
                "kelly": [0.5, None, 1.0],
            }
        }
        res = map_from_df(payload, "kelly")
        self.assertAlmostEqual(res["aapl"], 0.5)
        self.assertAlmostEqual(res["msft"], 0.0)
        self.assertAlmostEqual(res["nvda"], 1.0)

    def test_ranking_from_pizza_ascending(self):
        payload = {
            "pizza": {
                "df": {
                    "ticker": ["xlk", "xle", "xlf"],
                    "pizza_slice": [0.9, 0.1, 0.5],
                }
            }
        }
        ranking = ranking_from_pizza(payload)
        self.assertEqual(len(ranking), 3)
        self.assertEqual(ranking[0], ("xle", 0.1))
        self.assertEqual(ranking[1], ("xlf", 0.5))
        self.assertEqual(ranking[2], ("xlk", 0.9))

    def test_extract_signal_success_and_fallback(self):
        # Preferred algos column
        payload = {
            "df": {
                "ticker": ["nvda", "amd"],
                "algos": [0.45, -0.20],
                "kelly": [0.30, -0.10],
            }
        }
        self.assertAlmostEqual(extract_signal(payload, "NVDA"), 0.45)
        self.assertAlmostEqual(extract_signal(payload, "amd"), -0.20)

        # Flat when absent
        self.assertAlmostEqual(extract_signal(payload, "tsla"), 0.0)

    def test_extract_signal_excluded_ticker_raises(self):
        payload = {
            "excluded_tickers": {
                "unknown_symbol": ["zzzz", "foo"],
            },
            "df": {
                "ticker": ["aapl"],
                "algos": [0.5],
            },
        }
        with self.assertRaises(ValueError) as ctx:
            extract_signal(payload, "ZZZZ")
        self.assertIn("excluded by server", str(ctx.exception))

    def test_to_dataframe(self):
        payload = {
            "df": {
                "ticker": ["AAPL", "MSFT"],
                "price": [150.0, 300.0],
            }
        }
        df = to_dataframe(payload)
        self.assertEqual(len(df), 2)
        self.assertIn("ticker", df.columns)


if __name__ == "__main__":
    unittest.main()
