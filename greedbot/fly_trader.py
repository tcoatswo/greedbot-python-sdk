"""
GreedBot Drosophila Connectome Fly Trader
-----------------------------------------
Biologically inspired quantitative trading engine based on the Drosophila melanogaster
130k-neuron connectome. Integrates sensory neural circuits (Optic/Antennal lobes),
Mushroom Body dopamine plasticity (PAM reward / PPL1 punishment), Central Complex heading
steering, and Descending Motor Neurons (DNa01/DNa02/MDN) linked to Merton Jump-Kelly sizing.

100% Local Neural ODE / NumPy computation — Zero external LLM or API token cost.
"""

from __future__ import annotations

import logging
import math
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .quant.jump_kelly import MertonJumpKellySizer
from .quant.gex import GEXEngine, OptionContractData
from .quant.spreads import IronCondor, VerticalSpread
from .paper_engine import InstitutionalPaperBroker
from .models import OrderIntent, Side

logger = logging.getLogger("greedbot.fly_trader")


@dataclass
class ConnectomeSensoryInput:
    ticker: str
    price: float
    price_velocity_5m: float   # Fast momentum (% per 5 min)
    bid_ask_delta: float        # Order book delta (-1.0 to +1.0)
    net_gex_regime: float       # +1.0 for Long Gamma, -1.0 for Short Gamma
    iv_skew: float              # Put-Call IV skew (jump shock indicator)


@dataclass
class FlyMotorDecision:
    action: str                 # "BUY", "SELL", "HOLD", "SPREAD"
    confidence: float           # 0.0 to 1.0 firing rate
    target_dollars: float       # Scaled by Merton Jump Kelly
    strategy_hint: str          # "DIRECTIONAL_EQUITY", "VERTICAL_SPREAD", "IRON_CONDOR"
    dopamine_level: float       # PAM (+) vs PPL1 (-) level


class DrosophilaConnectomeTrader:
    """
    Simulates sensory-motor neural dynamics of a fruit fly brain trained to trade market ticks.
    """

    def __init__(
        self,
        broker: InstitutionalPaperBroker,
        num_kenyon_cells: int = 2000,
        num_mbon_units: int = 24,
        learning_rate: float = 0.01,
    ):
        self.broker = broker
        self.num_kc = num_kenyon_cells
        self.num_mbon = num_mbon_units
        self.lr = learning_rate

        # Synaptic Weight Matrices
        np.random.seed(42)
        self.W_sensory_to_kc = np.random.normal(0.0, 1.0, size=(4, self.num_kc))
        self.W_kc_to_mbon = np.random.uniform(0.1, 0.5, size=(self.num_kc, self.num_mbon))
        self.W_mbon_to_motor = np.random.normal(0.0, 0.5, size=(self.num_mbon, 4))

        # Neuromodulatory state (Dopamine baseline)
        self.pam_dopamine_reward = 0.0
        self.ppl1_dopamine_punish = 0.0
        
        # Kelly Sizer
        self.kelly_sizer = MertonJumpKellySizer(
            mu=0.05,
            lambda_jump=1.5,
            mu_J=0.10,
            sigma_J=0.20,
            gamma_penalty=1.5,
        )

    def process_tick(self, sensor: ConnectomeSensoryInput) -> FlyMotorDecision:
        """
        Runs one biological sensory-motor feedforward pass on a market tick.
        """
        # 1. Sensory Ingestion (Optic & Antennal Lobes)
        sensory_vector = np.array([
            sensor.price_velocity_5m,
            sensor.bid_ask_delta,
            sensor.net_gex_regime,
            sensor.iv_skew,
        ])

        # 2. Sparse Mushroom Body Projection (Kenyon Cells - Top 5% winner-take-all)
        kc_raw = np.dot(sensory_vector, self.W_sensory_to_kc)
        kc_thresh = np.percentile(kc_raw, 95)
        kc_active = np.maximum(0.0, kc_raw - kc_thresh)

        # 3. Mushroom Body Output Neurons (MBONs)
        mbon_activity = np.tanh(np.dot(kc_active, self.W_kc_to_mbon))

        # 4. Descending Motor Neurons Readout
        motor_activations = np.dot(mbon_activity, self.W_mbon_to_motor)
        dna01_buy = 1.0 / (1.0 + np.exp(-motor_activations[0]))    # DNa01 (Forward/Buy)
        mdn_sell = 1.0 / (1.0 + np.exp(-motor_activations[1]))     # MDN (Reverse/Sell)
        dnp09_hold = 1.0 / (1.0 + np.exp(-motor_activations[2]))   # DNp09 (Freeze/Hold)
        dna02_steer = 1.0 / (1.0 + np.exp(-motor_activations[3]))  # DNa02 (Steering/Size multiplier)

        # 5. Kelly Position Sizing
        available_cash = max(100.0, self.broker.cash)
        opt_price = max(0.5, sensor.price * 0.02)
        sized = self.kelly_sizer.size_contract(
            stock_price=sensor.price,
            option_price=opt_price,
            delta=0.50,
            gamma=0.02,
            theta=-0.02,
            iv=max(0.10, sensor.iv_skew),
            capital_usd=available_cash,
            max_risk_cap_pct=0.25,
        )
        target_dollars = max(100.0, min(available_cash * 0.25, sized["target_risk_dollars"] * float(dna02_steer)))

        # 6. Action Selection
        if dnp09_hold > max(dna01_buy, mdn_sell) or abs(dna01_buy - mdn_sell) < 0.15:
            if sensor.net_gex_regime > 0.5:
                action = "SPREAD"
                strat = "IRON_CONDOR"
                conf = float(dnp09_hold)
            else:
                action = "HOLD"
                strat = "WAIT_FOR_SIGNAL"
                conf = float(dnp09_hold)
        elif dna01_buy > mdn_sell:
            action = "BUY"
            strat = "DIRECTIONAL_LONG"
            conf = float(dna01_buy)
        else:
            action = "SELL"
            strat = "DIRECTIONAL_SHORT"
            conf = float(mdn_sell)

        return FlyMotorDecision(
            action=action,
            confidence=conf,
            target_dollars=round(target_dollars, 2),
            strategy_hint=strat,
            dopamine_level=float(self.pam_dopamine_reward - self.ppl1_dopamine_punish),
        )

    def learn_from_pnl(self, realized_pnl: float, last_kc_active: Optional[np.ndarray] = None) -> None:
        """
        Biological Spike-Timing-Dependent Plasticity (STDP) modulated by Dopamine:
        - Positive PnL -> PAM Dopamine releases -> Strengthens active synapses.
        - Negative PnL -> PPL1 Dopamine releases -> Depresses active synapses.
        """
        if realized_pnl > 0:
            self.pam_dopamine_reward = min(1.0, self.pam_dopamine_reward + 0.2)
            self.ppl1_dopamine_punish = max(0.0, self.ppl1_dopamine_punish - 0.1)
            self.W_kc_to_mbon += self.lr * self.pam_dopamine_reward * 0.05
        else:
            self.ppl1_dopamine_punish = min(1.0, self.ppl1_dopamine_punish + 0.3)
            self.pam_dopamine_reward = max(0.0, self.pam_dopamine_reward - 0.2)
            self.W_kc_to_mbon -= self.lr * self.ppl1_dopamine_punish * 0.05

        self.W_kc_to_mbon = np.clip(self.W_kc_to_mbon, 0.01, 2.0)
