"""
Unit tests for external data sources (Market Data & Catalysts).
"""

import unittest
from greedbot.datasources import (
    FinancialNewsSource,
    SecEdgarSource,
    YahooFinanceSource,
)


class TestDataSources(unittest.TestCase):

    def test_sec_edgar_source(self):
        source = SecEdgarSource()
        self.assertEqual(source.name, "sec_edgar")
        text = source.get_latest_catalyst_text("NVDA")
        self.assertIn("NVDA", text)

    def test_news_source(self):
        source = FinancialNewsSource()
        self.assertEqual(source.name, "financial_news")
        text = source.get_latest_catalyst_text("AAPL")
        self.assertIn("AAPL", text)

    def test_yahoo_finance_source(self):
        source = YahooFinanceSource()
        self.assertEqual(source.name, "yahoo_finance")
        prices = source.get_latest_prices(["nvda", "tsla"])
        self.assertIn("nvda", prices)
        self.assertIn("tsla", prices)
        self.assertTrue(prices["nvda"] > 0)


if __name__ == "__main__":
    unittest.main()
