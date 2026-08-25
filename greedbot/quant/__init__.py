"""
GreedBot Quantitative & Risk Management Toolkit
-----------------------------------------------
Contains mathematical models for position sizing, risk controls, and portfolio optimization:
- KellyPositionSizer (Discrete, Continuous, Half-Kelly)
- MeanVarianceOptimizer (Markowitz GMV, Tangency Portfolio, Efficient Frontier)
"""

from .kelly import KellyPositionSizer
from .jump_kelly import MertonJumpKellySizer, compute_jump_kelly
from .markowitz import MeanVarianceOptimizer

__all__ = [
    "KellyPositionSizer",
    "MertonJumpKellySizer",
    "compute_jump_kelly",
    "MeanVarianceOptimizer",
]
