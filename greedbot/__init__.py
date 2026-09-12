"""
GreedBot Python SDK
-------------------
Official community Python SDK for the GreedBot Quantitative Trading & Volatility Intelligence API.
"""

from .client import (
    GreedBotClient,
    GreedBotAPIError,
    GreedBotSpendCapError,
    GreedBotStaleDataError,
    DEFAULT_BASE_URL,
)
from .async_client import AsyncGreedBotClient
from .models import (
    SlotInfo,
    OrderIntent,
    Side,
    Fill,
    BotRunResult,
    TradePlan,
)
from .risk import RiskLimits
from .exits import (
    ChandelierExit,
    TrailingStopManager,
    PositionExitStatus,
)
from .broker import Broker, PaperBroker
from .dataframe import (
    map_from_df,
    ranking_from_pizza,
    extract_signal,
    to_dataframe,
)
from .journal import TradeJournal
from .llm import LLMAnalyzer
from .alerts import WebhookDispatcher
from .datasources import (
    DataSource,
    MarketDataSource,
    YahooFinanceSource,
    CatalystDataSource,
    SecEdgarSource,
    FinancialNewsSource,
)
from .signals import (
    Signal,
    SignalDirection,
    SignalGenerator,
    MovingAverageCrossover,
    TimeSeriesMomentum,
    BollingerMeanReversion,
    StatisticalArbitrageSpread,
    AvellanedaStoikovMarketMaker,
)
from .quant import (
    KellyPositionSizer,
    MertonJumpKellySizer,
    MeanVarianceOptimizer,
    OptionGreeks,
    calculate_greeks,
    solve_iv,
    generate_volatility_surface,
    is_rust_accelerated,
)
from .backtest import (
    PerformanceMetrics,
    BacktestEngine,
    BacktestResult,
)
from .strategies import (
    Strategy,
    ETFBarbellStrategy,
    SoloTacticalStrategy,
    SectorLongShortStrategy,
    OptionKellyEngine,
    EarningsRadarStrategy,
    VolatilityHarvestEngine,
    SectorSpilloverArb,
    MacroRegimeMatrix,
    QualitativeOverlayEngine,
    BotFleetFollower,
    TrendFollowingStrategy,
    MeanReversionStrategy,
    StatArbPairsStrategy,
    MarketMakerStrategy,
    MarkowitzAllocationStrategy,
)

__version__ = "1.3.0"

__all__ = [
    # Core Clients
    "GreedBotClient",
    "AsyncGreedBotClient",
    "GreedBotAPIError",
    "GreedBotSpendCapError",
    "GreedBotStaleDataError",
    "DEFAULT_BASE_URL",
    # Models & Primitives
    "SlotInfo",
    "OrderIntent",
    "Side",
    "Fill",
    "BotRunResult",
    "TradePlan",
    "RiskLimits",
    # Dynamic Position Exits
    "ChandelierExit",
    "TrailingStopManager",
    "PositionExitStatus",
    # Broker
    "Broker",
    "PaperBroker",
    # Dataframe Helpers
    "map_from_df",
    "ranking_from_pizza",
    "extract_signal",
    "to_dataframe",
    # Journal & Alerts
    "TradeJournal",
    "WebhookDispatcher",
    # LLM
    "LLMAnalyzer",
    # Data Sources
    "DataSource",
    "MarketDataSource",
    "YahooFinanceSource",
    "CatalystDataSource",
    "SecEdgarSource",
    "FinancialNewsSource",
    # Signal Generators
    "Signal",
    "SignalDirection",
    "SignalGenerator",
    "MovingAverageCrossover",
    "TimeSeriesMomentum",
    "BollingerMeanReversion",
    "StatisticalArbitrageSpread",
    "AvellanedaStoikovMarketMaker",
    # Quant Math & Portfolio Optimization
    "KellyPositionSizer",
    "MertonJumpKellySizer",
    "MeanVarianceOptimizer",
    "OptionGreeks",
    "calculate_greeks",
    "solve_iv",
    "generate_volatility_surface",
    "is_rust_accelerated",
    # Backtesting Engine & Metrics
    "PerformanceMetrics",
    "BacktestEngine",
    "BacktestResult",
    # Strategies Suite
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
