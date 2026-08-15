"""
Multi-Channel Webhook Alerts & Notification Dispatcher
------------------------------------------------------
Dispatches real-time trade signals, fill executions, bake slot announcements,
and risk limit breach alerts to Discord, Slack, Telegram, and generic HTTP endpoints.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional
import requests

from .models import OrderIntent, SlotInfo

logger = logging.getLogger("greedbot.alerts")


class WebhookDispatcher:
    """
    Multi-channel alert dispatcher for trading bots.
    """

    def __init__(
        self,
        discord_url: Optional[str] = None,
        slack_url: Optional[str] = None,
        telegram_bot_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        generic_url: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.discord_url = discord_url or os.environ.get("DISCORD_WEBHOOK_URL")
        self.slack_url = slack_url or os.environ.get("SLACK_WEBHOOK_URL")
        self.telegram_bot_token = telegram_bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self.generic_url = generic_url or os.environ.get("GENERIC_WEBHOOK_URL")
        self.timeout = timeout

    def _post_json(self, url: str, payload: Dict[str, Any]) -> bool:
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Failed to dispatch webhook to {url}: {e}")
            return False

    def send_trade_alert(
        self,
        intent: OrderIntent,
        strategy_name: str = "GreedBot Strategy",
        current_price: Optional[float] = None,
        rationale: Optional[str] = None,
    ) -> Dict[str, bool]:
        """Dispatches an executable trade intent alert."""
        results: Dict[str, bool] = {}
        price_str = f" @ ${current_price:.2f}" if current_price else ""
        title = f"⚡ Trade Alert: {intent.side.value.upper()} {intent.ticker.upper()}{price_str}"
        body = f"Strategy: {strategy_name}\nTarget Dollars: ${intent.dollars:,.2f}\n"
        if intent.limit:
            body += f"Limit Price: ${intent.limit:.2f}\n"
        if rationale:
            body += f"Rationale: {rationale}\n"

        # 1. Discord Embed
        if self.discord_url:
            color = 0x00FF00 if "BUY" in intent.side.value.upper() else 0xFF0000
            payload = {
                "embeds": [{
                    "title": title,
                    "description": body,
                    "color": color,
                    "footer": {"text": "GreedBot Trading SDK"},
                }]
            }
            results["discord"] = self._post_json(self.discord_url, payload)

        # 2. Slack Block
        if self.slack_url:
            payload = {
                "text": f"*{title}*\n```{body}```"
            }
            results["slack"] = self._post_json(self.slack_url, payload)

        # 3. Telegram Message
        if self.telegram_bot_token and self.telegram_chat_id:
            tg_url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": f"*{title}*\n\n{body}",
                "parse_mode": "Markdown",
            }
            results["telegram"] = self._post_json(tg_url, payload)

        # 4. Generic Webhook
        if self.generic_url:
            payload = {
                "event": "TRADE_ALERT",
                "ticker": intent.ticker,
                "side": intent.side.value,
                "dollars": intent.dollars,
                "limit": intent.limit,
                "strategy": strategy_name,
                "rationale": rationale,
            }
            results["generic"] = self._post_json(self.generic_url, payload)

        return results

    def send_bake_alert(self, hub_name: str, slot: SlotInfo) -> Dict[str, bool]:
        """Dispatches notification that a new daily/weekly bake slot is published."""
        results: Dict[str, bool] = {}
        title = f"🍞 New Bake Published: Hub '{hub_name}'"
        body = f"Slot: {slot.year}/{slot.refresh_n} ({slot.interval})\nEffective: {slot.effective_at} -> {slot.effective_until}"

        if self.discord_url:
            results["discord"] = self._post_json(self.discord_url, {"content": f"**{title}**\n{body}"})
        if self.slack_url:
            results["slack"] = self._post_json(self.slack_url, {"text": f"*{title}*\n{body}"})
        if self.generic_url:
            results["generic"] = self._post_json(self.generic_url, {"event": "NEW_BAKE", "hub": hub_name, "slot": vars(slot)})

        return results

    def send_risk_alert(self, message: str, severity: str = "WARNING") -> Dict[str, bool]:
        """Dispatches a risk limit breach or drawdown alert."""
        results: Dict[str, bool] = {}
        title = f"🚨 [{severity.upper()}] Risk Limit Alert"
        if self.discord_url:
            results["discord"] = self._post_json(self.discord_url, {"content": f"**{title}**\n{message}"})
        if self.slack_url:
            results["slack"] = self._post_json(self.slack_url, {"text": f"*{title}*\n{message}"})
        return results
