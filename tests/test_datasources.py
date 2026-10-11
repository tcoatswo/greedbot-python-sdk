"""
Unit tests for external data sources (Market Data & Catalysts).
"""

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
from greedbot.datasources import (
    FinancialNewsSource,
    SecEdgarSource,
    YahooFinanceSource,
    MarketDataUnavailableError,
    HistoricalBar,
    MarketDataSource,
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
        source._yf = SimpleNamespace(Ticker=lambda _: SimpleNamespace(fast_info=SimpleNamespace(last_price=125.0)))
        self.assertEqual(source.get_latest_prices(["nvda"]), {"nvda": 125.0})

    def test_missing_prices_fail_closed(self):
        source = YahooFinanceSource()
        source._yf = SimpleNamespace(Ticker=lambda _: SimpleNamespace(fast_info=SimpleNamespace(last_price=None)))
        with self.assertRaises(MarketDataUnavailableError):
            source.get_latest_prices(["NVDA"])
        with self.assertRaises(NotImplementedError):
            source.get_next_bar_open(["NVDA"])

    def test_historical_bars_exclude_incomplete_bar(self):
        source = YahooFinanceSource()
        frame = pd.DataFrame({
            "Open": [100, 101], "High": [102, 103], "Low": [99, 100],
            "Close": [101, 102], "Volume": [1000, 1200],
        }, index=pd.to_datetime(["2026-10-09", "2026-10-10"], utc=True))
        ticker = MagicMock()
        ticker.history.return_value = frame
        source._yf = SimpleNamespace(Ticker=lambda _: ticker)
        bars = source.get_historical_bars("NVDA", as_of=datetime(2026, 10, 10, 12, tzinfo=timezone.utc))
        self.assertEqual(len(bars), 1)
        self.assertEqual((bars[0].ticker, bars[0].close), ("nvda", 101))
        self.assertEqual(source.get_historical_prices("NVDA"), [101, 102])

    def test_aligned_closes_match_timestamps(self):
        source = MarketDataSource()
        first = datetime(2026, 10, 9, tzinfo=timezone.utc)
        second = datetime(2026, 10, 10, tzinfo=timezone.utc)
        def bar(symbol, stamp, price):
            return HistoricalBar(symbol, stamp, price, price, price, price, 100)
        source.get_historical_bars = lambda ticker, period, interval, as_of: (
            [bar("spy", first, 100), bar("spy", second, 101)] if ticker == "spy"
            else [bar("qqq", second, 200)])
        self.assertEqual(source.get_aligned_closes(["SPY", "QQQ"]), {"spy": [101], "qqq": [200]})


if __name__ == "__main__":
    unittest.main()
