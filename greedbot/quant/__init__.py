"""
GreedBot Quantitative & Risk Management Toolkit
-----------------------------------------------
Mathematical models for options pricing, dealer positioning, spreads, risk controls, and portfolio optimization:
- Option Greeks & Implied Volatility (Native Rust Accelerated Engine)
- Market-Maker Gamma Exposure (GEX) & Expiration Max Pain
- Multi-Leg Options Spread Engine (Iron Condor, Verticals, Straddles, Strangles)
- Monte Carlo Portfolio Stress-Testing & CVaR (Jump-Diffusion)
- Kelly Position Sizing & Merton Jump Kelly
- Mean-Variance Portfolio Optimization (Markowitz GMV & Tangency)
"""

from .kelly import KellyPositionSizer
from .jump_kelly import MertonJumpKellySizer, compute_jump_kelly
from .markowitz import MeanVarianceOptimizer
from .rust_engine import (
    OptionGreeks,
    calculate_greeks,
    solve_iv,
    generate_volatility_surface,
    is_rust_accelerated,
)
from .gex import GEXEngine, GEXResult, OptionContractData
from .spreads import (
    OptionLeg,
    OptionSpread,
    IronCondor,
    VerticalSpread,
    Straddle,
    Strangle,
    CompositeSpreadGreeks,
)
from .monte_carlo import MonteCarloEngine, MonteCarloResult

__all__ = [
    # Position Sizing & Portfolio Optimization
    "KellyPositionSizer",
    "MertonJumpKellySizer",
    "compute_jump_kelly",
    "MeanVarianceOptimizer",
    # Rust Options Greeks & Volatility
    "OptionGreeks",
    "calculate_greeks",
    "solve_iv",
    "generate_volatility_surface",
    "is_rust_accelerated",
    # GEX & Max Pain
    "GEXEngine",
    "GEXResult",
    "OptionContractData",
    # Multi-Leg Spreads
    "OptionLeg",
    "OptionSpread",
    "IronCondor",
    "VerticalSpread",
    "Straddle",
    "Strangle",
    "CompositeSpreadGreeks",
    # Monte Carlo & Stress-Testing
    "MonteCarloEngine",
    "MonteCarloResult",
]
