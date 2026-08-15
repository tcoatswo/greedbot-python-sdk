"""
Example Earnings Radar & Volatility Harvesting
----------------------------------------------
Scans upcoming earnings across 90-day horizons, computes event-dated options
expected moves, and identifies volatility harvest opportunities.
"""

from greedbot import GreedBotClient, EarningsRadarStrategy, VolatilityHarvestEngine

def main():
    client = GreedBotClient()

    print("⚡ Scanning 90-Day Earnings Radar...")
    radar_strat = EarningsRadarStrategy(target_window="next-7-bd", max_candidates=5)

    try:
        candidates = radar_strat.scan_radar(client)
        print(f"\nTop Earnings Candidates (Horizon: next-7-bd):")
        for c in candidates:
            print(f"  • {c['ticker']}: Reports on {c['report_date']} | Implied Move: ±{c['expected_move_pct']}% | Status: {c['status']}")

        # Volatility Harvesting Scan
        print("\n⚡ Scanning High-IV Volatility Harvest Setups (Iron Condor Candidates):")
        vol_engine = VolatilityHarvestEngine(client)
        harvests = vol_engine.scan_harvest()
        for h in harvests[:5]:
            print(f"  • {h['ticker']}: IV {h['implied_volatility']}% | Action: {h['action']}")

    except Exception as e:
        print(f"Earnings scan failed: {e}")

if __name__ == "__main__":
    main()
