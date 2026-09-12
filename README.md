# GreedBot Python SDK & High-Throughput Quant Engine

[![PyPI Version](https://img.shields.io/badge/pypi-v1.3.0-blue.svg)](https://pypi.org/project/greedbot/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Rust Core](https://img.shields.io/badge/Rust-Accelerated-orange.svg)](crates/greedbot_quant)
[![Speed](https://img.shields.io/badge/Latency-168ns-brightgreen.svg)]()

The official Python SDK and high-performance quantitative toolkit for **GreedBot** — featuring sub-microsecond options Greeks, Newton-Raphson IV solvers, Merton Jump-Diffusion Kelly position sizing, and volatility surface modeling.

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

```bash
pip install greedbot
```

To build from source with the native Rust acceleration:
```bash
git clone https://github.com/tcoatswo/greedbot-python-sdk.git
cd greedbot-python-sdk
cargo build --release --manifest-path crates/greedbot_quant/Cargo.toml
pip install -e .
```

---

## 🚀 Quickstart: Options Greeks & Volatility

```python
import greedbot
from greedbot import calculate_greeks, solve_iv, generate_volatility_surface

# 1. Sub-microsecond analytical Greeks (Delta, Gamma, Vega, Theta, Rho, Vanna, Volga)
greeks = calculate_greeks(
    spot=580.0,      # Underlying price
    strike=585.0,    # Strike
    dte=30.0,        # Days to expiration
    iv=0.22,         # 22% Implied Volatility
    is_call=True
)

print(f"Call Delta : {greeks.delta:.4f}")
print(f"Call Gamma : {greeks.gamma:.4f}")
print(f"Call Vega  : {greeks.vega:.4f}")
print(f"Call Theta : {greeks.theta:.4f}")
print(f"Call Price : ${greeks.price:.2f}")

# 2. Fast Implied Volatility Solver (Newton-Raphson + Bisection fallback)
iv = solve_iv(
    spot=580.0,
    strike=585.0,
    dte=30.0,
    market_price=13.25,
    is_call=True
)
print(f"Implied Volatility: {iv * 100:.2f}%")

# 3. Generate 3D Volatility Surface Grid
surface = generate_volatility_surface(spot=580.0, base_vol=0.20)
print(f"Generated {len(surface)} grid points across strike/expiration curve.")
```

---

## 🛡️ Merton Jump-Diffusion Kelly & Portfolio Math

```python
from greedbot import MertonJumpKellySizer, MeanVarianceOptimizer

# Position sizing with jump risk (fat tails & gap downs)
sizer = MertonJumpKellySizer(
    expected_drift=0.12,
    diffusion_vol=0.18,
    jump_intensity=0.5,    # 0.5 jump events / year
    mean_jump_size=-0.08,  # -8% average gap
    jump_vol=0.10
)
f_star = sizer.optimal_fraction(fraction_multiplier=0.5)  # Half-Kelly
print(f"Optimal Allocation: {f_star * 100:.1f}%")
```

---

## 💻 Standalone Rust Quant CLI

For ultra-low latency pipelines, call the compiled binary directly:

```bash
# Benchmark 100k contracts
./crates/greedbot_quant/target/release/greedbot_quant bench --contracts 100000

# Analytical Greeks calculation
./crates/greedbot_quant/target/release/greedbot_quant greeks \
  --spot 580.0 --strike 585.0 --dte 30 --iv 0.22 --opt-type call

# Fast IV solver
./crates/greedbot_quant/target/release/greedbot_quant solve-iv \
  --spot 580.0 --strike 585.0 --dte 30 --market-price 13.25 --opt-type call
```

---

## 📄 License
MIT License. Built for algorithmic traders, quant researchers, and the GreedBot community.
