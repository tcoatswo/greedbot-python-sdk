"""
Example LLM Qualitative Catalyst Pipeline
-----------------------------------------
Analyzes SEC corporate disclosures and financial news with universal LLM providers
(OpenAI, Anthropic Claude, Gemini, DeepSeek, or local models) and pipes structured
sentiment & conviction into the GreedBot Qualitative Overlay Engine.
"""

from greedbot import GreedBotClient, LLMAnalyzer, QualitativeOverlayEngine, SecEdgarSource

def main():
    client = GreedBotClient()
    ticker = "POET"

    print(f"⚡ Running Qualitative Catalyst LLM Pipeline for {ticker}...")

    # 1. Fetch catalyst text from SEC filings
    sec_source = SecEdgarSource()
    filing_text = sec_source.get_latest_catalyst_text(ticker)
    print(f"\nExtracted Disclosure Text:\n\"{filing_text}\"")

    # 2. Analyze with LLM Adapter (auto-detects OpenAI/Claude/Gemini/DeepSeek)
    llm = LLMAnalyzer(provider="auto")
    analysis = llm.analyze_catalyst(ticker=ticker, text=filing_text)
    print("\nLLM Qualitative Output:")
    print(f"  • Sentiment (-1.0 to +1.0): {analysis['qualitative_sentiment']}")
    print(f"  • Conviction (0.0 to 1.0): {analysis['catalyst_conviction']}")
    print(f"  • Thesis Rationale: {analysis['summary_rationale']}")

    # 3. Evaluate divergence against options market implied move
    qual_engine = QualitativeOverlayEngine()
    signal = qual_engine.evaluate_divergence(
        client=client,
        ticker=ticker,
        qualitative_sentiment=analysis["qualitative_sentiment"],
        conviction=analysis["catalyst_conviction"],
    )

    print("\nGreedBot Overlay Assessment:")
    print(f"  • Market Expected Move: ±{signal['market_expected_move_pct']}%")
    print(f"  • Qualitative Expected Move: ±{signal['qualitative_expected_move_pct']}%")
    print(f"  • Asymmetry Delta: {signal['asymmetry_delta_pct']:+0.2f}%")
    print(f"  • Assessment: {signal['assessment']}")
    print(f"  • Recommended Trade: {signal['recommended_trade']}")

if __name__ == "__main__":
    main()
