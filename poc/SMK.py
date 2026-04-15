"""
Sovereign Market Kernel - Refactored (Pure NumPy Version)
Removes JAX anti-patterns, fixes mathematical bugs, ensures type safety.
"""

import numpy as np
from scipy.fft import rfft, rfftfreq, angle
from dataclasses import dataclass
from typing import Dict, Union, List
from enum import IntEnum, auto

# --- ENUMS FOR TYPE SAFETY ---
class MarketPhase(IntEnum):
    ACCUMULATION = 0
    MANIPULATION = 1
    DISTRIBUTION = 2

class GateState(IntEnum):
    HALTED = 0
    ACTIVE = 1

class TradeIntent(IntEnum):
    BUY = auto()
    SELL = auto()
    NEUTRAL = auto()

# --- MATHEMATICAL CONSTANTS & CORE STATE ---
@dataclass(frozen=True)
class KernelState:
    """Immutable state container. Create new instance instead of mutating."""
    phase: MarketPhase = MarketPhase.ACCUMULATION
    gate: GateState = GateState.ACTIVE
    severity_score: float = 0.0
    is_privileged: bool = False

    def with_gate(self, gate: GateState) -> "KernelState":
        return KernelState(
            phase=self.phase,
            gate=gate,
            severity_score=self.severity_score,
            is_privileged=self.is_privileged
        )

# --- LAYER 1: IPDA COMPILER ---
class IPDACompiler:
    """Defines structural arena via lookbacks. Pure numpy, no side effects."""

    DEFAULT_LOOKBACKS = [8, 20, 40]

    def __init__(self, lookbacks: List[int] = None):
        self.lookbacks = lookbacks or self.DEFAULT_LOOKBACKS
        self._ranges = {}
        self._equilibrium = 0.0

    def update(self, price_history: np.ndarray) -> Dict:
        if len(price_history) < max(self.lookbacks):
            raise ValueError(f"Need at least {max(self.lookbacks)} price points")

        ranges = {}
        for lb in self.lookbacks:
            window = price_history[-lb:]
            ranges[lb] = {
                'high': float(np.max(window)),
                'low': float(np.min(window)),
                'mid': float((np.max(window) + np.min(window)) / 2)
            }

        equilibrium = float(np.mean([r['mid'] for r in ranges.values()]))
        self._ranges = ranges
        self._equilibrium = equilibrium

        return {
            "ranges": ranges,
            "equilibrium": equilibrium,
            "range_volatility": float(np.std([r['high'] - r['low'] for r in ranges.values()]))
        }

    def get_equilibrium(self) -> float:
        return self._equilibrium

# --- LAYER 2: DARK POOL MEMORY ---
class DarkPoolMemory:
    """Tracks latent institutional energy. Uses pure numpy."""

    def __init__(self, normalization_factor: float = 1000.0):
        self.normalization = normalization_factor
        self._cumulative_delta = 0.0
        self._hidden_inventory = 0.0

    def update(self, buy_vol: float, sell_vol: float) -> Dict:
        delta = buy_vol - sell_vol
        self._cumulative_delta += delta
        self._hidden_inventory = float(np.tanh(self._cumulative_delta / self.normalization))

        return {
            "hidden_inventory": self._hidden_inventory,
            "cumulative_delta": self._cumulative_delta,
            "current_delta": delta
        }

    def get_energy(self) -> float:
        return self._hidden_inventory

# --- LAYER 4 & 5: RISK GATING ENGINE ---
class RiskGatingEngine:
    """Implements 7-λ Risk Matrix with proper type safety."""

    LAMBDA_WEIGHTS = np.array([0.35, 0.25, 0.20, 0.15, 0.05])

    def __init__(self):
        self._weights = self.LAMBDA_WEIGHTS.copy()

    def check_lambda6_veto(
        self, open_p: float, high: float, low: float, 
        close: float, atr: float, intent: TradeIntent
    ) -> bool:
        range_size = high - low
        if range_size < 1e-9:
            return False

        body_ratio = abs(close - open_p) / range_size
        range_expansion = range_size > (1.2 * atr)

        is_bullish = close > open_p
        is_bearish = close < open_p

        conflict = False
        if intent == TradeIntent.BUY and is_bearish:
            conflict = True
        elif intent == TradeIntent.SELL and is_bullish:
            conflict = True

        return (body_ratio > 0.75) and range_expansion and conflict

    def check_lambda3_spectral(
        self, window: np.ndarray, equilibrium: float, sample_rate: float = 1.0
    ) -> Dict:
        if len(window) < 4:
            return {"fired": False, "phase_diff": 0.0, "dominant_freq": 0.0}

        centered = window - equilibrium
        fft_vals = rfft(centered)
        freqs = rfftfreq(len(window), d=sample_rate)
        magnitudes = np.abs(fft_vals)

        if len(magnitudes) <= 1:
            return {"fired": False, "phase_diff": 0.0, "dominant_freq": 0.0}

        dominant_idx = np.argmax(magnitudes[1:]) + 1
        dominant_freq = float(freqs[dominant_idx])
        phi_dominant = float(angle(fft_vals[dominant_idx]))
        reference_phase = 0.0
        phase_diff = abs(phi_dominant - reference_phase)
        phase_diff = min(phase_diff, 2 * np.pi - phase_diff)
        fired = phase_diff > (np.pi / 2)

        return {
            "fired": fired,
            "phase_diff": float(phase_diff),
            "dominant_freq": dominant_freq,
            "dominant_phase": phi_dominant
        }

