"""Broker API adapters. An accepted order is not an execution fill."""

import math
import os
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import quote

import requests

from .broker import Broker
from .models import Fill, OrderIntent, Side, TradePlan


def _positive(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite and greater than zero") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be finite and greater than zero")
    return number


def _order_id(value: Any) -> str:
    identifier = str(value)
    if not identifier or identifier in ("None", ".", "..") or "/" in identifier:
        raise ValueError("A valid order ID is required")
    return quote(identifier, safe="")


def _fill(order: Dict[str, Any], intent: OrderIntent, quantity_key: str, price_key: str) -> Optional[Fill]:
    """Return only quantity and price explicitly confirmed by the broker."""
    quantity = float(order.get(quantity_key) or 0)
    if not math.isfinite(quantity) or quantity < 0:
        raise ValueError("Broker returned an invalid filled quantity")
    if quantity == 0:
        return None
    price = _positive(order.get(price_key), "broker filled price")
    return Fill(ticker=intent.ticker, side=intent.side, quantity=quantity, price=price)


def _intent_quantity(intent: OrderIntent, current_prices: Optional[Dict[str, float]], whole_shares: bool) -> float:
    prices = {key.lower(): value for key, value in (current_prices or {}).items()}
    reference = prices.get(intent.ticker)
    if reference is None:
        reference = intent.limit
    if reference is None:
        raise ValueError(f"A current price or limit is required to size {intent.ticker}")
    price = _positive(reference, "reference price")
    quantity = intent.dollars / price
    if whole_shares:
        quantity = math.floor(quantity)
    else:
        quantity = math.floor(quantity * 10000) / 10000
    if quantity <= 0:
        raise ValueError(f"Order for {intent.ticker} is smaller than the broker quantity increment")
    return quantity


def _whole_quantity(value: Any, name: str) -> int:
    number = _positive(value, name)
    if number != int(number):
        raise ValueError(f"{name} must be a whole number")
    return int(number)


class AlpacaBrokerAdapter(Broker):
    """Alpaca paper or live trading; credentials are always required."""

    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, paper: bool = True):
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API key and secret are required; use PaperBroker for local simulation")
        self.paper = paper
        self.base_url = "https://paper-api.alpaca.markets/v2" if paper else "https://api.alpaca.markets/v2"
        self._headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json",
        }
        self.submitted_orders: List[Dict[str, Any]] = []

    @property
    def cash(self) -> float:
        return float(self.get_account()["cash"])

    @property
    def positions(self) -> Dict[str, float]:
        response = requests.get(f"{self.base_url}/positions", headers=self._headers, timeout=10, allow_redirects=False)
        response.raise_for_status()
        return {item["symbol"].lower(): float(item["qty"]) for item in response.json()}

    def get_account(self) -> Dict[str, Any]:
        response = requests.get(f"{self.base_url}/account", headers=self._headers, timeout=10, allow_redirects=False)
        response.raise_for_status()
        return response.json()

    def submit_order(self, symbol: str, qty: float, side: str, order_type: str = "market",
                     time_in_force: str = "day", limit_price: Optional[float] = None) -> Dict[str, Any]:
        quantity = _positive(qty, "quantity")
        if side not in ("buy", "sell") or order_type not in ("market", "limit"):
            raise ValueError("Unsupported Alpaca order side or type")
        payload: Dict[str, Any] = {
            "symbol": symbol.upper(), "qty": str(quantity), "side": side,
            "type": order_type, "time_in_force": time_in_force,
        }
        if order_type == "limit":
            payload["limit_price"] = str(_positive(limit_price, "limit_price"))
        response = requests.post(f"{self.base_url}/orders", json=payload, headers=self._headers,
                                 timeout=10, allow_redirects=False)
        response.raise_for_status()
        return response.json()

    def get_order(self, order_id: Any) -> Dict[str, Any]:
        response = requests.get(f"{self.base_url}/orders/{_order_id(order_id)}", headers=self._headers,
                                timeout=10, allow_redirects=False)
        response.raise_for_status()
        return response.json()

    def cancel_order(self, order_id: Any) -> None:
        response = requests.delete(f"{self.base_url}/orders/{_order_id(order_id)}", headers=self._headers,
                                   timeout=10, allow_redirects=False)
        response.raise_for_status()

    def execute(self, intents: Sequence[OrderIntent], current_prices: Optional[Dict[str, float]] = None,
                max_slippage_pct: Optional[float] = None) -> List[Fill]:
        """Submit orders and return only fills confirmed in submission responses.

        Use get_order for later fills. A timeout on submission has an unknown outcome;
        callers must reconcile orders before submitting the same intent again.
        """
        fills: List[Fill] = []
        if max_slippage_pct is not None:
            raise NotImplementedError("Broker-side slippage limits are not supported; use limit orders")
        self.submitted_orders = []
        for intent in intents:
            if intent.side not in (Side.BUY, Side.SELL, Side.SHORT_SELL, Side.BUY_TO_COVER):
                raise ValueError("Unsupported order side")
            quantity = _intent_quantity(intent, current_prices, whole_shares=False)
            side = "buy" if intent.side in (Side.BUY, Side.BUY_TO_COVER) else "sell"
            order = self.submit_order(intent.ticker, quantity, side,
                                      order_type="limit" if intent.limit is not None else "market",
                                      limit_price=intent.limit)
            self.submitted_orders.append(order)
            fill = _fill(order, intent, "filled_qty", "filled_avg_price")
            if fill is not None:
                fills.append(fill)
        return fills

    def execute_plan(self, plan: TradePlan) -> List[Fill]:
        raise TypeError("TradePlan is a journal record; execute OrderIntent objects instead")


