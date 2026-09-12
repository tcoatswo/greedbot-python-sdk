"""
GreedBot Python SDK
-------------------
Unofficial community Python SDK and Quantitative Toolkit for the GreedBot Trading & Volatility Intelligence API.
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
from .adapters import AlpacaBrokerAdapter, TradierBrokerAdapter
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
    GEXEngine,
    GEXResult,
    OptionContractData,
    OptionLeg,
    OptionSpread,
    IronCondor,
    VerticalSpread,
    Straddle,
    Strangle,
    CompositeSpreadGreeks,
    MonteCarloEngine,
    MonteCarloResult,
)
from .dashboard import print_terminal_dashboard, get_streamlit_app_code
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

__version__ = "1.4.0"

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
    # Brokers & Turnkey Adapters
    "Broker",
    "PaperBroker",
    "AlpacaBrokerAdapter",
    "TradierBrokerAdapter",
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
    # Rust Options Greeks & Volatility
    "OptionGreeks",
    "calculate_greeks",
    "solve_iv",
    "generate_volatility_surface",
    "is_rust_accelerated",
    # Market-Maker GEX & Max Pain
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
    # Dashboard & Visuals
    "print_terminal_dashboard",
    "get_streamlit_app_code",
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