# --- LAYER 6: CENTRAL BANK OVERRIDE ---
class CentralBankKernel:
    DEFAULT_SENTIMENT_THRESHOLD = -0.9
    DEFAULT_VOLATILITY_THRESHOLD = 5.0

    def __init__(self, sentiment_threshold: float = None, vol_threshold: float = None):
        self.sentiment_threshold = sentiment_threshold or self.DEFAULT_SENTIMENT_THRESHOLD
        self.vol_threshold = vol_threshold or self.DEFAULT_VOLATILITY_THRESHOLD

    def check_intervention(self, news_sentiment: float, vol_spike: float) -> bool:
        return (news_sentiment < self.sentiment_threshold) or (vol_spike > self.vol_threshold)

# --- OBNFE: BAYESIAN FUSION ENGINE ---
class OBNFEEngine:
    def __init__(self, alpha: float = 0.90, tau: float = 0.65, prior_failure: float = 0.05):
        self.alpha = alpha
        self.tau = tau
        self.posterior = prior_failure
        self._history = []

    def update(self, lambdas: np.ndarray) -> float:
        if not isinstance(lambdas, np.ndarray):
            lambdas = np.array(lambdas)

        pi_t = self.alpha * self.posterior + (1 - self.alpha) * (1 - self.posterior)

        p_fire_given_failure = 0.8
        p_fire_given_normal = 0.1

        likelihood_failure = np.prod(np.where(lambdas == 1, p_fire_given_failure, 1 - p_fire_given_failure))
        likelihood_normal = np.prod(np.where(lambdas == 1, p_fire_given_normal, 1 - p_fire_given_normal))

        numerator = pi_t * likelihood_failure
        denominator = numerator + (1 - pi_t) * likelihood_normal

        if denominator < 1e-10:
            self.posterior = 0.5
        else:
            self.posterior = float(numerator / denominator)

        self._history.append({"lambdas": lambdas.copy(), "posterior": self.posterior, "prior": pi_t})
        return self.posterior

    def should_halt(self) -> bool:
        return self.posterior > self.tau

    def get_history(self) -> List[dict]:
        return self._history.copy()

# --- TICK DATA STRUCTURE ---
@dataclass
class TickData:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    buy_vol: float
    sell_vol: float
    atr: float
    sentiment: float
    vol_spike: float
    intent: TradeIntent
    history: np.ndarray
    window: np.ndarray

    @classmethod
    def from_dict(cls, data: dict) -> "TickData":
        intent_map = {"BUY": TradeIntent.BUY, "SELL": TradeIntent.SELL, "NEUTRAL": TradeIntent.NEUTRAL}
        intent = intent_map.get(data.get("intent", "NEUTRAL"), TradeIntent.NEUTRAL)

        return cls(
            timestamp=float(data.get("timestamp", 0)),
            open=float(data["open"]),
            high=float(data["high"]),
            low=float(data["low"]),
            close=float(data["close"]),
            volume=float(data.get("volume", 0)),
            buy_vol=float(data["buy_vol"]),
            sell_vol=float(data["sell_vol"]),
            atr=float(data["atr"]),
            sentiment=float(data["sentiment"]),
            vol_spike=float(data["vol_spike"]),
            intent=intent,
            history=np.array(data["history"]),
            window=np.array(data["window"])
        )

