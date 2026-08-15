"""
Example ETF Bot: 80/20 Risk-Parity / Kelly Barbell
--------------------------------------------------
Constructs an 80/20 barbell over low-cost ETF assets (SCHP, VGLT, VT, PDBC, IAU).
Calls /parity + /kelly, blends weights, and generates /rebalance share orders.
"""

from greedbot import GreedBotClient, ETFBarbellStrategy, PaperBroker

def main():
    client = GreedBotClient()
    capital_usd = 10000.0

    print("⚡ Running ETF Barbell 80/20 Strategy...")
    strategy = ETFBarbellStrategy(
        assets=["schp", "vglt", "vt", "pdbc", "iau"],
        barbell_parity=0.80,
        barbell_kelly=0.20,
        kelly_fraction=0.50,
        no_shorting=True,
    )

    try:
        result = strategy.run(client, capital_usd=capital_usd)
        print(f"\nTarget Dollar Holdings ($ {capital_usd:,.2f}):")
        for ticker, dollars in result.target_dollars.items():
            print(f"  • {ticker.upper()}: ${dollars:,.2f}")

        print(f"\nGenerated {len(result.intents)} Executable Order Intents:")
        for intent in result.intents:
            print(f"  • {intent.side.value} {intent.ticker.upper()}: ${intent.dollars:,.2f}")

        # Simulate execution with PaperBroker using mock bar open prices
        broker = PaperBroker(cash_usd=capital_usd, fee_per_fill=1.0)
        prices = {"schp": 50.0, "vglt": 60.0, "vt": 110.0, "pdbc": 15.0, "iau": 45.0}
        fills = broker.execute(result.intents, prices=prices)

        print(f"\nPaperBroker Fills Executed ({len(fills)} fills):")
        for f in fills:
            print(f"  • Filled {f.quantity:.2f} shares of {f.ticker.upper()} @ ${f.price:.2f} (Fee: ${f.fees:.2f})")
        print(f"Remaining Cash: ${broker.cash:,.2f}")

    except Exception as e:
        print(f"Strategy execution failed: {e}")

if __name__ == "__main__":
    main()
