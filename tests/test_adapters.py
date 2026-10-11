"""Broker submission must not be confused with confirmed execution."""

import unittest
from unittest.mock import MagicMock, patch

from greedbot.adapters import AlpacaBrokerAdapter, TradierBrokerAdapter
from greedbot.models import OrderIntent, Side


def response(body):
    result = MagicMock()
    result.json.return_value = body
    result.status_code = 200
    return result


class TestAlpacaOrders(unittest.TestCase):
    def setUp(self):
        self.adapter = AlpacaBrokerAdapter(api_key="key", secret_key="secret")
        self.intent = OrderIntent(ticker="SPY", side=Side.BUY, dollars=1000, limit=100)

    @patch("greedbot.adapters.requests.post")
    def test_accepted_order_is_not_a_fill(self, post):
        post.return_value = response({"id": "123", "status": "new", "filled_qty": "0"})
        self.assertEqual(self.adapter.execute([self.intent]), [])
        self.assertEqual(post.call_args.kwargs["json"]["qty"], "10.0")
        self.assertFalse(post.call_args.kwargs["allow_redirects"])

    @patch("greedbot.adapters.requests.post")
    def test_partial_fill_uses_actual_quantity_and_price(self, post):
        post.return_value = response({"id": "123", "status": "partially_filled",
                                      "filled_qty": "3", "filled_avg_price": "99.75"})
        fills = self.adapter.execute([self.intent])
        self.assertEqual(len(fills), 1)
        self.assertEqual((fills[0].quantity, fills[0].price), (3, 99.75))

    @patch("greedbot.adapters.requests.post")
    def test_no_default_price_for_market_order(self, post):
        market_intent = OrderIntent(ticker="SPY", side=Side.BUY, dollars=1000)
        with self.assertRaises(ValueError):
            self.adapter.execute([market_intent])
        post.assert_not_called()

    @patch("greedbot.adapters.requests.get")
    @patch("greedbot.adapters.requests.delete")
    def test_lookup_and_cancel(self, delete, get):
        get.return_value = response({"id": "123", "status": "filled"})
        delete.return_value = response({})
        self.assertEqual(self.adapter.get_order("123")["status"], "filled")
        self.adapter.cancel_order("123")
        self.assertTrue(get.call_args.args[0].endswith("/orders/123"))
        self.assertTrue(delete.call_args.args[0].endswith("/orders/123"))
        with self.assertRaises(ValueError):
            self.adapter.cancel_order("../account")


class TestTradierOrders(unittest.TestCase):
    def setUp(self):
        self.adapter = TradierBrokerAdapter(access_token="token", account_id="ABC")
        self.intent = OrderIntent(ticker="SPY", side=Side.SHORT_SELL, dollars=1000, limit=100)

    @patch("greedbot.adapters.requests.get")
    @patch("greedbot.adapters.requests.post")
    def test_submits_equity_and_reads_confirmed_partial_fill(self, post, get):
        post.return_value = response({"order": {"id": 42, "status": "ok"}})
        get.return_value = response({"order": {"id": 42, "status": "partially_filled",
                                               "exec_quantity": 4, "avg_fill_price": 100.5}})
        fills = self.adapter.execute([self.intent])
        self.assertEqual((fills[0].quantity, fills[0].price), (4, 100.5))
        self.assertEqual(post.call_args.kwargs["data"]["side"], "sell_short")
        self.assertEqual(post.call_args.kwargs["data"]["class"], "equity")

    @patch("greedbot.adapters.requests.get")
    @patch("greedbot.adapters.requests.post")
    def test_pending_order_has_no_fill(self, post, get):
        post.return_value = response({"order": {"id": 42, "status": "ok"}})
        get.return_value = response({"order": {"id": 42, "status": "open", "exec_quantity": 0}})
        self.assertEqual(self.adapter.execute([self.intent]), [])

    @patch("greedbot.adapters.requests.post")
    def test_rejected_submission_is_not_a_fill(self, post):
        post.return_value = response({"order": {"status": "error"}})
        with self.assertRaises(ValueError):
            self.adapter.execute([self.intent])


if __name__ == "__main__":
    unittest.main()
