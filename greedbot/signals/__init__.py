"""
GreedBot Quantitative Signal Generation Suite
---------------------------------------------
Exposes signal generators across the four quantitative pillars:
1. Trend Following (MovingAverageCrossover, TimeSeriesMomentum)
2. Mean Reversion (BollingerMeanReversion)
3. Statistical Arbitrage (StatisticalArbitrageSpread)
4. Market Making (AvellanedaStoikovMarketMaker)
"""

from .base import Signal, SignalDirection, SignalGenerator
from .trend import MovingAverageCrossover, TimeSeriesMomentum
from .mean_reversion import BollingerMeanReversion
from .pairs import StatisticalArbitrageSpread
from .market_maker import AvellanedaStoikovMarketMaker

__all__ = [
    "Signal",
    "SignalDirection",
    "SignalGenerator",
    "MovingAverageCrossover",
    "TimeSeriesMomentum",
    "BollingerMeanReversion",
    "StatisticalArbitrageSpread",
    "AvellanedaStoikovMarketMaker",
]
