"""
Example Solo Bot: Single-Ticker Tactical IN/FLAT
------------------------------------------------
Tactical single-asset bot on NVDA. Driven by /targets aggregated algo score.
Enforces MIN_SIGNAL filter to reject noise and toggle cleanly between IN and FLAT.
"""

from greedbot import GreedBotClient, SoloTacticalStrategy, PaperBroker

def main():
    client = GreedBotClient()
    ticker = "NVDA"
    capital_usd = 10000.0

    print(f"⚡ Running Solo Tactical Bot for {ticker}...")
    strategy = SoloTacticalStrategy(ticker=ticker, min_signal=0.05)

    try:
        result = strategy.run(client, capital_usd=capital_usd)
        print(f"\nTarget Allocation ($ {capital_usd:,.2f}):")
        for t, dollars in result.target_dollars.items():
            status = "IN (100% Invested)" if dollars > 0 else "FLAT (100% Cash)"
            print(f"  • {t.upper()}: ${dollars:,.2f} -> {status}")

        if result.intents:
            print("\nOrder Intent:")
            for intent in result.intents:
                print(f"  • {intent.side.value} {intent.ticker.upper()} ${intent.dollars:,.2f}")
        else:
            print("\nNo order intent generated (Strategy is FLAT/Cash).")

    except Exception as e:
        print(f"Strategy execution failed: {e}")

if __name__ == "__main__":
    main()
