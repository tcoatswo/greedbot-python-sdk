"""
GreedBot Quantitative & Risk Management Toolkit
-----------------------------------------------
Contains mathematical models for position sizing, risk controls, and portfolio optimization:
- Option Greeks & Implied Volatility (Native Rust Accelerated Engine)
- KellyPositionSizer (Discrete, Continuous, Half-Kelly)
- MertonJumpKellySizer (Merton Jump Diffusion Kelly)
- MeanVarianceOptimizer (Markowitz GMV, Tangency Portfolio, Efficient Frontier)
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

__all__ = [
    "KellyPositionSizer",
    "MertonJumpKellySizer",
    "compute_jump_kelly",
    "MeanVarianceOptimizer",
    "OptionGreeks",
    "calculate_greeks",
    "solve_iv",
    "generate_volatility_surface",
    "is_rust_accelerated",
]
