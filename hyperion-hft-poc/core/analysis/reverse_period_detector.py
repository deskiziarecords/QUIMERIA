import pandas as pd
import numpy as np
from scipy.fft import fft, fftfreq
from typing import Tuple, Dict

class ReversePeriodDetector:
    """
    Full mathematical Reverse Period Detector as specified.
    Detects alpha inversion across phase, temporal, spectral, confluence, and liquidity domains.
    Triggers kill switch when structural coherence breaks.
    """
    
    def __init__(self,
                 tau_max: int = 8,           # max stay in Distribution before suspicion
                 delta: float = 0.65,        # low variation threshold for entrapment
                 gamma: float = 0.3,         # sign agreement threshold
                 theta: float = 0.55,        # overall severity threshold
                 weights: list = None):
        
        self.tau_max = tau_max
        self.delta = delta
        self.gamma = gamma
        self.theta = theta
        self.weights = np.array(weights or [0.25, 0.15, 0.30, 0.20, 0.10])  # λ3 (spectral) highest weight
    
    def compute_atr(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        tr = np.maximum.reduce([
            df['high'] - df['low'],
            np.abs(df['high'] - df['close'].shift()),
            np.abs(df['low'] - df['close'].shift())
        ])
        return tr.rolling(period).mean()
    
    def compute_liquidity_gradient(self, df: pd.DataFrame, window: int = 10) -> pd.Series:
        """∇U_t = d(P*V)/dt approximated"""
        U = df['close'] * df.get('synthetic_volume', 10000)  # use PREV volume if available
        return U.diff().rolling(window).mean()
    
    def detect_spectral_inversion(self, price_series: pd.Series, window: int = 64) -> pd.Series:
        """λ₃: Phase inversion via FFT (dominant mode)"""
        inversions = pd.Series(index=price_series.index, dtype=float)
        for i in range(window, len(price_series)):
            segment = price_series.iloc[i-window:i].values
            if len(segment) < window:
                continue
            fft_vals = fft(segment)
            freqs = fftfreq(window)
            dominant_idx = np.argmax(np.abs(fft_vals[1:])) + 1  # skip DC
            phase = np.angle(fft_vals[dominant_idx])
            inversions.iloc[i] = abs(phase)
        return (inversions > np.pi / 2).astype(int)
    
    def detect(self, df: pd.DataFrame) -> Dict:
        """
        df must have columns: open, high, low, close, synthetic_volume (from VolumeFootprintEngine)
        Returns enriched df + reverse metrics
        """
        df = df.copy()
        
        # Core computations
        df['atr20'] = self.compute_atr(df, 20)
        df['returns'] = np.log(df['close']) - np.log(df['close'].shift())
        df['variation'] = df['close'].diff().abs().rolling(10).sum()
        df['liquidity_grad'] = self.compute_liquidity_gradient(df)
        df['liquidity_grad_hist'] = df['liquidity_grad'].shift(5).rolling(10).mean()
        
        # IPDA Phase (simplified — replace with your full IPDA if available)
        df['phase'] = 'Consolidation'
        df.loc[df['variation'] < df['atr20'] * 0.7, 'phase'] = 'Accumulation'
        df.loc[(df['close'] > df['high'].rolling(5).max().shift(1)), 'phase'] = 'Manipulation'
        df.loc[(df['close'] < df['low'].rolling(5).min().shift(1)) & (df['phase'] == 'Manipulation'), 'phase'] = 'Distribution'
        
        # Stay counter in Distribution
        df['tau_stay'] = (df['phase'] == 'Distribution').astype(int).groupby((df['phase'] != 'Distribution').cumsum()).cumsum()
        
        # λ indicators
        df['lambda1'] = ((df['phase'] == 'Distribution') & 
                        (df['tau_stay'] > self.tau_max) & 
                        (df['variation'] / df['atr20'] < self.delta)).astype(int)
        
        df['lambda2'] = ((df.get('killzone', 0) == 1) & 
                        (df['returns'].rolling(8).apply(lambda x: np.mean(np.sign(x))) < self.gamma)).astype(int)
        
        df['lambda3'] = self.detect_spectral_inversion(df['close'])
        
        df['lambda4'] = ((df.get('confluence', 0.5) > 0.6) & 
                        (df['returns'].rolling(10).mean() < 0)).astype(int)
        
        df['lambda5'] = (df['liquidity_grad'] * df['liquidity_grad_hist'] < 0).astype(int)
        
        # Unified Reverse Trigger & Severity Score
        df['reverse_trigger'] = (df[['lambda1','lambda2','lambda3','lambda4','lambda5']].sum(axis=1) > 0).astype(int)
        df['reverse_score'] = (df[['lambda1','lambda2','lambda3','lambda4','lambda5']] * self.weights).sum(axis=1)
        df['reverse_active'] = (df['reverse_score'] > self.theta).astype(int)
        
        # Action: Reset phase & halt execution on reverse
        df['execution_halt'] = df['reverse_active']
        df.loc[df['reverse_active'] == 1, 'phase'] = 'Reverse Detected - Reset'
        
        metrics = {
            'current_reverse_score': df['reverse_score'].iloc[-1],
            'reverse_active': bool(df['reverse_active'].iloc[-1]),
            'dominant_lambda': df[['lambda1','lambda2','lambda3','lambda4','lambda5']].iloc[-1].idxmax(),
            'current_phase': df['phase'].iloc[-1]
        }
        
        return df, metrics