class TradierBrokerAdapter(Broker):
    """Tradier sandbox or live trading; credentials and account ID are required."""

    def __init__(self, access_token: Optional[str] = None, account_id: Optional[str] = None, sandbox: bool = True):
        self.access_token = access_token or os.getenv("TRADIER_ACCESS_TOKEN")
        self.account_id = account_id or os.getenv("TRADIER_ACCOUNT_ID")
        if not self.access_token or not self.account_id:
            raise ValueError("Tradier token and account ID are required; use PaperBroker for local simulation")
        self.sandbox = sandbox
        self.base_url = "https://sandbox.tradier.com/v1" if sandbox else "https://api.tradier.com/v1"
        self._headers = {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}
        self._account_path = f"{self.base_url}/accounts/{quote(self.account_id, safe='')}"
        self.submitted_orders: List[Dict[str, Any]] = []

    @property
    def cash(self) -> float:
        payload = self.get_balances()
        balance = payload.get("balance", payload)
        balances = balance.get("balances", balance)
        cash = balance.get("cash")
        if isinstance(cash, dict) and "cash_available" in cash:
            return float(cash["cash_available"])
        return float(balances["total_cash"])

    @property
    def positions(self) -> Dict[str, float]:
        response = requests.get(f"{self._account_path}/positions", headers=self._headers,
                                timeout=10, allow_redirects=False)
        response.raise_for_status()
        positions = response.json().get("positions") or {}
        items = positions.get("position") or []
        if isinstance(items, dict):
            items = [items]
        return {item["symbol"].lower(): float(item["quantity"]) for item in items}

    def get_balances(self) -> Dict[str, Any]:
        response = requests.get(f"{self._account_path}/balances", headers=self._headers,
                                timeout=10, allow_redirects=False)
        response.raise_for_status()
        return response.json()

    def _submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(f"{self._account_path}/orders", data=payload, headers=self._headers,
                                 timeout=10, allow_redirects=False)
        response.raise_for_status()
        order = response.json().get("order")
        if not isinstance(order, dict) or not order.get("id") or order.get("status") == "error":
            raise ValueError("Tradier did not accept the order")
        return order

    def submit_order(self, symbol: str, quantity: int, side: str, order_type: str = "market",
                     duration: str = "day", price: Optional[float] = None) -> Dict[str, Any]:
        if side not in ("buy", "sell", "sell_short", "buy_to_cover"):
            raise ValueError("Unsupported Tradier equity side")
        if order_type not in ("market", "limit"):
            raise ValueError("Unsupported Tradier equity order type")
        quantity = _whole_quantity(quantity, "Tradier equity quantity")
        payload: Dict[str, Any] = {"class": "equity", "symbol": symbol.upper(), "side": side,
                                   "quantity": str(quantity), "type": order_type, "duration": duration}
        if order_type == "limit":
            payload["price"] = str(_positive(price, "price"))
        return self._submit(payload)

    def submit_option_order(self, symbol: str, option_symbol: str, side: str, quantity: int,
                            order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        if side not in ("buy_to_open", "buy_to_close", "sell_to_open", "sell_to_close"):
            raise ValueError("Unsupported Tradier option side")
        if order_type not in ("market", "limit"):
            raise ValueError("Unsupported Tradier option order type")
        quantity = _whole_quantity(quantity, "Option quantity")
        payload: Dict[str, Any] = {"class": "option", "symbol": symbol.upper(), "option_symbol": option_symbol,
                                   "side": side, "quantity": str(quantity), "type": order_type, "duration": "day"}
        if order_type == "limit":
            payload["price"] = str(_positive(price, "price"))
        return self._submit(payload)

    def get_order(self, order_id: Any) -> Dict[str, Any]:
        response = requests.get(f"{self._account_path}/orders/{_order_id(order_id)}", headers=self._headers,
                                timeout=10, allow_redirects=False)
        response.raise_for_status()
        return response.json()["order"]

    def cancel_order(self, order_id: Any) -> None:
        response = requests.delete(f"{self._account_path}/orders/{_order_id(order_id)}", headers=self._headers,
                                   timeout=10, allow_redirects=False)
        response.raise_for_status()

    def execute(self, intents: Sequence[OrderIntent], current_prices: Optional[Dict[str, float]] = None,
                max_slippage_pct: Optional[float] = None) -> List[Fill]:
        fills: List[Fill] = []
        if max_slippage_pct is not None:
            raise NotImplementedError("Broker-side slippage limits are not supported; use limit orders")
        self.submitted_orders = []
        sides = {Side.BUY: "buy", Side.SELL: "sell", Side.SHORT_SELL: "sell_short",
                 Side.BUY_TO_COVER: "buy_to_cover"}
        for intent in intents:
            quantity = int(_intent_quantity(intent, current_prices, whole_shares=True))
            accepted = self.submit_order(intent.ticker, quantity, sides[intent.side],
                                         order_type="limit" if intent.limit is not None else "market",
                                         price=intent.limit)
            self.submitted_orders.append(accepted)
            order = self.get_order(accepted["id"])
            fill = _fill(order, intent, "exec_quantity", "avg_fill_price")
            if fill is not None:
                fills.append(fill)
        return fills

    def execute_plan(self, plan: TradePlan) -> List[Fill]:
        raise TypeError("TradePlan is a journal record; execute OrderIntent objects instead")
