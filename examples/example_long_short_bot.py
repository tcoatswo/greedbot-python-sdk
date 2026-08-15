"""
Example Long/Short Bot: Dollar-Neutral Sector Pairs
---------------------------------------------------
Ranks 11 US Sector SPDR ETFs using /pizza, goes Long the top-2 sectors and
Short the bottom-2 sectors with dollar-neutral sizing and strict risk limits.
"""

from greedbot import GreedBotClient, SectorLongShortStrategy, PaperBroker

def main():
    client = GreedBotClient()
    capital_usd = 10000.0

    print("⚡ Running Sector Dollar-Neutral Long/Short Bot...")
    strategy = SectorLongShortStrategy(
        gross_fraction=0.20,
        per_name_cap=0.05,
        n_long=2,
        n_short=2,
    )

    try:
        result = strategy.run(client, capital_usd=capital_usd)
        print(f"\nTarget Allocations ($ {capital_usd:,.2f}):")
        for ticker, dollars in result.target_dollars.items():
            print(f"  • {ticker.upper()}: ${dollars:,.2f}")

        print("\nTyped Order Intents (Short legs typed as ShortSell):")
        for intent in result.intents:
            print(f"  • {intent.side.value} {intent.ticker.upper()} ${intent.dollars:,.2f}")

        # PaperBroker simulation
        broker = PaperBroker(cash_usd=capital_usd, fee_per_fill=0.50)
        # Mock sector ETF prices
        prices = {
            "xlk": 220.0, "xlc": 85.0, "xlf": 45.0, "xle": 90.0,
            "xlv": 140.0, "xly": 190.0, "xlp": 75.0, "xlu": 65.0,
            "xlb": 88.0, "xlre": 40.0, "xli": 120.0
        }
        fills = broker.execute(result.intents, prices=prices)

        print(f"\nPaperBroker Fills Executed ({len(fills)} fills):")
        for f in fills:
            print(f"  • {f.side.value} {f.quantity:.2f} shs of {f.ticker.upper()} @ ${f.price:.2f}")

        print(f"Resulting Paper Positions: {broker.positions}")
        print(f"Paper Cash: ${broker.cash:,.2f}")

    except Exception as e:
        print(f"Strategy execution failed: {e}")

if __name__ == "__main__":
    main()
