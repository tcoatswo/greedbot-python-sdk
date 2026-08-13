"""
End-to-End LLM Qualitative Overlay Pipeline Example
----------------------------------------------------
Demonstrates how to plug in your own LLM API key (OpenAI, Anthropic, or Gemini)
to analyze raw text (e.g. 10-Q filing / earnings transcript) and feed the output
directly into GreedBot's Qualitative Overlay Engine to generate asymmetric option trades.

Usage:
    export GREEDBOT_API_KEY="***"
    export OPENAI_API_KEY="***"       # Or ANTHROPIC_API_KEY / GEMINI_API_KEY
    python examples/llm_qualitative_pipeline.py
"""

import os
import json
from greedbot import GreedBotClient, LLMAnalyzer
from greedbot.strategies import QualitativeOverlayEngine

# Sample un-summarized excerpt from a corporate SEC filing / earnings release
SAMPLE_CATALYST_TEXT = """
POET Technologies Inc. reported a significant revenue increase of +112% YoY for Q2 2026.
The Company closed a $400M registered direct offering, increasing total cash and short-term
investments to $796.3M. Furthermore, the Company secured an initial $50M purchase order from
Lumilens Inc. as part of a $500M multi-year commercial framework for AI optical engines,
and completed production transfer to high-volume manufacturing facilities in Malaysia.
Management expects rapid adoption of its 800G and 1.6T optical engine chipsets for AI clusters.
"""

def main():
    print("⚡ [GreedBot + LLM Qualitative Analysis Pipeline]")
    print("--------------------------------------------------")

    # 1. Initialize GreedBot Client
    client = GreedBotClient(api_key=os.environ.get("GREEDBOT_API_KEY", ""))

    # 2. Initialize Pluggable LLM Analyzer
    # Automatically picks up OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY
    # Or explicitly pass: LLMAnalyzer(provider="openai", api_key="sk-...", model="gpt-4o-mini")
    # Or pass a custom callable for local models/Ollama: LLMAnalyzer(custom_caller=my_fn)
    llm = LLMAnalyzer(provider="auto")
    print(f"🤖 Active LLM Provider: {llm.provider.upper()}")

    # 3. Analyze raw text to extract structured qualitative sentiment & conviction
    ticker = "POET"
    print(f"\n🧠 Analyzing catalyst text for ${ticker} with LLM...")
    llm_analysis = llm.analyze_catalyst(ticker=ticker, text=SAMPLE_CATALYST_TEXT)
    print(f"  • Sentiment Score: {llm_analysis.get('qualitative_sentiment')}")
    print(f"  • Conviction:      {llm_analysis.get('catalyst_conviction')}")
    print(f"  • Thesis Rationale: {llm_analysis.get('summary_rationale')}")

    # 4. Pipe structured scores into GreedBot Qualitative Overlay Engine
    print(f"\n📊 Evaluating against GreedBot options-implied expected move...")
    qual_engine = QualitativeOverlayEngine(client)
    signal = qual_engine.evaluate_divergence(
        ticker=ticker,
        qualitative_sentiment=float(llm_analysis.get("qualitative_sentiment", 0.8)),
        conviction=float(llm_analysis.get("catalyst_conviction", 0.85))
    )

    print("\n🎯 Final Generated Trade Signal:")
    print(json.dumps(signal, indent=2))

if __name__ == "__main__":
    main()
