# ⚡ GreedBot Python SDK (`greedbot`)

The official Python client library and quantitative strategy toolkit for the **[GreedBot API](https://greedbot.com)**.

GreedBot provides real-time quantitative momentum indicators, Kelly Criterion capital allocation, volatility surface analytics, and AI-driven trade generation.

[![PyPI Version](https://img.shields.io/badge/pypi-v1.0.0-blue.svg)](https://pypi.org/project/greedbot/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

---

## 📦 Installation

```bash
pip install greedbot
```

Or install from source:

```bash
git clone https://github.com/greedbot/greedbot-python-sdk.git
cd greedbot-python-sdk
pip install -e .
```

---

## 🔑 Authentication & Quickstart

Set your GreedBot API Key as an environment variable:

```bash
export GREEDBOT_API_KEY="your_api_key_here"
```

### 1. Fetch Quantitative Price Targets & Sizing
```python
from greedbot import GreedBotClient

client = GreedBotClient()

# Get quantitative price targets and support/resistance zones
targets = client.get_targets(["NVDA", "TSLA", "MSFT"])
print(targets)

# Compute Kelly Criterion capital allocation
kelly = client.get_kelly(["AAPL", "AMZN"])
print(kelly)
```

### 2. Run Quantitative AI Strategies
```python
from greedbot import GreedBotClient
from greedbot.strategies import (
    QualitativeOverlayEngine,
    OptionKellyEngine,
    VolatilityHarvestEngine
)

client = GreedBotClient()

# Qualitative Catalyst vs Options Implied Move Asymmetry
qual = QualitativeOverlayEngine(client)
signal = qual.evaluate_divergence(ticker="NVDA", qualitative_sentiment=0.85)
print(signal)
# Output: {'assessment': 'ASYMMETRIC_UNDERPRICED_VOLATILITY', 'recommended_trade': 'Buy OTM Call Spread'}

# Non-Linear Kelly Convexity Option Sizing
kelly_opt = OptionKellyEngine(client)
sizing = kelly_opt.calculate_sizing(ticker="NVDA", portfolio_size=25000.0)
print(f"Max Risk Budget: ${sizing['max_risk_budget']}")
```

---

## 💻 CLI Commands

The package comes with a built-in CLI executable `greedbot`:

```bash
# Quantitative Price Targets
greedbot targets NVDA TSLA

# Kelly Fraction Allocation
greedbot kelly AAPL MSFT

# Real-time Momentum Pizza Leaderboard
greedbot pizza

# Run full 5-strategy quant scan
greedbot scan
```

---

## 🎯 5 Core Quantitative AI Strategies

1. **Non-Linear Kelly Options Convexity:** Optimizes call/put leverage while enforcing hard downside loss limits.
2. **Qualitative LLM Overlay:** Flags asymmetric mispricings where qualitative catalyst potential exceeds options market pricing.
3. **Sector Volatility Contagion:** Detects sympathy volatility spillover opportunities during earnings cycles.
4. **Macro Dynamic Regime-Switching Matrix:** Rebalances portfolios between Aggressive Kelly Momentum, Risk Parity, and Defensive Cash.
5. **Earnings Volatility Harvest:** Identifies high-IV, low-conviction setups for delta-neutral Iron Condors.

---

## 📄 License
MIT License. Open-source and free for developers building automated trading systems.
