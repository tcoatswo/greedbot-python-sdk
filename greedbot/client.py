"""
GreedBot Core API Client
------------------------
Provides robust HTTP communication, rate-limit retries (HTTP 429), and async receipt
polling with progressive exponential backoff for computed quant results.
"""

import os
import sys
import time
import requests
from typing import Dict, Any, List, Optional, Union

DEFAULT_BASE_URL = "https://greedbot.com"

class GreedBotAPIError(Exception):
    """Raised when the GreedBot API returns an unhandled error."""
    pass

class GreedBotClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = DEFAULT_BASE_URL):
        self.api_key = api_key or os.environ.get("GREEDBOT_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        self.session.headers.update({
            "User-Agent": "GreedBot-Python-SDK/1.0.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def _request_with_retry(self, method: str, path: str, max_retries: int = 5, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        backoff = 1.0

        for attempt in range(max_retries):
            try:
                resp = self.session.request(method, url, **kwargs)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    sleep_time = float(retry_after) if retry_after else backoff
                    time.sleep(sleep_time)
                    backoff *= 1.5
                    continue
                return resp
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise GreedBotAPIError(f"Network request failed: {e}") from e
                time.sleep(backoff)
                backoff *= 1.5

        raise GreedBotAPIError(f"Exceeded max retries ({max_retries}) for {method} {url}")

    def _poll_receipt(self, receipt_url: str, baked_url: str, payload: Dict[str, Any], max_attempts: int = 15) -> Dict[str, Any]:
        """Handles async job receipt submission and polls until computation completes."""
        resp = self._request_with_retry("POST", receipt_url, json=payload)
        if resp.status_code not in (200, 202):
            raise GreedBotAPIError(f"Receipt submission failed ({resp.status_code}): {resp.text}")

        data = resp.json()
        receipt_id = data.get("receipt_id") or data.get("id")
        if not receipt_id:
            return data  # Immediate synchronous result

        delay = 1.0
        for _ in range(max_attempts):
            poll_resp = self._request_with_retry("GET", f"{baked_url}?receipt_id={receipt_id}")
            if poll_resp.status_code == 200:
                return poll_resp.json()
            elif poll_resp.status_code == 202:
                time.sleep(delay)
                delay = min(delay * 1.3, 4.0)
            else:
                raise GreedBotAPIError(f"Receipt polling failed ({poll_resp.status_code}): {poll_resp.text}")

        raise TimeoutError(f"Timed out polling baked result for receipt {receipt_id}")

    # Core Quant Endpoints
    def get_targets(self, tickers: Union[str, List[str]], risk_tolerance: str = "moderate") -> Dict[str, Any]:
        ticker_list = [tickers] if isinstance(tickers, str) else tickers
        payload = {"tickers": ticker_list, "risk_tolerance": risk_tolerance}
        return self._poll_receipt(
            receipt_url="/api/v1/targets/receipt",
            baked_url="/api/v1/targets/baked",
            payload=payload
        )

    def get_kelly(self, tickers: Union[str, List[str]], win_rate_override: Optional[float] = None) -> Dict[str, Any]:
        ticker_list = [tickers] if isinstance(tickers, str) else tickers
        payload: Dict[str, Any] = {"tickers": ticker_list}
        if win_rate_override is not None:
            payload["win_rate_override"] = win_rate_override
        return self._poll_receipt(
            receipt_url="/api/v1/kelly/receipt",
            baked_url="/api/v1/kelly/baked",
            payload=payload
        )

    def get_pizza(self, tickers: Optional[List[str]] = None) -> Dict[str, Any]:
        params = {"tickers": ",".join(tickers)} if tickers else {}
        resp = self._request_with_retry("GET", "/api/v1/pizza", params=params)
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch pizza rankings: {resp.text}")
        return resp.json()

    # Hub Endpoints
    def get_hub_macro(self) -> Dict[str, Any]:
        resp = self._request_with_retry("GET", "/api/v1/hub/macro/latest")
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch macro regime: {resp.text}")
        return resp.json()

    def get_hub_ideas(self) -> List[Dict[str, Any]]:
        resp = self._request_with_retry("GET", "/api/v1/hub/ideas/latest")
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch hub trade ideas: {resp.text}")
        data = resp.json()
        return data if isinstance(data, list) else data.get("ideas", [])

    def get_hub_earnings(self) -> List[Dict[str, Any]]:
        resp = self._request_with_retry("GET", "/api/v1/hub/earnings/calendar")
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch earnings calendar: {resp.text}")
        data = resp.json()
        return data if isinstance(data, list) else data.get("earnings", [])

    def get_hub_earnings_expected_move(self, ticker: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        params = {"ticker": ticker.upper()} if ticker else {}
        resp = self._request_with_retry("GET", "/api/v1/hub/earnings/expected-move", params=params)
        if resp.status_code != 200:
            raise GreedBotAPIError(f"Failed to fetch expected moves: {resp.text}")
        return resp.json()
