"""
Example Macro Dynamic Regime Allocation
---------------------------------------
Fetches macro cycle regime from /hub/macro/latest and dynamically weights
multi-asset allocations across Equities, Tech Growth, Gold, Treasuries, and Commodities.
"""

from greedbot import GreedBotClient, MacroRegimeMatrix

def main():
    client = GreedBotClient()
    capital_usd = 100000.0

    print("⚡ Running Macro Dynamic Regime-Switching Matrix...")
    macro_strat = MacroRegimeMatrix()

    try:
        allocations = macro_strat.get_regime_allocations(client, capital_usd=capital_usd)
        print(f"\nActive Regime: {allocations['active_regime']}")
        print(f"Macro Outlook: {allocations['macro_opinion']}")
        print(f"\nPortfolio Allocations ($ {capital_usd:,.2f}):")
        for sym, data in allocations["allocations"].items():
            print(f"  • {sym} ({data['asset_class']}): {data['target_weight_pct']}% -> ${data['target_dollars']:,.2f}")

    except Exception as e:
        print(f"Macro regime allocation failed: {e}")

if __name__ == "__main__":
    main()
