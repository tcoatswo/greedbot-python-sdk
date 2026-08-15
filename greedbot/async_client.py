"""
AsyncGreedBotClient
-------------------
High-concurrency, non-blocking asynchronous client for parallel quant scans,
concurrent receipt polling, and event-driven trading bots.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Sequence
import requests

from .client import (
    DEFAULT_BASE_URL,
    GreedBotAPIError,
    GreedBotClient,
    GreedBotSpendCapError,
    GreedBotStaleDataError,
)
from .models import SlotInfo

logger = logging.getLogger("greedbot.async_client")


class AsyncGreedBotClient:
    """
    Asynchronous GreedBot Client supporting asyncio concurrency.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self._sync_client = GreedBotClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    @property
    def api_key(self) -> str:
        return self._sync_client.api_key

    @property
    def base_url(self) -> str:
        return self._sync_client.base_url

    def __repr__(self) -> str:
        return (
            f"AsyncGreedBotClient(base_url={self.base_url!r}, "
            f"api_key='<redacted>', timeout={self._sync_client.timeout})"
        )

    async def ping(self) -> str:
        """Asynchronous public health check."""
        return await asyncio.to_thread(self._sync_client.ping)

    async def get_usage(self) -> Dict[str, Any]:
        """Asynchronous spend & usage check."""
        return await asyncio.to_thread(self._sync_client.get_usage)

    async def get_targets(
        self,
        tickers: Sequence[str],
        intervals: Sequence[str] = ("1w", "1d"),
        interval_aggregation_mode: str = "raw",
    ) -> Dict[str, Any]:
        """Asynchronous /targets receipt-to-baked computation."""
        return await asyncio.to_thread(
            self._sync_client.get_targets,
            tickers=tickers,
            intervals=intervals,
            interval_aggregation_mode=interval_aggregation_mode,
        )

    async def get_kelly(
        self,
        tickers: Sequence[str],
        intervals: Sequence[str] = ("1w", "1d"),
        kelly_fraction: float = 0.5,
        interval_aggregation_mode: str = "raw",
        win_rate_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Asynchronous /kelly computation."""
        return await asyncio.to_thread(
            self._sync_client.get_kelly,
            tickers=tickers,
            intervals=intervals,
            kelly_fraction=kelly_fraction,
            interval_aggregation_mode=interval_aggregation_mode,
            win_rate_override=win_rate_override,
        )

    async def get_parity(
        self,
        tickers: Sequence[str],
        intervals: Sequence[str] = ("1w", "1d"),
        interval_aggregation_mode: str = "raw",
    ) -> Dict[str, Any]:
        """Asynchronous /parity computation."""
        return await asyncio.to_thread(
            self._sync_client.get_parity,
            tickers=tickers,
            intervals=intervals,
            interval_aggregation_mode=interval_aggregation_mode,
        )

    async def get_pizza(
        self,
        tickers: Optional[Sequence[str]] = None,
        fundamentals_mode: str = "off",
    ) -> Dict[str, Any]:
        """Asynchronous /pizza leaderboard."""
        return await asyncio.to_thread(
            self._sync_client.get_pizza,
            tickers=tickers,
            fundamentals_mode=fundamentals_mode,
        )

    async def get_hub_macro(self) -> Dict[str, Any]:
        """Asynchronous /hub/macro/latest snapshot."""
        return await asyncio.to_thread(self._sync_client.get_hub_macro)

    async def get_hub_earnings(self) -> Dict[str, Any]:
        """Asynchronous /hub/earnings/latest snapshot."""
        return await asyncio.to_thread(self._sync_client.get_hub_earnings)

    async def get_hub_earnings_expected_move(
        self, ticker: str, date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Asynchronous /hub/earnings/expected-move calculation."""
        return await asyncio.to_thread(
            self._sync_client.get_hub_earnings_expected_move,
            ticker=ticker,
            date=date,
        )

    async def batch_scan_expected_moves(self, tickers: Sequence[str]) -> Dict[str, Any]:
        """
        Concurrently price options expected moves across a basket of tickers.
        """
        tasks = [self.get_hub_earnings_expected_move(t) for t in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: Dict[str, Any] = {}
        for ticker, res in zip(tickers, results):
            if isinstance(res, Exception):
                output[ticker.upper()] = {"error": str(res)}
            else:
                output[ticker.upper()] = res
        return output
