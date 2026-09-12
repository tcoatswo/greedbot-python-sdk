"""
GreedBot Interactive Quant & Visual Analytics Dashboard
-------------------------------------------------------
Provides terminal-based live analytics (Rich ASCII charts) and Streamlit web UI launcher
for 3D Volatility Surfaces, Market-Maker GEX, Multi-Leg Spread payoffs, and Monte Carlo risk.
"""

from typing import Dict, List, Optional
import sys

from .quant.gex import GEXEngine, OptionContractData
from .quant.spreads import IronCondor, VerticalSpread, Straddle, Strangle
from .quant.monte_carlo import MonteCarloEngine
from .quant.rust_engine import generate_volatility_surface

def print_terminal_dashboard(spot: float = 580.0):
    """
    Renders an ASCII/ANSI terminal quant dashboard.
    """
    print("=" * 65)
    print(" 🚀 GREEDBOT QUANT & VOLATILITY ANALYTICS DASHBOARD")
    print(f" Underlying Spot Price: ${spot:.2f}")
    print("=" * 65)

    # 1. GEX Analysis
    contracts = [
        OptionContractData(strike=spot * 0.95, is_call=False, open_interest=12000, dte=30, iv=0.24),
        OptionContractData(strike=spot * 0.98, is_call=False, open_interest=8500, dte=30, iv=0.22),
        OptionContractData(strike=spot * 1.00, is_call=True, open_interest=15000, dte=30, iv=0.20),
        OptionContractData(strike=spot * 1.02, is_call=True, open_interest=9500, dte=30, iv=0.19),
        OptionContractData(strike=spot * 1.05, is_call=True, open_interest=22000, dte=30, iv=0.18),
    ]
    gex_engine = GEXEngine(spot=spot)
    gex_res = gex_engine.calculate_gex(contracts)
    print("\n[1] MARKET-MAKER GAMMA EXPOSURE (GEX)")
    print(gex_res.summary().strip())

    # 2. Multi-Leg Spread Profiler
    ic = IronCondor(
        spot=spot,
        put_wing=spot * 0.90,
        put_short=spot * 0.95,
        call_short=spot * 1.05,
        call_wing=spot * 1.10,
        dte=30,
        iv=0.20,
    )
    greeks = ic.get_net_greeks(spot)
    print("\n[2] MULTI-LEG SPREAD: IRON CONDOR")
    print(f"Net Delta: {greeks.net_delta:+.4f} | Gamma: {greeks.net_gamma:+.6f} | Theta: {greeks.net_theta:+.2f}/day | Vega: {greeks.net_vega:+.2f}")
    print(f"Max Profit: ${greeks.max_profit:,.2f} | Max Loss: -${abs(greeks.max_loss or 0):,.2f}")
    print(f"Break-Evens: {greeks.break_even_points}")

    # 3. Monte Carlo Risk & Stress Test
    mc = MonteCarloEngine(portfolio_value=100000.0, annual_volatility=0.22, jump_intensity=0.5, jump_mean=-0.08, jump_vol=0.10)
    mc_res = mc.run_simulation(days=30, num_simulations=5000)
    print("\n[3] MONTE CARLO JUMP-DIFFUSION STRESS TEST (30 Days)")
    print(f"95% VaR (Value at Risk)   : -${mc_res.var_95_pct:,.2f}")
    print(f"95% CVaR (Expected Loss)  : -${mc_res.cvar_95_pct:,.2f}")
    print("=" * 65)

def get_streamlit_app_code() -> str:
    """Returns standalone Streamlit web dashboard script."""
    return """
import streamlit as st
import plotly.graph_objects as go
import numpy as np
from greedbot import generate_volatility_surface, GEXEngine, OptionContractData, IronCondor, MonteCarloEngine

st.set_page_config(page_title="GreedBot Quant Dashboard", layout="wide")
st.title("⚡ GreedBot Quantitative & Volatility Intelligence")

spot = st.sidebar.number_input("Underlying Spot Price ($)", value=580.0, step=1.0)
base_vol = st.sidebar.slider("Base Implied Volatility", min_value=0.05, max_value=1.00, value=0.20)

tab1, tab2, tab3 = st.tabs(["3D Volatility Surface", "Gamma Exposure (GEX)", "Monte Carlo VaR"])

with tab1:
    st.subheader("3D Implied Volatility Surface")
    surface = generate_volatility_surface(spot=spot, base_vol=base_vol)
    strikes = sorted(list(set(p['strike'] for p in surface)))
    dtes = sorted(list(set(p['dte'] for p in surface)))
    z = np.array([[next(p['iv'] for p in surface if p['strike']==k and p['dte']==d) for k in strikes] for d in dtes])
    fig = go.Figure(data=[go.Surface(z=z*100, x=strikes, y=dtes)])
    fig.update_layout(scene=dict(xaxis_title='Strike ($)', yaxis_title='DTE (Days)', zaxis_title='IV (%)'))
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Dealer Gamma Exposure (GEX) & Max Pain")
    engine = GEXEngine(spot=spot)
    contracts = [
        OptionContractData(strike=spot*0.95, is_call=False, open_interest=10000, dte=30, iv=base_vol),
        OptionContractData(strike=spot*1.05, is_call=True, open_interest=15000, dte=30, iv=base_vol)
    ]
    res = engine.calculate_gex(contracts)
    st.text(res.summary())

with tab3:
    st.subheader("Monte Carlo Stress-Testing & CVaR")
    mc = MonteCarloEngine(portfolio_value=100000.0, annual_volatility=base_vol, jump_intensity=0.5, jump_mean=-0.08, jump_vol=0.10)
    res = mc.run_simulation(days=30, num_simulations=2000)
    st.text(res.summary())
"""
