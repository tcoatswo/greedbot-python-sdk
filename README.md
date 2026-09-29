# GreedBot Unofficial Python SDK & High-Throughput Quant Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Rust Core](https://img.shields.io/badge/Rust-Accelerated-orange.svg)](crates/greedbot_quant)
[![Latency](https://img.shields.io/badge/Latency-168ns-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/Tests-112%20Passing-brightgreen.svg)]()
[![Type Checked](https://img.shields.io/badge/type--checked-PEP%20561-blueviolet.svg)]()

The unofficial community Python SDK and high-performance quantitative toolkit for **GreedBot** — featuring sub-microsecond options Greeks, Newton-Raphson IV solvers, Market-Maker Gamma Exposure (GEX), Multi-Leg Options Spreads, Monte Carlo Jump-Diffusion CVaR, Risk Parity / ERC, RSI, MACD, Turnkey Broker Adapters (Alpaca & Tradier), Institutional Paper Broker with market microstructure slippage, and the Drosophila Connectome Bio-Trader.

---

## ⚡ Blazing-Fast Performance (Rust Engine)

Under the hood, `greedbot` provides a native SIMD-accelerated Rust backend (`crates/greedbot_quant`) capable of processing millions of option contracts per second with zero garbage collection overhead and an analytical pure-Python fallback.

### 🔥 Benchmark: 100,000 Option Contracts

| Engine | Latency / Contract | Throughput (Contracts/Sec) | Speedup vs Baseline |
| :--- | :--- | :--- | :--- |
| **GreedBot Native (Rust + Rayon)** | **168.1 nanoseconds** | **5,949,734 / sec** | **~50.5x faster** |
| GreedBot Python FFI | 6.43 microseconds | 155,520 / sec | ~1.35x faster |
| NumPy / SciPy Baseline | 8.50 microseconds | 117,640 / sec | 1.0x (Baseline) |
| Pure Python Loop | 42.10 microseconds | 23,750 / sec | ~0.20x |

---

## 📦 Installation

### Direct Install via Git
```bash
pip install git+https://github.com/tcoatswo/greedbot-python-sdk.git
```

### Build from Source with Native Rust Acceleration
```bash
git clone https://github.com/tcoatswo/greedbot-python-sdk.git
cd greedbot-python-sdk
cargo build --release --manifest-path crates/greedbot_quant/Cargo.toml
pip install -e .
```

---

## 🚀 Quant & Execution Feature Suite

### 1. 🎯 Market-Maker Gamma Exposure (GEX) & Max Pain
Pinpoint dealer hedging pressure, Zero-Gamma volatility flip points, and expiration Max Pain strikes:

```python
from greedbot import GEXEngine, OptionContractData

engine = GEXEngine(spot=580.0)
contracts = [
    OptionContractData(strike=560.0, is_call=False, open_interest=10000, dte=30, iv=0.25),
    OptionContractData(strike=570.0, is_call=False, open_interest=8000, dte=30, iv=0.22),
    OptionContractData(strike=580.0, is_call=True, open_interest=15000, dte=30, iv=0.20),
    OptionContractData(strike=590.0, is_call=True, open_interest=20000, dte=30, iv=0.18),
    OptionContractData(strike=600.0, is_call=True, open_interest=25000, dte=30, iv=0.16),
]

res = engine.calculate_gex(contracts)
print(res.summary())
```

---

### 2. 🦅 Multi-Leg Options Spread Engine
Construct multi-leg structures with composite Greeks, break-even points, and full payoff curves:

```python
from greedbot import IronCondor

# Construct a 4-leg Iron Condor
ic = IronCondor(
    spot=580.0,
    put_wing=550.0,
    put_short=565.0,
    call_short=595.0,
    call_wing=610.0,
    dte=30.0,
    iv=0.20,
)

greeks = ic.get_net_greeks(spot=580.0)
print(f"Net Delta: {greeks.net_delta:+.4f} | Theta: +${greeks.net_theta:.2f}/day | Vega: {greeks.net_vega:.2f}")
print(f"Max Profit: ${greeks.max_profit:,.2f} | Max Loss: -${abs(greeks.max_loss):,.2f}")
```

---

### 3. 🪰 Drosophila Connectome Bio-Trader & Institutional Paper Broker
Simulate sensory-motor neural dynamics (130k-neuron fruit fly connectome) driving Kelly-sized paper execution with square-root slippage and SQLite ledger tracking:

```python
from greedbot import InstitutionalPaperBroker, DrosophilaConnectomeTrader, ConnectomeSensoryInput

broker = InstitutionalPaperBroker(starting_cash=100000.0)
fly = DrosophilaConnectomeTrader(broker=broker)

sensor = ConnectomeSensoryInput(
    ticker="BTC",
    price=78000.0,
    price_velocity_5m=1.85,
    bid_ask_delta=0.65,
    net_gex_regime=-1.0,
    iv_skew=0.35
)

decision = fly.process_tick(sensor)
print(f"Action: {decision.action} | Confidence: {decision.confidence:.2f} | Target Sizing: ${decision.target_dollars:,.2f}")
```

---

### 4. 🎲 Monte Carlo Jump-Diffusion CVaR & Stress Testing
Simulate 10,000 portfolio price paths with stochastic jumps to compute tail risk:

```python
from greedbot import MonteCarloEngine

mc = MonteCarloEngine(
    portfolio_value=100000.0,
    annual_volatility=0.22,
    jump_intensity=0.5,
    jump_mean=-0.08,
    jump_vol=0.10
)

res = mc.run_simulation(days=30, num_simulations=10000)
print(f"95% Value at Risk (VaR): -${res.var_95_pct:,.2f}")
print(f"95% Expected Shortfall (CVaR): -${res.cvar_95_pct:,.2f}")
```

---

### 5. 📐 Quantitative Signal Generators (`greedbot.signals`)

- **Moving Average Crossover**: `MovingAverageCrossover(short_window=10, long_window=50)` triggers `LONG` on golden cross and `SHORT` on death cross.
- **Time-Series Momentum**: `TimeSeriesMomentum(lookback_k=14, require_acceleration=True)` measures rate-of-change and second derivative velocity.
- **Bollinger Mean Reversion**: `BollingerMeanReversion(window=20, z_threshold=2.0)` computes rolling z-scores with dynamic standard deviation bands.
- **Statistical Arbitrage**: `StatisticalArbitrageSpread(ticker_a="SPY", ticker_b="QQQ")` dynamically estimates cointegrating hedge ratio $\beta$ via rolling OLS.
- **Avellaneda-Stoikov Market Maker**: `AvellanedaStoikovMarketMaker(gamma=0.1, k=1.5)` quotes two-sided bid/ask orders with reservation price inventory shading.
- **Relative Strength Index (RSI)**: `RSIMeanReversion(period=14, oversold_threshold=30.0, overbought_threshold=70.0)` with Wilder exponential smoothing.
- **MACD Trend Momentum**: `MACDCrossover(fast_period=12, slow_period=26, signal_period=9)` with dual-EMA and histogram convergence/divergence.

---

### 6. 🧮 Risk Management & Quant Math (`greedbot.quant`)

- **Kelly Criterion**: `KellyPositionSizer(default_fraction=0.50)` calculates optimal growth fraction $f^* = \frac{p(b+1) - 1}{b}$ and applies Half-Kelly.
- **Merton Jump Kelly**: `MertonJumpKellySizer` calculates non-linear option convex sizing incorporating jump penalties and tail risk.
- **Markowitz Mean-Variance Optimization**: `MeanVarianceOptimizer(risk_free_rate=0.04)` solves for Global Minimum Variance (GMV) and Maximum Sharpe Ratio (Tangency) portfolios.
- **Risk Parity & Equal Risk Contribution (ERC)**: `RiskParityOptimizer()` calculates Inverse Volatility and exact Equal Risk Contribution allocations via cyclical coordinate descent.

---

### 7. 🛡 Dynamic Position Protection & Trailing Stops (`greedbot.exits`)

- **ATR Chandelier Stop**: `ChandelierExit(atr_period=14, multiplier_k=3.0)` sets stop at $\text{Highest High} - 3 \times \text{ATR}_{14}$ (ratchets upward only for longs).
- **R-Multiple Trailing Ratchet**: `TrailingStopManager(entry_price=100.0, initial_stop=95.0)` automatically moves stops to Breakeven at $+1.0R$, locks $+1.0R$ at $+2.0R$, and locks $+2.0R$ at $+3.0R$.

---

### 8. 📈 Event-Driven Backtesting & Analytics (`greedbot.backtest`)

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
- Historical Value at Risk (VaR 95% & 99%)
- Conditional Value at Risk (CVaR / Expected Shortfall 95% & 99%)
- Benchmark Relative Metrics: Jensen's Alpha, Beta, Treynor Ratio, and Information Ratio (IR)

---

### 9. 📢 Multi-Channel Webhook Alerts (`greedbot.alerts`)

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

## 💻 CLI Reference

```bash
# Health & Spend
greedbot ping
greedbot usage

# Quantitative Endpoints
greedbot targets NVDA TSLA
greedbot kelly AAPL MSFT --fraction 0.5
greedbot parity XLK XLE XLF
greedbot pizza XLK XLE XLF
greedbot macro
greedbot earnings
greedbot expected-move NVDA

# Standalone Quant Math
greedbot quant kelly --win-rate 0.60 --win-loss-ratio 2.0 --capital 50000
greedbot quant markowitz --capital 100000
greedbot quant risk-parity --capital 100000

# Options Analytics & Greeks
greedbot greeks --spot 580 --strike 580 --dte 30 --iv 0.20
greedbot solve-iv --spot 580 --strike 580 --price 12.50 --dte 30
greedbot gex --spot 580
greedbot spread --type iron-condor --spot 580
greedbot mc --capital 100000 --days 30 --sims 5000
greedbot dashboard --spot 580

# Event-Driven Backtesting
greedbot backtest trend --ticker NVDA
greedbot backtest rsi --ticker AAPL
greedbot backtest macd --ticker TSLA
greedbot backtest mean_revert --ticker SPY --json

# Automated Strategy Runs
greedbot run-strategy trend --ticker NVDA
greedbot run-strategy mean_revert --ticker SPY
greedbot run-strategy pairs --ticker SPY --ticker2 QQQ
greedbot run-strategy mm --ticker NVDA
greedbot run-strategy markowitz --capital 100000
greedbot run-strategy etf --capital 25000
```

---

## 🧪 Testing & Verification

```bash
.venv/bin/pytest -v
```

**112 unit tests passing** across 27 test modules covering all endpoints, mathematical formulations, backtesting simulation, risk firewalls, broker accounting, exits, options Greeks, GEX, Monte Carlo, and connectome bio-traders.

---

## 📄 License
MIT License. Built for algorithmic traders, quantitative researchers, and the GreedBot community.
