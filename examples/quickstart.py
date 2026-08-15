"""
GreedBot Python SDK - Quickstart
--------------------------------
Demonstrates core client methods, receipt/baked computation, hub snapshots,
bot fleet inspection, and unmetered health/spend endpoints.
"""

import os
from greedbot import GreedBotClient, SlotInfo

def main():
    # Initialize client (uses GREEDBOT_API_KEY from env or default)
    client = GreedBotClient()
    print(f"Initialized client: {client}")

    # 1. Health check (Free)
    try:
        ping_res = client.ping()
        print(f"Health check: {ping_res}")
    except Exception as e:
        print(f"Ping failed: {e}")

    # 2. Spend & Usage check (Free)
    try:
        usage = client.get_usage()
        print(f"Usage summary: Key {usage.get('key', {}).get('api_key_id')} - Total events: {usage.get('key', {}).get('total_events')}")
    except Exception as e:
        print(f"Usage check: {e}")

    # 3. Macro Regime Snapshot
    try:
        macro = client.get_hub_macro()
        print(f"Active Macro Regime: {macro.get('regime', 'N/A')}")
    except Exception as e:
        print(f"Macro hub fetch: {e}")

    # 4. Earnings Expected Move
    try:
        exp = client.get_hub_earnings_expected_move(ticker="NVDA")
        print(f"NVDA Options Market Expected Move: ±{exp.get('expected_move_pct')}%")
    except Exception as e:
        print(f"Expected move fetch: {e}")

    # 5. Currency Check Demonstration
    try:
        ideas = client.get_hub_when_current("ideas", max_attempts=1, retry_secs=5)
        slot = SlotInfo.from_payload(ideas)
        if slot:
            print(f"Current Ideas Slot: {slot.year}/{slot.refresh_n} (Effective: {slot.effective_at} -> {slot.effective_until})")
    except Exception as e:
        print(f"Slot freshness check: {e}")

if __name__ == "__main__":
    main()
