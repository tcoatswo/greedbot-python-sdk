# ⚡ GreedBot Python SDK (`greedbot`)

The official community Python SDK, quantitative algorithmic trading architecture, backtesting engine, and volatility intelligence toolkit for the **[GreedBot API](https://greedbot.com/api-docs)**.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-67%20passed-brightgreen.svg)]()
[![Type Checked](https://img.shields.io/badge/type--checked-PEP%20561-blueviolet.svg)]()

> **Disclaimer:** Community-maintained SDK for algorithmic traders, autonomous AI trading agents, and quantitative researchers interacting with the GreedBot API.

---

## 📑 Table of Contents

- [Architectural Triad](#-architectural-triad)
- [Strategy Paradigm Overview](#-strategy-paradigm-overview)
- [Installation](#-installation)
- [Authentication & Spend Caps](#-authentication--spend-caps)
- [Receipt / Baked Transport & Slot Freshness](#-receipt--baked-transport--slot-freshness)
- [Complete API Reference](#-complete-api-reference)
  - [Synchronous & Asynchronous Clients](#synchronous--asynchronous-clients)
  - [System & Usage (Unmetered)](#system--usage-unmetered)
  - [Quantitative Computation Endpoints](#quantitative-computation-endpoints)
  - [Hub Snapshots](#hub-snapshots)
  - [Hosted Bot Fleet & Copy Trading](#hosted-bot-fleet--copy-trading)
  - [Trade Journal (Unmetered)](#trade-journal-unmetered)
  - [Chart Image Rendering (Plot)](#chart-image-rendering-plot)
- [Quantitative Signal Generators (`greedbot.signals`)](#-quantitative-signal-generators-greedbotsignals)
  - [1. Moving Average Crossover](#1-moving-average-crossover)
  - [2. Time-Series Momentum (Rate of Change & Acceleration)](#2-time-series-momentum-rate-of-change--acceleration)
  - [3. Bollinger Bands & Rolling Z-Score](#3-bollinger-bands--rolling-z-score)
  - [4. Statistical Arbitrage (Cointegration & OLS Spread)](#4-statistical-arbitrage-cointegration--ols-spread)
  - [5. Avellaneda-Stoikov Market Making](#5-avellaneda-stoikov-market-making)
- [Risk Management & Portfolio Math (`greedbot.quant`)](#-risk-management--portfolio-math-greedbotquant)
  - [Kelly Criterion & Half-Kelly Sizing](#kelly-criterion--half-kelly-sizing)
  - [Markowitz Modern Portfolio Theory & Mean-Variance Optimization](#markowitz-modern-portfolio-theory--mean-variance-optimization)
- [Dynamic Position Protection & Trailing Stops (`greedbot.exits`)](#-dynamic-position-protection--trailing-stops-greedbotexits)
- [Event-Driven Backtesting & Analytics (`greedbot.backtest`)](#-event-driven-backtesting--analytics-greedbotbacktest)
- [Multi-Channel Webhook Alerts (`greedbot.alerts`)](#-multi-channel-webhook-alerts-greedbotalerts)
- [Quantitative Strategy Suite (`greedbot.strategies`)](#-quantitative-strategy-suite-greedbotstrategies)
- [Execution Primitives & Paper Broker](#-execution-primitives--paper-broker)
- [External Data Sources Integration](#-external-data-sources-integration)
- [CLI Reference](#-cli-reference)
- [Testing](#-testing)
- [License](#-license)

---

## 🏛 Architectural Triad

To ensure maximum robustness, the GreedBot SDK strictly decouples trading systems into three distinct modules:

```
┌────────────────────────────────────────────────────────┐
│               1. SIGNAL GENERATION                     │
│               (WHEN to Trade)                          │
│   • Trend (SMA, Momentum)   • Mean Reversion (Z-Score) │
│   • Stat Arb (OLS Spread)   • Market Making (AS Model) │
└───────────────────────────┬────────────────────────────┘
                            │ Emits Signals / Targets
┌───────────────────────────▼────────────────────────────┐
│               2. RISK MANAGEMENT & SIZING              │
│               (HOW MUCH to Trade)                      │
│   • Kelly Criterion (f*)    • Markowitz Mean-Variance  │
│   • RiskLimits Book Caps    • Per-Name Concentration   │
│   • Chandelier ATR Stops    • R-Multiple Profit Ratchet│
└───────────────────────────┬────────────────────────────┘
                            │ Emits OrderIntents
┌───────────────────────────▼────────────────────────────┐
│               3. EXECUTION BACKEND                     │
│               (HOW to Trade)                           │
│   • PaperBroker Simulation  • Limit & Spread Orders    │
│   • Batch-Atomic Rollback   • BacktestEngine Simulator │
└────────────────────────────────────────────────────────┘
```

---

## 📊 Strategy Paradigm Overview

| Strategy Paradigm | Core Mathematical Principle | Best Market Regime | Risk Profile |
| :--- | :--- | :--- | :--- |
| **Trend Following** | Assets in motion continue in motion | Strong, persistent trends | Medium to High |
| **Mean Reversion** | Prices return to rolling equilibrium | Range-bound or volatile | Medium |
| **Statistical Arbitrage** | Cointegrated price divergences revert to 0 | Any (Market-Neutral) | Low |
| **Market Making** | Capture bid-ask spread with inventory skew | High-volume, liquid markets | Low |

---

## 📦 Installation

```bash
git clone https://github.com/tcoatswo/greedbot-python-sdk.git
cd greedbot-python-sdk
pip install -e ".[dev]"
```

Dependencies: `requests`, `rich`, `tabulate`, `yfinance`, `numpy`, `pytest`.

---

## 🔑 Authentication & Spend Caps

```bash
export GREEDBOT_API_KEY="your_api_key_here"
export GREEDBOT_API_BASE="https://greedbot.com"  # Optional
```

```python
from greedbot import GreedBotClient, AsyncGreedBotClient

# Synchronous Client
client = GreedBotClient()

# Asynchronous Client (asyncio)
async_client = AsyncGreedBotClient()
```

> [!WARNING]
> **API Metering & Spend Protection:**
> Hub snapshots and Bot Fleet calls are 5¢/call (1 unit). Computations (pizza, rebalance, targets, kelly, parity) are priced by workload. Health checks (`/ping`) and Trade Log calls (`/log`, `/usage`) are **always free / unmetered**.
> If monthly spend reaches your account cap, calls raise `GreedBotSpendCapError` (HTTP 402).

---

## ⏱ Receipt / Baked Transport & Slot Freshness

```python
from greedbot import GreedBotClient, SlotInfo

client = GreedBotClient()
ideas_payload = client.get_hub_when_current("ideas", max_attempts=10, retry_secs=60.0)
slot = SlotInfo.from_payload(ideas_payload)
print(f"Active Slot: {slot.year}/{slot.refresh_n} (Valid until: {slot.effective_until})")
```

---

## ⚡ Synchronous & Asynchronous Clients

```python
import asyncio
from greedbot import AsyncGreedBotClient

async def main():
    client = AsyncGreedBotClient()
    # Concurrently price options expected moves across 5 tickers
    results = await client.batch_scan_expected_moves(["NVDA", "TSLA", "AAPL", "MSFT", "AMD"])
    print(results)

asyncio.run(main())
```

---

## 📐 Quantitative Signal Generators (`greedbot.signals`)

### 1. Moving Average Crossover
$$SMA_n = \frac{1}{n} \sum_{i=0}^{n-1} P_{t-i}$$
`MovingAverageCrossover(short_window=10, long_window=50)` triggers `LONG` when fast crosses above slow and `SHORT` when fast crosses below slow.

### 2. Time-Series Momentum (Rate of Change & Acceleration)
$$M_t = \frac{P_t - P_{t-k}}{P_{t-k}} \times 100, \quad \Delta M_t = M_t - M_{t-1}$$
`TimeSeriesMomentum(lookback_k=14, require_acceleration=True)` captures acceleration in price velocity.

### 3. Bollinger Bands & Rolling Z-Score
$$\mu_t = \text{SMA}_n(P_t), \quad \sigma_t = \sqrt{\frac{1}{n}\sum_{i=0}^{n-1} (P_{t-i} - \mu_t)^2}, \quad Z_t = \frac{P_t - \mu_t}{\sigma_t}$$
`BollingerMeanReversion(window=20, z_threshold=2.0)` shorts when $Z > 2.0$ (overbought) and longs when $Z < -2.0$ (oversold).

### 4. Statistical Arbitrage (Cointegration & OLS Spread)
$$S_t = \ln P^{(A)}_t - \beta \ln P^{(B)}_t - \alpha, \quad \beta = \frac{\text{Cov}(\ln A, \ln B)}{\text{Var}(\ln B)}, \quad Z_S = \frac{S_t - \mu_S}{\sigma_S}$$
`StatisticalArbitrageSpread(ticker_a="SPY", ticker_b="QQQ")` computes dynamic OLS $\beta$ and trades mean reversion of the spread.

### 5. Avellaneda-Stoikov Market Making
$$r(s, t) = s - q \gamma \sigma^2 (T-t), \quad \delta = \gamma \sigma^2 (T-t) + \frac{2}{\gamma} \ln\left(1 + \frac{\gamma}{k}\right)$$
$$\text{Bid} = r - \frac{\delta}{2}, \quad \text{Ask} = r + \frac{\delta}{2}$$
`AvellanedaStoikovMarketMaker(gamma=0.1, k=1.5)` quotes two-sided limit orders, automatically skewing reservation prices to shed inventory $q$.

---

## 🧮 Risk Management & Portfolio Math (`greedbot.quant`)

- **Kelly Criterion**: `KellyPositionSizer(default_fraction=0.50)` calculates optimal growth fraction $f^* = \frac{p(b+1) - 1}{b}$ and applies Half-Kelly.
- **Markowitz Mean-Variance Optimization**: `MeanVarianceOptimizer(risk_free_rate=0.04)` solves $\min \mathbf{w}^T \Sigma \mathbf{w}$ for Global Minimum Variance (GMV) and Maximum Sharpe Ratio (Tangency) portfolios.

---

## 🛡 Dynamic Position Protection & Trailing Stops (`greedbot.exits`)

- **ATR Chandelier Stop**: `ChandelierExit(atr_period=14, multiplier_k=3.0)` sets stop at $\text{Highest High} - 3 \times \text{ATR}_{14}$ (ratchets upward only for longs).
- **R-Multiple Trailing Ratchet**: `TrailingStopManager(entry_price=100.0, initial_stop=95.0)` automatically moves stops to Breakeven at $+1.0R$, locks $+1.0R$ at $+2.0R$, and locks $+2.0R$ at $+3.0R$.

```python
from greedbot import TrailingStopManager

manager = TrailingStopManager(ticker="NVDA", entry_price=100.0, initial_stop=95.0)
status = manager.update(current_price=112.0)
print(f"Stop Ratcheted to: ${status.stop_price:.2f} (+{status.r_multiple}R gain)")
```

---

## 📈 Event-Driven Backtesting & Analytics (`greedbot.backtest`)

Simulate any strategy or signal generator with bar-by-bar execution, realistic transaction costs (slippage + commissions), and zero lookahead bias:

```python
from greedbot import BacktestEngine, MovingAverageCrossover

engine = BacktestEngine(initial_capital=50000.0, slippage_bps=5.0, fee_per_trade=1.00)
signal_gen = MovingAverageCrossover(short_window=10, long_window=30)
result = engine.run_signal_series("NVDA", prices=[...], signal_generator=signal_gen)

print(result.summary())
```

**Performance Tear Sheet Output:**
- CAGR, Total Net Profit, Annualized Sharpe & Sortino Ratios
- Max Drawdown (MDD) & Drawdown Duration
- Calmar Ratio, Win Rate, Profit Factor, and Payoff Ratio ($b$)

---

## 📢 Multi-Channel Webhook Alerts (`greedbot.alerts`)

Dispatch real-time alerts to Discord, Slack, Telegram, or generic webhooks:

```python
from greedbot import OrderIntent, Side, WebhookDispatcher

dispatcher = WebhookDispatcher(discord_url="...", slack_url="...")
dispatcher.send_trade_alert(
    intent=OrderIntent(ticker="NVDA", side=Side.BUY, dollars=10000.0, limit=124.50),
    strategy_name="TrendFollowingStrategy",
    current_price=124.20,
    rationale="10/50 Golden Cross Breakout",
)
```

---

## 🎯 Quantitative Strategy Suite (`greedbot.strategies`)

- **`TrendFollowingStrategy`**: Dual moving average crossover + momentum acceleration.
- **`MeanReversionStrategy`**: Bollinger Bands rolling Z-score reversion.
- **`StatArbPairsStrategy`**: Cointegrated OLS spread pairs trading.
- **`MarketMakerStrategy`**: Avellaneda-Stoikov high-frequency quote placement.
- **`MarkowitzAllocationStrategy`**: Mean-Variance GMV / Tangency asset rebalancing.
- **`ETFBarbellStrategy`**: 80/20 Risk Parity + Kelly growth barbell.
- **`SoloTacticalStrategy`**: Single-asset tactical bot with `MIN_SIGNAL` noise filter.
- **`SectorLongShortStrategy`**: Dollar-neutral long/short sector pair trading across 11 SPDR ETFs.
- **`OptionKellyEngine`**: Non-linear Kelly convex option sizing and risk budgeting.
- **`EarningsRadarStrategy` / `VolatilityHarvestEngine`**: 90-day earnings radar & event-dated expected moves.
- **`MacroRegimeMatrix`**: Dynamic asset allocation matrix driven by `/hub/macro/latest`.
- **`QualitativeOverlayEngine`**: Structured LLM qualitative catalyst overlay vs options pricing.
- **`BotFleetFollower`**: Hosted paper bot fleet tracking and copy trading.

---

## 💻 CLI Reference

```bash
# Health & Spend
greedbot ping
greedbot usage

# Quantitative Endpoints
greedbot targets NVDA TSLA
greedbot kelly AAPL MSFT --fraction 0.5
greedbot pizza XLK XLE XLF
greedbot macro
greedbot earnings
greedbot expected-move NVDA

# Standalone Quant Math
greedbot quant kelly --win-rate 0.60 --win-loss-ratio 2.0 --capital 50000

# Automated Strategy Runs
greedbot run-strategy trend --ticker NVDA
greedbot run-strategy mean_revert --ticker SPY
greedbot run-strategy pairs --ticker SPY --ticker2 QQQ
greedbot run-strategy mm --ticker NVDA
greedbot run-strategy markowitz --capital 100000
greedbot run-strategy etf --capital 25000
```

---

## 🧪 Testing

```bash
# Run the complete test suite
.venv/bin/pytest -v
```

**67 unit tests passing** across 16 test modules covering all endpoints, mathematical formulations, backtesting simulation, exits, async calls, and webhook dispatches.

---

## 📄 License

MIT License. Copyright (c) 2026 GreedBot Community Contributors.
