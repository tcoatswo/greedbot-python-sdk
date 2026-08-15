"""
GreedBot Quantitative Strategy Suite
------------------------------------
Contains the full suite of quantitative, volatility, and AI investment strategies:

1. ETFBarbellStrategy: 80/20 Risk Parity + Kelly barbell over ETF basket.
2. SoloTacticalStrategy: Single-ticker directional IN/FLAT based on /targets signal.
3. SectorLongShortStrategy: Dollar-neutral long/short sector pair trading across 11 SPDR ETFs.
4. OptionKellyEngine: Non-linear Kelly convex option sizing and risk budgeting.
5. EarningsRadarStrategy: 90-day earnings radar & event-dated expected move options trading.
6. VolatilityHarvestEngine: High-IV delta-neutral Iron Condor scanner.
7. SectorSpilloverArb: Earnings volatility contagion & sympathy spillover scanner.
8. MacroRegimeMatrix: Dynamic macro cycle multi-asset allocation matrix.
9. QualitativeOverlayEngine: Structured LLM qualitative catalyst overlay vs options implied move.
10. BotFleetFollower: Copy trading and hosted paper bot fleet tracking.
11. TrendFollowingStrategy: Dual-factor Moving Average Crossover + Time-Series Momentum.
12. MeanReversionStrategy: Bollinger Bands & Rolling Z-Score mean reversion.
13. StatArbPairsStrategy: Cointegrated OLS spread pairs trading.
14. MarketMakerStrategy: Avellaneda-Stoikov inventory reservation & quote maker.
15. MarkowitzAllocationStrategy: Mean-Variance GMV and Tangency portfolio optimization.
"""

from .base import Strategy
from .etf_barbell import ETFBarbellStrategy
from .solo_tactical import SoloTacticalStrategy
from .sector_long_short import SectorLongShortStrategy
from .option_kelly import OptionKellyEngine
from .earnings_radar import EarningsRadarStrategy, VolatilityHarvestEngine, SectorSpilloverArb
from .macro_matrix import MacroRegimeMatrix
from .qualitative_overlay import QualitativeOverlayEngine
from .bot_follower import BotFleetFollower
from .trend_following import TrendFollowingStrategy
from .mean_reversion import MeanReversionStrategy
from .pairs_trading import StatArbPairsStrategy
from .market_making import MarketMakerStrategy
from .markowitz_rebalance import MarkowitzAllocationStrategy

__all__ = [
    "Strategy",
    "ETFBarbellStrategy",
    "SoloTacticalStrategy",
    "SectorLongShortStrategy",
    "OptionKellyEngine",
    "EarningsRadarStrategy",
    "VolatilityHarvestEngine",
    "SectorSpilloverArb",
    "MacroRegimeMatrix",
    "QualitativeOverlayEngine",
    "BotFleetFollower",
    "TrendFollowingStrategy",
    "MeanReversionStrategy",
    "StatArbPairsStrategy",
    "MarketMakerStrategy",
    "MarkowitzAllocationStrategy",
]
