import pandas as pd
import numpy as np

class IPDASystem:
    def __init__(self, delta=0.7, tau_max=20):
        self.delta = delta        # Volatility decay threshold
        self.tau_max = tau_max    # Max bars in consolidation before expansion

    def compute_kernel(self, df):
        """Calculates L1 Compiler Ranges & λ1 Entrapment"""
        # 1. Structural Ranges (20, 40, 60 lookbacks)
        for lb in [20, 40, 60]:
            df[f'H{lb}'] = df['high'].rolling(lb).max()
            df[f'L{lb}'] = df['low'].rolling(lb).min()
        
        # 2. Equilibrium (The Fair Value Mean)
        df['Equilibrium'] = (df['H60'] + df['L60']) / 2
        
        # 3. Price Variation Integral (Vt) vs ATR Benchmark
        df['ATR20'] = df['high'].rolling(20).max() - df['low'].rolling(20).min()
        df['Vt'] = df['close'].diff().abs().rolling(20).sum()
        
        # 4. λ1: Phase Entrapment Score
        # If Vt/ATR < 0.7, latent energy H(t) is reaching critical mass
        df['lambda_1'] = np.where((df['Vt'] / df['ATR20']) < self.delta, 1, 0)
        
        # 5. Signal Logic: Expansion vs Reverse
        df['Signal'] = 'NEUTRAL'
        
        # EXPANSION: Critical mass reached + equilibrium presence
        df.loc[df['lambda_1'] == 1, 'Signal'] = 'EXPANSION_IMMINENT'
        
        # REVERSE: Price at L60 Extreme + λ1 Firing (Exhaustion)
        df.loc[(df['high'] >= df['H60']) & (df['lambda_1'] == 1), 'Signal'] = 'REVERSE_PERIOD'
        df.loc[(df['low'] <= df['L60']) & (df['lambda_1'] == 1), 'Signal'] = 'REVERSE_PERIOD'
        
        return df