# --- UNIFIED SOVEREIGN MARKET KERNEL ---
class SovereignMarketKernel:
    FAILURE_THRESHOLD = 0.65

    def __init__(
        self,
        ipda_lookbacks: List[int] = None,
        obnfe_alpha: float = 0.90,
        obnfe_tau: float = 0.65,
        cb_sentiment_threshold: float = -0.9,
        cb_vol_threshold: float = 5.0
    ):
        self.l1 = IPDACompiler(lookbacks=ipda_lookbacks)
        self.l2 = DarkPoolMemory()
        self.risk = RiskGatingEngine()
        self.l6 = CentralBankKernel(
            sentiment_threshold=cb_sentiment_threshold,
            vol_threshold=cb_vol_threshold
        )
        self.obnfe = OBNFEEngine(alpha=obnfe_alpha, tau=obnfe_tau)
        self.state = KernelState()
        self._tick_count = 0

    def tick(self, data: Union[TickData, dict]) -> Dict:
        if isinstance(data, dict):
            tick_data = TickData.from_dict(data)
        else:
            tick_data = data

        self._tick_count += 1

        # 1. Privileged Check (Layer 6)
        if self.l6.check_intervention(tick_data.sentiment, tick_data.vol_spike):
            self.state = self.state.with_gate(GateState.HALTED)
            return {
                "tick_id": self._tick_count,
                "u_t": GateState.HALTED.value,
                "phase": MarketPhase.ACCUMULATION.value,
                "status": "HALTED: PRIVILEGED_OVERRIDE",
                "posterior": 1.0,
                "equilibrium": self.l1.get_equilibrium(),
                "energy": self.l2.get_energy(),
                "halt_reason": "central_bank_intervention"
            }

        # 2. Structural & Memory Mapping (L1, L2)
        l1_data = self.l1.update(tick_data.history)
        l2_data = self.l2.update(tick_data.buy_vol, tick_data.sell_vol)

        # 3. Risk Matrix Evaluation
        l3_result = self.risk.check_lambda3_spectral(tick_data.window, l1_data["equilibrium"])
        l3_fired = l3_result["fired"]

        l6_veto = self.risk.check_lambda6_veto(
            tick_data.open, tick_data.high, tick_data.low,
            tick_data.close, tick_data.atr, tick_data.intent
        )

        # 4. Bayesian Consensus (OBNFE)
        current_lambdas = np.array([0, 0, 1 if l3_fired else 0, 0, 0])
        p_failure = self.obnfe.update(current_lambdas)

        # 5. Causal Gate Enforcement
        halt_conditions = [
            p_failure > self.FAILURE_THRESHOLD,
            self.obnfe.should_halt(),
            l6_veto,
            l3_fired
        ]

        if any(halt_conditions):
            self.state = self.state.with_gate(GateState.HALTED)
            status = "HALTED: GEOMETRY_BREAK"
            halt_reasons = []
            if p_failure > self.FAILURE_THRESHOLD:
                halt_reasons.append("high_failure_probability")
            if self.obnfe.should_halt():
                halt_reasons.append("exceeds_tau")
            if l6_veto:
                halt_reasons.append("lambda6_veto")
            if l3_fired:
                halt_reasons.append("lambda3_spectral")
        else:
            self.state = self.state.with_gate(GateState.ACTIVE)
            status = "EXECUTING: NOMINAL"
            halt_reasons = []

        return {
            "tick_id": self._tick_count,
            "u_t": self.state.gate.value,
            "phase": self.state.phase.value,
            "status": status,
            "posterior": float(p_failure),
            "equilibrium": l1_data["equilibrium"],
            "energy": l2_data["hidden_inventory"],
            "phase_diff": l3_result.get("phase_diff", 0.0),
            "dominant_freq": l3_result.get("dominant_freq", 0.0),
            "halt_reasons": halt_reasons if halt_reasons else None,
            "lambdas": current_lambdas.tolist(),
            "l6_veto": l6_veto,
            "l3_fired": l3_fired
        }

    def reset(self):
        self.state = KernelState()
        self._tick_count = 0
        self.l2 = DarkPoolMemory()
        self.obnfe = OBNFEEngine()

    def get_diagnostics(self) -> dict:
        return {
            "tick_count": self._tick_count,
            "current_state": {
                "phase": self.state.phase.name,
                "gate": self.state.gate.name,
                "severity": self.state.severity_score
            },
            "obnfe_history": self.obnfe.get_history()[-10:]
        }

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    kernel = SovereignMarketKernel()

    np.random.seed(42)
    n_history = 50
    base_price = 100.0
    returns = np.random.normal(0.0001, 0.01, n_history)
    price_history = base_price * np.exp(np.cumsum(returns))

    for i in range(10):
        current_price = price_history[-1]

        tick_dict = {
            "timestamp": float(i),
            "open": current_price * (1 + np.random.normal(0, 0.001)),
            "high": current_price * (1 + abs(np.random.normal(0, 0.002))),
            "low": current_price * (1 - abs(np.random.normal(0, 0.002))),
            "close": current_price,
            "volume": 1000.0,
            "buy_vol": 600.0,
            "sell_vol": 400.0,
            "atr": 1.5,
            "sentiment": 0.0,
            "vol_spike": 1.0,
            "intent": "BUY",
            "history": price_history,
            "window": price_history[-20:]
        }

        result = kernel.tick(tick_dict)
        print(f"Tick {result['tick_id']}: {result['status']} (p={result['posterior']:.3f}, u_t={result['u_t']})")

        price_history = np.append(price_history, current_price * (1 + np.random.normal(0.0001, 0.01)))

    print("\nDiagnostics:")
    print(kernel.get_diagnostics())
