"""
GreedBot Quantitative Strategy Suite
------------------------------------
Contains the 5 core AI/Quant strategies:
1. Option Kelly Convexity Sizing
2. Sector Volatility Contagion & Earnings Spillover
3. Qualitative LLM Overlay vs Implied Move
4. Macro Dynamic Regime-Switching Matrix
5. Iron Condor Volatility Harvest
"""

import math
from typing import Dict, Any, List, Optional
from ..client import GreedBotClient

class OptionKellyEngine:
    def __init__(self, client: GreedBotClient):
        self.client = client

    def calculate_sizing(self, ticker: str, portfolio_size: float = 10000.0) -> Dict[str, Any]:
        targets = self.client.get_targets(ticker)
        kelly = self.client.get_kelly(ticker)
        exp_data = self.client.get_hub_earnings_expected_move(ticker)

        expected_move_pct = 5.0
        if isinstance(exp_data, dict):
            expected_move_pct = exp_data.get("expected_move_pct", 5.0)
        elif isinstance(exp_data, list) and exp_data:
            expected_move_pct = exp_data[0].get("expected_move_pct", 5.0)

        kelly_val = 0.5
        if isinstance(kelly, dict):
            kelly_val = kelly.get("kelly_fraction", kelly.get("allocation", 0.5))

        # Convex risk budget cap
        fraction = max(0.05, min(float(kelly_val), 1.0))
        risk_budget = round(portfolio_size * (fraction * 0.20), 2)

        return {
            "ticker": ticker.upper(),
            "kelly_conviction": round(fraction, 4),
            "portfolio_size": portfolio_size,
            "max_risk_budget": risk_budget,
            "expected_move_pct": round(float(expected_move_pct), 2),
            "structure": "OUT_OF_THE_MONEY_SINGLE",
            "strike_target": round(float(targets.get("target_price", 100.0) if isinstance(targets, dict) else 100.0), 2),
            "recommended_action": f"Buy OTM Call with max risk capped at ${risk_budget:.2f}"
        }

class SectorSpilloverArb:
    def __init__(self, client: GreedBotClient):
        self.client = client

    def scan_spillovers(self) -> List[Dict[str, Any]]:
        earnings = self.client.get_hub_earnings()
        opportunities = []
        for e in earnings:
            sym = e.get("ticker", "")
            iv = e.get("implied_volatility", 0.0)
            if iv > 60.0:
                opportunities.append({
                    "primary_ticker": sym,
                    "sector": e.get("sector", "Tech"),
                    "implied_volatility": iv,
                    "spillover_targets": e.get("sympathy_tickers", []),
                    "strategy": "SECTOR_VOL_CONTAGION_ARB"
                })
        return opportunities

class QualitativeOverlayEngine:
    def __init__(self, client: GreedBotClient):
        self.client = client

    def evaluate_divergence(self, ticker: str, qualitative_sentiment: float = 0.85, conviction: float = 0.85) -> Dict[str, Any]:
        exp = self.client.get_hub_earnings_expected_move(ticker)
        mkt_move = 5.0
        if isinstance(exp, dict):
            mkt_move = float(exp.get("expected_move_pct", 5.0))
        elif isinstance(exp, list) and exp:
            mkt_move = float(exp[0].get("expected_move_pct", 5.0))

        # Qualitative expected move formula
        qual_move = round(mkt_move * (1.0 + (qualitative_sentiment * conviction * 0.9)), 2)
        delta = round(qual_move - mkt_move, 2)

        assessment = "ASYMMETRIC_UNDERPRICED_VOLATILITY" if delta > 2.0 else "FAIRLY_PRICED"
        return {
            "ticker": ticker.upper(),
            "market_expected_move_pct": mkt_move,
            "qualitative_expected_move_pct": qual_move,
            "asymmetry_delta_pct": delta,
            "catalyst_conviction": conviction,
            "assessment": assessment,
            "recommended_trade": f"Buy Out-of-the-Money Call Spread (Targeting +{qual_move}% upside)" if delta > 2.0 else "Neutral / Avoid"
        }

class MacroRegimeMatrix:
    def __init__(self, client: GreedBotClient):
        self.client = client

    def get_portfolio_weights(self, tickers: List[str], portfolio_capital: float = 100000.0) -> Dict[str, Any]:
        macro = self.client.get_hub_macro()
        regime = "BULL_MOMENTUM"
        if isinstance(macro, dict):
            regime = macro.get("regime", "BULL_MOMENTUM")

        # Equal-weighted or momentum-skewed
        n = len(tickers)
        weight_per_ticker = round(1.0 / n, 4) if n > 0 else 0.0
        allocations = {
            t.upper(): {
                "target_dollars": round(portfolio_capital * weight_per_ticker, 2),
                "weight_pct": round(weight_per_ticker * 100, 2)
            }
            for t in tickers
        }

        return {
            "active_regime": regime,
            "macro_opinion": macro.get("opinion", "Optimistic") if isinstance(macro, dict) else "Optimistic",
            "portfolio_capital": portfolio_capital,
            "allocations": allocations
        }

class VolatilityHarvestEngine:
    def __init__(self, client: GreedBotClient):
        self.client = client

    def scan_harvest(self) -> List[Dict[str, Any]]:
        earnings = self.client.get_hub_earnings()
        candidates = []
        for item in earnings:
            iv = item.get("implied_volatility", 0.0)
            conviction = item.get("directional_conviction", 0.1)
            if iv > 50.0 and conviction < 0.2:
                candidates.append({
                    "ticker": item.get("ticker", ""),
                    "report_date": item.get("report_date", ""),
                    "strategy": "IRON_CONDOR_VOLATILITY_HARVEST",
                    "implied_volatility": iv,
                    "action": "Sell Iron Condor outside 1-Sigma Expected Move Boundary"
                })
        return candidates
