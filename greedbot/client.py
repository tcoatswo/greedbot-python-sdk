"""
GreedBot Core API Client
------------------------
Provides robust HTTP communication, x-api-key authentication with key redaction,
rate-limit retries (HTTP 429), spend cap detection (HTTP 402), asynchronous receipt-to-baked
polling (HTTP 202), and slot freshness verification to prevent mid-bake stale data consumption.
"""

from __future__ import annotations

import logging
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Union

import requests

from .models import SlotInfo, TradePlan

logger = logging.getLogger("greedbot")

DEFAULT_BASE_URL: str = "https://greedbot.com"
RECEIPT_ATTEMPTS: int = 6
BAKED_ATTEMPTS: int = 30
REQUEST_TIMEOUT_SECS: float = 60.0


class GreedBotAPIError(Exception):
    """Raised when the GreedBot API returns an unhandled or client/server error."""
    pass


class GreedBotSpendCapError(GreedBotAPIError):
    """Raised when an API key has reached its monthly spend cap (HTTP 402)."""
    pass


class GreedBotStaleDataError(GreedBotAPIError):
    """Raised when a hub snapshot is superseded and not yet republished."""
    pass


class GreedBotClient:
    """
    Client for GreedBot /api/v1 machine endpoints.

    Parameters:
    - `api_key`: GreedBot API key. If omitted, read from `GREEDBOT_API_KEY` env var.
    - `base_url`: Base URL for the API. If omitted, read from `GREEDBOT_API_BASE` or defaults to `https://greedbot.com`.
    - `timeout`: Per-request timeout in seconds (default 60.0s).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = REQUEST_TIMEOUT_SECS,
    ):
        self.api_key = (api_key or os.environ.get("GREEDBOT_API_KEY", "")).strip()
        env_base = os.environ.get("GREEDBOT_API_BASE", DEFAULT_BASE_URL)
        self.base_url = (base_url or env_base).rstrip("/")
        self.timeout = float(timeout)

        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {self.api_key}",
            })
        self.session.headers.update({
            "User-Agent": "GreedBot-Python-SDK/1.0.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def __repr__(self) -> str:
        return f"GreedBotClient(base_url='{self.base_url}', api_key='<redacted>', timeout={self.timeout})"

    @classmethod
    def from_env(cls) -> GreedBotClient:
        """Create a client instance reading GREEDBOT_API_KEY from the environment."""
        key = os.environ.get("GREEDBOT_API_KEY", "").strip()
        if not key:
            raise ValueError("Missing GREEDBOT_API_KEY environment variable. Obtain one at https://greedbot.com/auth/account")
        return cls(api_key=key)

    def _request_with_retry(
        self,
        method: str,
        path_or_url: str,
        max_retries: int = RECEIPT_ATTEMPTS,
        **kwargs
    ) -> requests.Response:
        """
        Execute an HTTP request with automatic rate-limit and transient error handling.
        """
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            url = path_or_url
        else:
            p = path_or_url if path_or_url.startswith("/") else f"/{path_or_url}"
            url = f"{self.base_url}{p}"

        kwargs.setdefault("timeout", self.timeout)
        backoff = 1.0

        for attempt in range(max_retries):
            try:
                resp = self.session.request(method, url, **kwargs)

                # HTTP 402: Spend Cap reached
                if resp.status_code == 402:
                    raise GreedBotSpendCapError(
                        f"Monthly spend cap reached for API key on {method} {url} (HTTP 402). "
                        f"Adjust your spend cap at https://greedbot.com/auth/account"
                    )

                # HTTP 429: Rate limited -> sleep Retry-After
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    sleep_time = float(retry_after) if retry_after else backoff
                    sleep_time += random.uniform(0.1, 0.5)  # add jitter
                    time.sleep(sleep_time)
                    backoff *= 1.5
                    continue

                return resp

            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt == max_retries - 1:
                    raise GreedBotAPIError(f"Network request failed for {method} {url}: {e}") from e
                jitter = random.uniform(0.1, 0.5)
                time.sleep(backoff + jitter)
                backoff *= 1.5

        raise GreedBotAPIError(f"Exceeded max retries ({max_retries}) for {method} {url}")

    def post_baked(
        self,
        route: str,
        body: Dict[str, Any],
        receipt_attempts: int = RECEIPT_ATTEMPTS,
        baked_attempts: int = BAKED_ATTEMPTS,
    ) -> Dict[str, Any]:
        """
        POST to `{route}/receipt`, extract receipt id, and poll `{route}/baked`
        until HTTP 200 is returned. Handles HTTP 202 (processing) and 429 (rate limit).
        """
        clean_route = route.rstrip("/")
        receipt_url = f"{clean_route}/receipt"
        baked_url = f"{clean_route}/baked"

        # 1. Enqueue job receipt
        resp = self._request_with_retry("POST", receipt_url, json=body, max_retries=receipt_attempts)
        if resp.status_code not in (200, 202):
            raise GreedBotAPIError(f"Receipt submission failed ({resp.status_code}) on {receipt_url}: {resp.text}")

        receipt_data = resp.json()
        receipt_id = receipt_data.get("id") or receipt_data.get("receipt_id")
        if not receipt_id:
            # Immediate synchronous return
            return receipt_data

        # 2. Poll baked endpoint
        poll_delay = 1.0
        for _ in range(baked_attempts):
            # Send receipt_id in POST body or fallback
            poll_resp = self._request_with_retry(
                "POST",
                baked_url,
                json={"receipt_id": receipt_id},
                max_retries=RECEIPT_ATTEMPTS
            )

            if poll_resp.status_code == 200:
                return poll_resp.json()
            elif poll_resp.status_code == 202:
                retry_header = poll_resp.headers.get("Retry-After")
                sleep_secs = float(retry_header) if retry_header else poll_delay
                time.sleep(sleep_secs)
                poll_delay = min(poll_delay * 1.3, 4.0)
            else:
                raise GreedBotAPIError(
                    f"Baked polling failed ({poll_resp.status_code}) on {baked_url}: {poll_resp.text}"
                )

        raise TimeoutError(f"Timed out after {baked_attempts} attempts polling baked result for receipt '{receipt_id}'")

    def get_hub_when_current(
        self,
        hub: str,
        max_attempts: int = 10,
        retry_secs: float = 60.0,
    ) -> Dict[str, Any]:
        """
        GET a hub snapshot (`ideas`, `crypto`, `earnings`, `macro`, `dia`, `qqq`) and
        return it ONLY IF IT IS CURRENT (active within its slot effective window).

        During daily/intraday bakes (just after 00:00 UTC), hub endpoints intentionally serve
        the PREVIOUS slot rather than a half-written one. This method validates the `slot.effective_until`
        window and waits for the new slot to publish before returning.
        """
        url = f"/api/v1/hub/{hub.lower().strip()}/latest"
        last_slot: Optional[SlotInfo] = None

        for attempt in range(max(1, max_attempts)):
            resp = self._request_with_retry("GET", url)
            if resp.status_code != 200:
                raise GreedBotAPIError(f"Failed to fetch hub '{hub}' ({resp.status_code}): {resp.text}")

            body = resp.json()
            slot = SlotInfo.from_payload(body)
            if slot is None:
                raise GreedBotAPIError(f"No usable slot block on {url}; cannot confirm data freshness")

            if slot.is_effective_now():
                return body

            last_slot = slot
            if attempt + 1 < max_attempts:
                time.sleep(max(1.0, retry_secs))

        raise GreedBotStaleDataError(
            f"Hub '{hub}' served a superseded slot after {max_attempts} attempts "
            f"(last: slot {last_slot.year}/{last_slot.refresh_n} effective until {last_slot.effective_until}); "
            f"refusing to act on stale data."
        )

    # ---------------------------------------------------------------------------
    # System & Spend Endpoints (Free / Unmetered)
    # ---------------------------------------------------------------------------

    def ping(self) -> str:
        """Health check endpoint. Always replies 'PONG'. Unmetered."""
        resp = self._request_with_retry("GET", "/api/v1/ping")
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Ping failed ({resp.status_code}): {resp.text}")
        try:
            return resp.json()
        except Exception:
            return resp.text.strip('"')

    def get_usage(self) -> Dict[str, Any]:
        """
        Return per-key and per-user usage plus Stripe billing summaries.
        Always free/unmetered.
        """
        resp = self._request_with_retry("GET", "/api/v1/usage")
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch usage ({resp.status_code}): {resp.text}")
        return resp.json()

    # ---------------------------------------------------------------------------
    # Core Quant & Computation Endpoints (Receipt / Baked)
    # ---------------------------------------------------------------------------

    def get_targets(
        self,
        tickers: Union[str, Sequence[str]],
        intervals: Sequence[str] = ("1w", "1d"),
        interval_aggregation_mode: str = "raw",
    ) -> Dict[str, Any]:
        """
        Fetch quantitative directional price targets and support/resistance zones.
        """
        ticker_list = [tickers.lower()] if isinstance(tickers, str) else [t.lower() for t in tickers]
        payload = {
            "tickers": ticker_list,
            "intervals": list(intervals),
            "interval_aggregation_mode": interval_aggregation_mode,
        }
        return self.post_baked("/api/v1/targets", payload)

    def get_kelly(
        self,
        tickers: Union[str, Sequence[str]],
        intervals: Sequence[str] = ("1w", "1d"),
        kelly_fraction: float = 0.5,
        interval_aggregation_mode: str = "raw",
        win_rate_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Fetch Kelly criterion portfolio weights and sizing fractions (-1.0 to +1.0).
        """
        ticker_list = [tickers.lower()] if isinstance(tickers, str) else [t.lower() for t in tickers]
        payload: Dict[str, Any] = {
            "tickers": ticker_list,
            "intervals": list(intervals),
            "kelly_fraction": float(kelly_fraction),
            "interval_aggregation_mode": interval_aggregation_mode,
        }
        if win_rate_override is not None:
            payload["win_rate_override"] = float(win_rate_override)
        return self.post_baked("/api/v1/kelly", payload)

    def get_parity(
        self,
        tickers: Union[str, Sequence[str]],
        intervals: Sequence[str] = ("1w", "1d"),
        interval_aggregation_mode: str = "raw",
    ) -> Dict[str, Any]:
        """
        Fetch risk parity portfolio allocation weights.
        """
        ticker_list = [tickers.lower()] if isinstance(tickers, str) else [t.lower() for t in tickers]
        payload = {
            "tickers": ticker_list,
            "intervals": list(intervals),
            "interval_aggregation_mode": interval_aggregation_mode,
        }
        return self.post_baked("/api/v1/parity", payload)

    def get_rebalance(
        self,
        current: Dict[str, Any],
        target: Dict[str, Any],
        current_input_type: str = "dollars",
        target_input_type: str = "dollars",
        output_type: str = "shares",
    ) -> Dict[str, Any]:
        """
        Compute rebalancing orders given current holdings and target holdings.
        """
        payload = {
            "current": current,
            "target": target,
            "current_input_type": current_input_type,
            "target_input_type": target_input_type,
            "output_type": output_type,
        }
        return self.post_baked("/api/v1/rebalance", payload)

    def get_pizza(
        self,
        tickers: Optional[Union[str, Sequence[str]]] = None,
        fundamentals_mode: str = "off",
    ) -> Dict[str, Any]:
        """
        Fetch GreedBot multi-factor Pizza rankings (fundamentals + technicals).
        `fundamentals_mode`: 'off' (technicals only), 'required', or 'only'.
        """
        payload: Dict[str, Any] = {"fundamentals_mode": fundamentals_mode}
        if tickers:
            ticker_list = [tickers.lower()] if isinstance(tickers, str) else [t.lower() for t in tickers]
            payload["tickers"] = ticker_list
        return self.post_baked("/api/v1/pizza", payload)

    def get_metadata(self, tickers: Union[str, Sequence[str]]) -> Dict[str, Any]:
        """
        Fetch rich company fundamentals and metadata for specified tickers.
        """
        ticker_list = [tickers.lower()] if isinstance(tickers, str) else [t.lower() for t in tickers]
        return self.post_baked("/api/v1/metadata", {"tickers": ticker_list})

    def get_plot(
        self,
        ticker: str,
        plot_type: str = "chart",
        interval: str = "1d",
        output_file: Optional[str] = None,
    ) -> bytes:
        """
        Render the chart as a PNG image for visual agent inspection.
        `plot_type`: 'chart' (candles + technicals) or 'algo_targets'.
        `interval`: '1d' (default) or '1w'.
        """
        payload = {
            "ticker": ticker.lower().strip(),
            "plot_type": plot_type,
            "interval": interval,
        }

        # 1. Enqueue plot receipt
        receipt_resp = self._request_with_retry("POST", "/api/v1/plot/receipt", json=payload)
        if receipt_resp.status_code != 200:
            raise GreedBotAPIError(f"Plot receipt failed ({receipt_resp.status_code}): {receipt_resp.text}")

        receipt_id = receipt_resp.json().get("id")
        if not receipt_id:
            raise GreedBotAPIError(f"No receipt id in plot response: {receipt_resp.text}")

        # 2. Poll for the PNG bytes
        poll_delay = 1.0
        for _ in range(BAKED_ATTEMPTS):
            poll_resp = self._request_with_retry(
                "POST",
                "/api/v1/plot/baked",
                json={"receipt_id": receipt_id},
            )
            if poll_resp.status_code == 200:
                image_bytes = poll_resp.content
                if output_file:
                    with open(output_file, "wb") as f:
                        f.write(image_bytes)
                return image_bytes
            elif poll_resp.status_code == 202:
                time.sleep(poll_delay)
                poll_delay = min(poll_delay * 1.3, 4.0)
            else:
                raise GreedBotAPIError(f"Plot polling failed ({poll_resp.status_code}): {poll_resp.text}")

        raise TimeoutError(f"Timed out polling plot image for receipt {receipt_id}")

    # ---------------------------------------------------------------------------
    # Hub Endpoints (Metered 1 Unit / 5c)
    # ---------------------------------------------------------------------------

    def get_hub_ideas(self) -> Dict[str, Any]:
        """Fetch latest algorithmic trade ideas snapshot."""
        resp = self._request_with_retry("GET", "/api/v1/hub/ideas/latest")
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch hub trade ideas: {resp.text}")
        return resp.json()

    def get_hub_macro(self) -> Dict[str, Any]:
        """Fetch latest macro regime, inflation, and market cycle indicators."""
        resp = self._request_with_retry("GET", "/api/v1/hub/macro/latest")
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch macro regime: {resp.text}")
        return resp.json()

    def get_hub_earnings(self) -> Dict[str, Any]:
        """
        Fetch latest 90-day Earnings Radar with qualifying reports labeled by horizon
        ('today', 'next-bd', 'next-7-bd', 'next-30-bd', 'next-90-days') and cross-sectional ranks.
        """
        resp = self._request_with_retry("GET", "/api/v1/hub/earnings/latest")
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch earnings radar: {resp.text}")
        return resp.json()

    def get_hub_earnings_expected_move(
        self,
        ticker: str,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Price the options market expected move for an earnings report from the options chain.
        """
        params: Dict[str, str] = {"ticker": ticker.upper().strip()}
        if date:
            params["date"] = date.strip()
        resp = self._request_with_retry("GET", "/api/v1/hub/earnings/expected-move", params=params)
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch earnings expected move for {ticker}: {resp.text}")
        return resp.json()

    def get_hub_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch latest hub snapshot for an ETF or asset (e.g. 'dia', 'qqq', 'ibb', 'spy', 'crypto').
        """
        t = ticker.lower().strip()
        resp = self._request_with_retry("GET", f"/api/v1/hub/{t}/latest")
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch hub for {ticker}: {resp.text}")
        return resp.json()

    # ---------------------------------------------------------------------------
    # Hosted Bot Fleet & Copy Trading (Metered 1 Unit / 5c)
    # ---------------------------------------------------------------------------

    def get_bots(self) -> Dict[str, Any]:
        """
        Fetch hosted paper-bot fleet leaderboard, fund mixes, and performance metrics.
        """
        resp = self._request_with_retry("GET", "/api/v1/bots")
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch bot fleet: {resp.text}")
        return resp.json()

    def get_bot_book(self, bot_id: str) -> Dict[str, Any]:
        """
        Fetch open positions, planned allocations, and book history for a specific bot.
        """
        resp = self._request_with_retry("GET", f"/api/v1/bots/{bot_id.strip()}/book")
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch book for bot '{bot_id}': {resp.text}")
        return resp.json()

    # ---------------------------------------------------------------------------
    # Trade Log Endpoints (Always Free / Unmetered)
    # ---------------------------------------------------------------------------

    def list_logs(
        self,
        page: int = 1,
        per: int = 50,
        status: str = "active",
        ticker: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List trade journal plans. Never metered.
        `status`: 'active' (default), 'finished', 'planned', 'open', 'closed', 'canceled', or 'all'.
        """
        params: Dict[str, Any] = {"page": page, "per": per, "status": status}
        if ticker:
            params["ticker"] = ticker.strip().lower()
        if tag:
            params["tag"] = tag.strip()
        resp = self._request_with_retry("GET", "/api/v1/log", params=params)
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to list trade logs: {resp.text}")
        return resp.json()

    def create_log(self, plan: Union[Dict[str, Any], TradePlan]) -> Dict[str, Any]:
        """
        Create a trade plan in the journal. Never metered.
        """
        payload = plan.to_dict() if isinstance(plan, TradePlan) else plan
        resp = self._request_with_retry("POST", "/api/v1/log", json=payload)
        if resp.status_code not in (200, 201):
            raise GreedBotAPIError(f"Failed to create trade plan: {resp.text}")
        return resp.json()

    def get_log(self, log_id: str) -> Dict[str, Any]:
        """Get one trade plan with its fills and status. Never metered."""
        resp = self._request_with_retry("GET", f"/api/v1/log/{log_id.strip()}")
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to get trade plan '{log_id}': {resp.text}")
        return resp.json()

    def open_log(
        self,
        log_id: str,
        opened_at: Optional[str] = None,
        entry_price: Optional[str] = None,
        shares: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark a trade plan as opened. Never metered."""
        payload: Dict[str, Any] = {}
        if opened_at:
            payload["opened_at"] = opened_at
        if entry_price:
            payload["entry_price"] = str(entry_price)
        if shares:
            payload["shares"] = str(shares)
        resp = self._request_with_retry("POST", f"/api/v1/log/{log_id.strip()}/open", json=payload)
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to open trade plan '{log_id}': {resp.text}")
        return resp.json()

    def close_log(
        self,
        log_id: str,
        closed_at: Optional[str] = None,
        exit_price: Optional[str] = None,
        net_pnl: Optional[str] = None,
        realized_r: Optional[str] = None,
        exit_reason: Optional[str] = None,
        exit_notes: Optional[str] = None,
        followed_plan: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark a trade plan as closed. Never metered."""
        payload: Dict[str, Any] = {}
        if closed_at:
            payload["closed_at"] = closed_at
        if exit_price:
            payload["exit_price"] = str(exit_price)
        if net_pnl:
            payload["net_pnl"] = str(net_pnl)
        if realized_r:
            payload["realized_r"] = str(realized_r)
        if exit_reason:
            payload["exit_reason"] = exit_reason
        if exit_notes:
            payload["exit_notes"] = exit_notes
        if followed_plan:
            payload["followed_plan"] = followed_plan
        resp = self._request_with_retry("POST", f"/api/v1/log/{log_id.strip()}/close", json=payload)
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to close trade plan '{log_id}': {resp.text}")
        return resp.json()

    def cancel_log(
        self,
        log_id: str,
        canceled_at: Optional[str] = None,
        cancel_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cancel a trade plan. Never metered."""
        payload: Dict[str, Any] = {}
        if canceled_at:
            payload["canceled_at"] = canceled_at
        if cancel_reason:
            payload["cancel_reason"] = cancel_reason
        resp = self._request_with_retry("POST", f"/api/v1/log/{log_id.strip()}/cancel", json=payload)
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to cancel trade plan '{log_id}': {resp.text}")
        return resp.json()
