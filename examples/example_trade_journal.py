"""
Example Trade Journal Management (Unmetered)
--------------------------------------------
Demonstrates logging planned trades, tracking status, opening fills,
and recording closed trades with P&L on GreedBot's free /api/v1/log system.
"""

from greedbot import GreedBotClient, TradeJournal

def main():
    client = GreedBotClient()
    journal = TradeJournal(client)

    print("⚡ Recording Trade Plan to GreedBot Journal (Unmetered)...")

    try:
        # 1. Record a planned trade before entry
        plan_id = journal.record_plan(
            ticker="NVDA",
            direction="long",
            entry=125.0,
            stop=118.0,
            target=140.0,
            risk_amount=700.0,
            thesis="Breakout above resistance with strong momentum",
            tags=["breakout", "tech", "momentum"],
        )
        print(f"Recorded Plan ID: {plan_id}")

        # 2. Simulate opening the trade on fill
        print("\nOpening trade plan...")
        open_res = journal.open_trade(plan_id=plan_id, entry_price=125.20, shares=100)
        print(f"Open Status: {open_res}")

        # 3. Simulate closing the trade at target
        print("\nClosing trade plan at target...")
        close_res = journal.close_trade(
            plan_id=plan_id,
            exit_price=140.50,
            net_pnl=1530.0,
            realized_r=2.18,
            exit_reason="target",
            exit_notes="Clean exit at upper resistance band",
        )
        print(f"Close Status: {close_res}")

        # 4. List recent active/closed plans
        plans = journal.get_active_plans()
        print(f"\nActive Plans in Journal: {len(plans)}")

    except Exception as e:
        print(f"Journal operation failed: {e}")

if __name__ == "__main__":
    main()
