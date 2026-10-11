"""Market data for strategies and paper trading.

Unavailable data raises instead of silently substituting synthetic prices.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence

from .base import DataSource


class MarketDataUnavailableError(RuntimeError):
    """The provider did not return usable market data."""


@dataclass(frozen=True)
class HistoricalBar:
    ticker: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


def _price(value: Any) -> float:
    try:
        price = float(value)
    except (TypeError, ValueError) as exc:
        raise MarketDataUnavailableError("Provider returned a non-numeric price") from exc
    if not math.isfinite(price) or price <= 0:
        raise MarketDataUnavailableError("Provider returned a non-positive or non-finite price")
    return price


def _bar_duration(interval: str) -> timedelta:
    match = re.fullmatch(r"([1-9][0-9]*)(m|h|d|wk)", interval)
    if not match:
        raise ValueError("interval must be a positive number followed by m, h, d, or wk")
    count = int(match.group(1))
    unit = match.group(2)
    return timedelta(minutes=count) if unit == "m" else (
        timedelta(hours=count) if unit == "h" else (
            timedelta(days=count) if unit == "d" else timedelta(weeks=count)))


class MarketDataSource(DataSource):
    @property
    def name(self) -> str:
        return "market_data"

    def get_latest_prices(self, tickers: Sequence[str]) -> Dict[str, float]:
        raise NotImplementedError

    def get_next_bar_open(self, tickers: Sequence[str]) -> Dict[str, float]:
        """A future bar cannot be fetched before it opens; provide it during replay."""
        raise NotImplementedError("Next-bar opens are only available after the next bar starts")

    def get_historical_bars(self, ticker: str, period: str = "6mo", interval: str = "1d",
                            as_of: Optional[datetime] = None) -> List[HistoricalBar]:
        raise NotImplementedError

    def get_historical_prices(self, ticker: str, period: str = "6mo", interval: str = "1d") -> List[float]:
        return [bar.close for bar in self.get_historical_bars(ticker, period, interval)]

    def get_aligned_closes(self, tickers: Sequence[str], period: str = "6mo", interval: str = "1d",
                           as_of: Optional[datetime] = None) -> Dict[str, List[float]]:
        """Join completed bars on common timestamps for multi-asset strategies."""
        symbols = [ticker.strip().lower() for ticker in tickers]
        if not symbols or any(not symbol for symbol in symbols) or len(set(symbols)) != len(symbols):
            raise ValueError("Tickers must be nonempty and unique")
        by_symbol = {symbol: {bar.timestamp: bar.close for bar in self.get_historical_bars(
            symbol, period, interval, as_of)} for symbol in symbols}
        common = sorted(set.intersection(*(set(bars) for bars in by_symbol.values())))
        if not common:
            raise MarketDataUnavailableError("Tickers have no common completed bars")
        return {symbol: [by_symbol[symbol][stamp] for stamp in common] for symbol in symbols}


class YahooFinanceSource(MarketDataSource):
    def __init__(self):
        try:
            import yfinance as yf
        except ImportError as exc:
            raise MarketDataUnavailableError("Install yfinance to use YahooFinanceSource") from exc
        self._yf = yf

    @property
    def name(self) -> str:
        return "yahoo_finance"

    def get_latest_prices(self, tickers: Sequence[str]) -> Dict[str, float]:
        symbols = list(dict.fromkeys(t.strip().upper() for t in tickers))
        if not symbols:
            return {}
        if any(not symbol for symbol in symbols):
            raise ValueError("Ticker cannot be empty")
        try:
            result = {}
            for symbol in symbols:
                info = self._yf.Ticker(symbol).fast_info
                result[symbol.lower()] = _price(getattr(info, "last_price", None))
            return result
        except MarketDataUnavailableError:
            raise
        except Exception as exc:
            raise MarketDataUnavailableError("Failed to fetch latest Yahoo Finance prices") from exc

    def get_historical_bars(self, ticker: str, period: str = "6mo", interval: str = "1d",
                            as_of: Optional[datetime] = None) -> List[HistoricalBar]:
        symbol = ticker.strip().upper()
        if not symbol:
            raise ValueError("Ticker cannot be empty")
        duration = _bar_duration(interval)
        cutoff = as_of or datetime.now(timezone.utc)
        if cutoff.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        try:
            history = self._yf.Ticker(symbol).history(period=period, interval=interval)
            bars = []
            for stamp, row in history.iterrows():
                timestamp = stamp.to_pydatetime() if hasattr(stamp, "to_pydatetime") else stamp
                if timestamp.tzinfo is None:
                    raise MarketDataUnavailableError("Provider returned a bar without timezone information")
                if timestamp + duration > cutoff:
                    continue
                opening = _price(row["Open"])
                high = _price(row["High"])
                low = _price(row["Low"])
                close = _price(row["Close"])
                volume = float(row["Volume"])
                if not math.isfinite(volume) or volume < 0 or low > min(opening, close) or high < max(opening, close):
                    raise MarketDataUnavailableError("Provider returned an invalid OHLCV bar")
                bars.append(HistoricalBar(symbol.lower(), timestamp, opening, high, low, close, volume))
            if not bars:
                raise MarketDataUnavailableError(f"No completed historical bars for {symbol}")
            return bars
        except MarketDataUnavailableError:
            raise
        except Exception as exc:
            raise MarketDataUnavailableError(f"Failed to fetch historical bars for {symbol}") from exc

    def get_option_chain(self, ticker: str, expiration: Optional[str] = None) -> Dict[str, Any]:
        symbol = ticker.strip().upper()
        if not symbol:
            raise ValueError("Ticker cannot be empty")
        try:
            security = self._yf.Ticker(symbol)
            expirations = security.options
            if not expirations:
                raise MarketDataUnavailableError(f"No option expirations for {symbol}")
            if expiration is not None and expiration not in expirations:
                raise MarketDataUnavailableError(f"Expiration {expiration} unavailable for {symbol}")
            expiry = expiration or expirations[0]
            chain = security.option_chain(expiry)
            return {"ticker": symbol, "expiration": expiry, "expirations": list(expirations),
                    "calls": chain.calls.to_dict(orient="records"),
                    "puts": chain.puts.to_dict(orient="records")}
        except MarketDataUnavailableError:
            raise
        except Exception as exc:
            raise MarketDataUnavailableError(f"Failed to fetch option chain for {symbol}") from exc
