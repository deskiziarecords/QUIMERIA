# core/analysis/ipda_phase_detector.py
import pandas as pd
import numpy as np
from typing import Tuple, Dict

class IPDAPhaseDetector:
    """
    IPDA Phase Detector based on your 7ZERO-REVERSE / AEGIS implementation.
    Detects Accumulation, Manipulation, Distribution using multi-lookback ranges.
    Outputs phase + stay count for λ1 (Phase Entrapment) in ReversePeriodDetector.
    """
    
    def __init__(self,
                 short_lookback: int = 20,      # Most recent liquidity (your standard)
                 medium_lookback: int = 40,
                 long_lookback: int = 60,
                 accumulation_ratio: float = 0.65,   # Tight range = Accumulation
                 manipulation_breakout: float = 1.0): # Break above recent high
        
        self.short_lb = short_lookback
        self.medium_lb = medium_lookback
        self.long_lb = long_lookback
        self.acc_ratio = accumulation_ratio
        self.manip_break = manipulation_breakout
    
    def detect_phases(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Main method.
        df must contain: open, high, low, close (ideally daily or higher TF for classic IPDA)
        Returns enriched DataFrame with 'phase' and 'phase_stay_count'
        """
        if len(df) < self.long_lb:
            raise ValueError(f"Data too short for IPDA (need at least {self.long_lb} bars)")
        
        df = df.copy()
        
        # Core IPDA range calculations (liquidity pools)
        df['range_short']  = df['high'].rolling(self.short_lb).max()  - df['low'].rolling(self.short_lb).min()
        df['range_medium'] = df['high'].rolling(self.medium_lb).max() - df['low'].rolling(self.medium_lb).min()
        df['range_long']   = df['high'].rolling(self.long_lb).max()   - df['low'].rolling(self.long_lb).min()
        
        # Base phase assignment
        df['phase'] = 'Consolidation'
        
        # 1. Accumulation: Price trapped in tight range (classic IPDA consolidation)
        tight_range = df['range_short'] < df['range_medium'] * self.acc_ratio
        df.loc[tight_range, 'phase'] = 'Accumulation'
        
        # 2. Manipulation: False breakout / Judas swing (stop hunt above recent highs)
        recent_high = df['high'].rolling(5).max().shift(1)
        breakout_up = (df['close'] > recent_high * (1 + self.manip_break * 0.001)) & (df['phase'].shift(1) == 'Accumulation')
        df.loc[breakout_up, 'phase'] = 'Manipulation'
        
        # 3. Distribution: Breakdown after manipulation (real move or reversal)
        recent_low = df['low'].rolling(5).min().shift(1)
        breakdown = (df['close'] < recent_low * (1 - self.manip_break * 0.001)) & (df['phase'].shift(1) == 'Manipulation')
        df.loc[breakdown, 'phase'] = 'Distribution'
        
        # Phase stay counter (critical for λ1: Phase Entrapment)
        df['phase_change'] = (df['phase'] != df['phase'].shift(1)).astype(int)
        df['phase_stay_count'] = df.groupby(df['phase_change'].cumsum()).cumcount() + 1
        
        # Optional: Add simple liquidity imbalance hint (for better reverse detection)
        df['liquidity_imbalance'] = (df['high'].rolling(10).max() - df['close']) / (df['range_short'].replace(0, np.nan))
        
        return df
    
    def get_current_state(self, df: pd.DataFrame) -> Dict:
        """Convenience method for dashboard / real-time display"""
        if df.empty:
            return {"phase": "Unknown", "stay_count": 0, "range_short": 0.0}
        
        last = df.iloc[-1]
        return {
            "phase": last['phase'],
            "stay_count": int(last['phase_stay_count']),
            "range_short": float(last.get('range_short', 0)),
            "range_medium": float(last.get('range_medium', 0))
        }
