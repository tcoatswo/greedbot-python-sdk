"""
GreedBot SDK Quickstart & Usage Examples
----------------------------------------
Run this script to test all core features of the GreedBot Python SDK.

Usage:
    export GREEDBOT_API_KEY="your_api_key_here"  # Optional if using public demo endpoints
    python examples/quickstart.py
"""

import os
import json
from greedbot import GreedBotClient
from greedbot.strategies import (
    OptionKellyEngine,
    QualitativeOverlayEngine,
    MacroRegimeMatrix,
    VolatilityHarvestEngine,
    SectorSpilloverArb,
)

def main():
    print("⚡ Initializing GreedBot Client...")
    client = GreedBotClient(api_key=os.environ.get("GREEDBOT_API_KEY", ""))

    print("\n1️⃣ Fetching Momentum Leaderboard (Pizza Index)...")
    try:
        pizza = client.get_pizza(["NVDA", "TSLA", "MSFT", "AAPL"])
        print(f"Top Tickers: {json.dumps(pizza, indent=2)}")
    except Exception as e:
        print(f"[-] Note: {e}")

    print("\n2️⃣ Running Qualitative Catalyst vs Expected Move Asymmetry...")
    qual = QualitativeOverlayEngine(client)
    nvda_signal = qual.evaluate_divergence(ticker="NVDA", qualitative_sentiment=0.85)
    print(f"NVDA Analysis: {json.dumps(nvda_signal, indent=2)}")

    print("\n3️⃣ Sizing Trade via Non-Linear Kelly Option Convexity...")
    kelly = OptionKellyEngine(client)
    sizing = kelly.calculate_sizing(ticker="NVDA", portfolio_size=25000.0)
    print(f"NVDA Kelly Sizing: {json.dumps(sizing, indent=2)}")

    print("\n4️⃣ Macro Dynamic Regime-Switching Matrix...")
    macro = MacroRegimeMatrix(client)
    weights = macro.get_portfolio_weights(tickers=["NVDA", "MSFT", "AMZN", "AAPL"], portfolio_capital=100000.0)
    print(f"Macro Allocations: {json.dumps(weights, indent=2)}")

    print("\n✅ Quickstart demonstration completed successfully!")

if __name__ == "__main__":
    main()
