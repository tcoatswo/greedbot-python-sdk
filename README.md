# GreedBot Unofficial Python SDK & High-Throughput Quant Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Rust Core](https://img.shields.io/badge/Rust-Accelerated-orange.svg)](crates/greedbot_quant)
[![Speed](https://img.shields.io/badge/Latency-168ns-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/Tests-84%20Passing-brightgreen.svg)]()

The unofficial community Python SDK and high-performance quantitative toolkit for **GreedBot** — featuring sub-microsecond options Greeks, Newton-Raphson IV solvers, Market-Maker Gamma Exposure (GEX), Multi-Leg Options Spreads, Monte Carlo Jump-Diffusion CVaR, and Turnkey Broker Adapters (Alpaca & Tradier).

---

## ⚡ Blazing-Fast Performance (Rust Engine)

Under the hood, `greedbot` compiles a native SIMD-accelerated Rust backend (`crates/greedbot_quant`) capable of processing millions of option contracts per second with zero garbage collection overhead.

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

## 🚀 Quant & Options Feature Suite

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
# Output: Net GEX, Regime (Long/Short Gamma), Zero-Gamma Flip, Call/Put Walls, Max Pain
```

---

### 2. 🦅 Multi-Leg Options Spread Engine
Construct multi-leg structures with composite Greeks, break-even points, and full payoff curves:

```python
from greedbot import IronCondor, VerticalSpread, Straddle, Strangle

# Construct a 4-leg Iron Condor
ic = IronCondor(
    spot=580.0,
    put_wing=550.0,
    put_short=565.0,
    call_short=595.0,
    call_wing=610.0,
    dte=30.0,
    iv=0.20
)

greeks = ic.get_net_greeks(spot=580.0)
print(f"Net Delta: {greeks.net_delta:+.4f} | Theta: +${greeks.net_theta:.2f}/day | Vega: {greeks.net_vega:.2f}")
print(f"Max Profit: ${greeks.max_profit:,.2f} | Max Loss: -${abs(greeks.max_loss):,.2f}")
print(f"Break-Even Points: {greeks.break_even_points}")
```

---

### 3. 🔌 Turnkey Broker Connectors (Alpaca & Tradier)
Execute GreedBot trade plans directly on retail broker APIs with 1 line of code:

```python
from greedbot import AlpacaBrokerAdapter, TradierBrokerAdapter

# Alpaca Paper / Live Execution
alpaca = AlpacaBrokerAdapter(api_key="...", secret_key="...", paper=True)
print(f"Alpaca Buying Power: ${alpaca.get_account()['buying_power']}")

# Tradier Options Execution
tradier = TradierBrokerAdapter(access_token="...", account_id="...", sandbox=True)
tradier.submit_option_order(
    symbol="SPY",
    option_symbol="SPY260918C00585000",
    side="buy_to_open",
    quantity=2
)
```

---

### 4. 🎲 Monte Carlo Jump-Diffusion CVaR & Stress Testing
Simulate 10,000 portfolio price paths with stochastic jumps to compute tail risk:

```python
from greedbot import MonteCarloEngine

mc = MonteCarloEngine(
    portfolio_value=100000.0,
    annual_volatility=0.22,
    jump_intensity=0.5,    # 0.5 jump events / year
    jump_mean=-0.08,       # -8% average gap down
    jump_vol=0.10
)

res = mc.run_simulation(days=30, num_simulations=10000)
print(res.summary())
print(f"95% Value at Risk (VaR): -${res.var_95_pct:,.2f}")
print(f"95% Expected Shortfall (CVaR): -${res.cvar_95_pct:,.2f}")
```

---

### 5. 💻 Interactive Dashboard & CLI

Run quantitative analytics directly in your terminal:

```bash
# Launch interactive terminal dashboard
greedbot dashboard --spot 580.0

# Compute Market-Maker GEX & Max Pain
greedbot gex --spot 580.0

# Profile Multi-Leg Iron Condors or Straddles
greedbot spread --type iron-condor --spot 580.0

# Run Monte Carlo Jump-Diffusion Stress Test
greedbot mc --capital 100000 --days 30 --sims 5000

# Sub-microsecond analytical Greeks
greedbot greeks --spot 580.0 --strike 585.0 --dte 30 --iv 0.22
```

---

## 🧪 Testing & Verification

Run the comprehensive unit test suite:

```bash
python -m unittest discover tests/ -v
```

All 84 unit tests run in ~1 second across Python 3.9, 3.10, 3.11, and 3.12.

---

## 📄 License
MIT License. Built for algorithmic traders, quantitative researchers, and the GreedBot community.
