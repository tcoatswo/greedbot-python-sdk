"""
Example Webhook Alerts & Notification Dispatcher
------------------------------------------------
Demonstrates formatting and dispatching trade alerts, daily bake announcements,
and risk notifications to Discord, Slack, Telegram, and generic webhooks.
"""

from greedbot import OrderIntent, Side, SlotInfo, WebhookDispatcher

def main():
    print("⚡ Testing Multi-Channel Webhook Dispatcher...")

    # Initialize dispatcher (reads webhook URLs from environment or constructor)
    dispatcher = WebhookDispatcher()

    # 1. Dispatch Trade Alert
    intent = OrderIntent(ticker="NVDA", side=Side.BUY, dollars=10000.0, limit=124.50)
    print("\n1. Dispatching Trade Intent Alert:")
    print(f"  • {intent.side.value} {intent.ticker} ${intent.dollars:,.2f} @ Limit ${intent.limit:.2f}")
    results = dispatcher.send_trade_alert(
        intent=intent,
        strategy_name="TrendFollowingStrategy",
        current_price=124.20,
        rationale="10/50 SMA Bullish Golden Cross with accelerating momentum",
    )
    print(f"  Dispatch Results: {results or 'Configured for live webhooks (Set DISCORD_WEBHOOK_URL / SLACK_WEBHOOK_URL)'}")

    # 2. Dispatch Daily Bake Alert
    print("\n2. Dispatching Daily Bake Publication Alert:")
    slot = SlotInfo(
        year=2026,
        refresh_n=140,
        interval="day",
        quote_type="equity",
        effective_at="2026-07-25T00:00:00Z",
        effective_until="2026-07-28T00:00:00Z",
    )
    bake_res = dispatcher.send_bake_alert(hub_name="ideas", slot=slot)
    print(f"  Bake Alert Results: {bake_res or 'Logged to stdout'}")

if __name__ == "__main__":
    main()
