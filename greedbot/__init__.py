"""
GreedBot Python SDK
Community-maintained Python client library for GreedBot Quantitative Momentum, Sizing, and Volatility APIs.
"""

from .client import GreedBotClient
from .strategies import (
    OptionKellyEngine,
    SectorSpilloverArb,
    QualitativeOverlayEngine,
    MacroRegimeMatrix,
    VolatilityHarvestEngine,
)
from .llm import LLMAnalyzer

__version__ = "1.0.0"
__all__ = [
    "GreedBotClient",
    "OptionKellyEngine",
    "SectorSpilloverArb",
    "QualitativeOverlayEngine",
    "MacroRegimeMatrix",
    "VolatilityHarvestEngine",
    "LLMAnalyzer",
]
