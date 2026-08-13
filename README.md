# ⚡ GreedBot Python SDK (`greedbot`)

An open-source, community-maintained Python client library and quantitative strategy toolkit for interacting with the **[GreedBot API](https://greedbot.com)**.

> **Disclaimer:** This is an unofficial, community-developed SDK and is not affiliated with or endorsed by GreedBot.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

---

## 📦 Installation

Install directly from GitHub using `pip`:

```bash
pip install git+https://github.com/tcoatswo/greedbot-python-sdk.git
```

Or install locally in editable/development mode:

```bash
git clone https://github.com/tcoatswo/greedbot-python-sdk.git
cd greedbot-python-sdk
pip install -e .
```

---

## 🔑 Authentication & Quickstart

Set your API keys as environment variables:

```bash
export GREEDBOT_API_KEY="***"
export OPENAI_API_KEY="***"  # Optional: Or ANTHROPIC_API_KEY / GEMINI_API_KEY
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

### 2. Plug-and-Play LLM Qualitative Analysis Pipeline
Use any LLM (OpenAI, Anthropic, Gemini, or local models) to analyze SEC filings, earnings transcripts, or news, then pipe structured sentiment & conviction directly into GreedBot:

```python
from greedbot import GreedBotClient, LLMAnalyzer
from greedbot.strategies import QualitativeOverlayEngine

client = GreedBotClient()

# 1. Initialize plug-and-play LLM adapter (auto-detects OpenAI/Anthropic/Gemini)
llm = LLMAnalyzer(provider="auto")

# 2. Extract structured qualitative sentiment (-1.0 to +1.0) & conviction (0.0 to 1.0)
catalyst_text = "Company reported Q2 revenue growth of +112% YoY and secured a $50M initial order..."
analysis = llm.analyze_catalyst(ticker="POET", text=catalyst_text)

# 3. Pipe into GreedBot Qualitative Overlay Engine
qual_engine = QualitativeOverlayEngine(client)
signal = qual_engine.evaluate_divergence(
    ticker="POET",
    qualitative_sentiment=analysis["qualitative_sentiment"],
    conviction=analysis["catalyst_conviction"]
)
print(signal)
# Output: {'assessment': 'ASYMMETRIC_UNDERPRICED_VOLATILITY', 'recommended_trade': 'Buy OTM Call Spread'}
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

## 📂 Examples & Demos

Check the [`examples/`](examples/) directory for full runnable scripts:
- [`examples/quickstart.py`](examples/quickstart.py): End-to-end tour of client methods and strategy sizing.
- [`examples/llm_qualitative_pipeline.py`](examples/llm_qualitative_pipeline.py): Live catalyst text analysis using OpenAI/Anthropic/Gemini with GreedBot.

---

## 📄 License
MIT License.
