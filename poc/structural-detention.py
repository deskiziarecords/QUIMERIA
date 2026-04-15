import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class DetentionTelemetry:
    volatility_ratio: float
    is_detained: bool
    tau_stay: int
    delta_threshold: float = 0.7

class StructuralDetentionEngine:
    """
    Lambda 1 Sensor: Detects structural entrapment/detention.
    Triggers when Price Variation / ATR20 < 0.7 (The Critical Mass threshold).
    """
    def __init__(self, tau_max: int = 20, delta: float = 0.7):
        self.tau_max = tau_max  # Maximum allowed time in consolidation
        self.delta = delta      # Volatility decay threshold
        self.tau_stay = 0       # Counter for persistence
        self.history = []

    def calculate_variation_integral(self, prices: np.ndarray) -> float:
        """Calculates the sum of absolute price changes (Vt)."""
        return np.sum(np.abs(np.diff(prices)))

    def update(self, price_window: pd.Series, atr20: float) -> Dict:
        """
        Main monitor for structural detention.
        price_window: Current lookback window of prices.
        atr20: The current 20-period Average True Range.
        """
        prices = price_window.values
        v_t = self.calculate_variation_integral(prices)
        
        # Volatility Ratio Calculation: Vt / ATR20
        volatility_ratio = v_t / (atr20 + 1e-9)
        
        # Detection Logic: Is the market 'Detained'?
        is_detained = volatility_ratio < self.delta
        
        if is_detained:
            self.tau_stay += 1
        else:
            self.tau_stay = 0 # Reset on expansion
            
        # Critical Alert: Persistence exceeds tau_max
        critical_alert = is_detained and (self.tau_stay > self.tau_max)

        return {
            "volatility_ratio": round(volatility_ratio, 4),
            "is_detained": is_detained,
            "tau_stay": self.tau_stay,
            "alert": "CRITICAL_DETENTION" if critical_alert else "NOMINAL",
            "potential_energy": 0.5 * (self.tau_stay ** 2) # E = 1/2 * k * H(t)^2
        }
