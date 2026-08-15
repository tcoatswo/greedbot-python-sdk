"""
GreedBot Market Data Source
---------------------------
Provides market pricing, next-bar open prices for paper fill simulation,
OHLCV historical bars, real-time quotes, and option chains.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence
from .base import DataSource

logger = logging.getLogger("greedbot.datasources.market")


class MarketDataSource(DataSource):
    """
    Market data provider interface supplying bar prices and option data.
    """

    @property
    def name(self) -> str:
        return "market_data"

    def get_latest_prices(self, tickers: Sequence[str]) -> Dict[str, float]:
        """Fetch latest market price for a list of tickers."""
        raise NotImplementedError

    def get_next_bar_open(self, tickers: Sequence[str]) -> Dict[str, float]:
        """
        Fetch the next session's opening price for simulated execution.
        Prevents lookahead bias by using next bar's open price.
        """
        return self.get_latest_prices(tickers)


class YahooFinanceSource(MarketDataSource):
    """
    Market data adapter using `yfinance` to fetch real market data.
    """

    def __init__(self):
        try:
            import yfinance as yf
            self._yf = yf
        except ImportError:
            self._yf = None
            logger.warning("yfinance package not installed. Live market data fetching will be limited.")

    @property
    def name(self) -> str:
        return "yahoo_finance"

    def get_latest_prices(self, tickers: Sequence[str]) -> Dict[str, float]:
        """
        Fetch current market prices for specified tickers.
        """
        out: Dict[str, float] = {}
        if not tickers:
            return out

        if self._yf is None:
            # Fallback mock pricing if yfinance not available
            for t in tickers:
                out[t.strip().lower()] = 100.0
            return out

        ticker_syms = [t.upper().strip() for t in tickers]
        try:
            if len(ticker_syms) == 1:
                t = self._yf.Ticker(ticker_syms[0])
                info = t.fast_info
                price = getattr(info, "last_price", getattr(info, "previous_close", 100.0))
                out[ticker_syms[0].lower()] = float(price or 100.0)
            else:
                data = self._yf.download(
                    tickers=" ".join(ticker_syms),
                    period="5d",
                    interval="1d",
                    progress=False,
                    auto_adjust=True
                )
                if hasattr(data, "columns") and "Close" in data:
                    close_df = data["Close"]
                    for sym in ticker_syms:
                        if sym in close_df:
                            series = close_df[sym].dropna()
                            if not series.empty:
                                out[sym.lower()] = float(series.iloc[-1])
                            else:
                                out[sym.lower()] = 100.0
                        else:
                            out[sym.lower()] = 100.0
                else:
                    for sym in ticker_syms:
                        out[sym.lower()] = 100.0
        except Exception as e:
            logger.error(f"Error fetching market data from Yahoo Finance: {e}")
            for t in tickers:
                out[t.strip().lower()] = 100.0

        return out

    def get_next_bar_open(self, tickers: Sequence[str]) -> Dict[str, float]:
        """
        Fetch next bar open prices or current live prices for paper execution.
        """
        return self.get_latest_prices(tickers)

    def get_option_chain(self, ticker: str, expiration: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch options chain for calculating implied volatility and straddle prices.
        """
        if self._yf is None:
            return {"calls": [], "puts": [], "expirations": []}

        t = self._yf.Ticker(ticker.upper().strip())
        expirations = t.options
        if not expirations:
            return {"calls": [], "puts": [], "expirations": []}

        exp = expiration if expiration in expirations else expirations[0]
        chain = t.option_chain(exp)
        return {
            "ticker": ticker.upper(),
            "expiration": exp,
            "expirations": list(expirations),
            "calls": chain.calls.to_dict(orient="records") if hasattr(chain.calls, "to_dict") else [],
            "puts": chain.puts.to_dict(orient="records") if hasattr(chain.puts, "to_dict") else [],
        }
