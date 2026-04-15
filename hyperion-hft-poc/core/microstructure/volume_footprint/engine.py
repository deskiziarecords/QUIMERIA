# core/microstructure/volume_footprint/engine.py
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN
from typing import Dict, Any, Optional
import warnings
warnings.filterwarnings("ignore")


class VolumeFootprintEngine:
    """
    Consolidated Volume Footprint Engine for Hyperion HFT PoC.
    Implements the 5 novel approaches, focused on forex (no true volume).
    Outputs enriched features that feed directly into:
      - IPDAPhaseDetector
      - ReversePeriodDetector (λ1, λ5 especially benefit from volume)
      - Symbolic Encoder (adds volume_score tokens)
    """

    def __init__(self,
                 baseline_vol: float = 12000,
                 atr_period: int = 20,
                 dbscan_eps_ms: int = 60,
                 dbscan_min_samples: int = 5,
                 num_price_levels: int = 25):
        
        self.baseline_vol = baseline_vol
        self.atr_period = atr_period
        self.dbscan_eps_ms = dbscan_eps_ms
        self.dbscan_min_samples = dbscan_min_samples
        self.num_price_levels = num_price_levels

    # ===================================================================
    # 5. PREV - Price-Range Expansion Volume (fastest fallback)
    # ===================================================================
    def _prev_synthetic(self, ohlc: pd.DataFrame) -> pd.DataFrame:
        """Pure price-based synthetic volume with conviction"""
        df = ohlc.copy()
        df['tr'] = np.maximum.reduce([
            df['high'] - df['low'],
            np.abs(df['high'] - df['close'].shift()),
            np.abs(df['low'] - df['close'].shift())
        ])
        df['atr'] = df['tr'].rolling(self.atr_period).mean()
        df['range'] = df['high'] - df['low']
        df['body'] = np.abs(df['close'] - df['open'])
        df['wick_ratio'] = (df['range'] - df['body']) / df['range'].replace(0, np.nan)
        df['wick_ratio'] = df['wick_ratio'].fillna(0).clip(0, 1)

        df['synthetic_volume'] = (
            (df['range'] / df['atr'].replace(0, 1)) *
            (1 - df['wick_ratio']) *
            self.baseline_vol
        ).fillna(self.baseline_vol)

        # Distribute volume across price levels inside each candle
        footprint = []
        for idx, row in df.iterrows():
            if row['range'] <= 0:
                footprint.append({'time': idx, 'price': row['close'], 'volume': row['synthetic_volume'], 'method': 'PREV'})
                continue
            levels = np.linspace(row['low'], row['high'], self.num_price_levels)
            vol_per_level = row['synthetic_volume'] / self.num_price_levels
            for lvl in levels:
                footprint.append({
                    'time': idx,
                    'price': round(lvl, 5),
                    'volume': vol_per_level,
                    'method': 'PREV',
                    'conviction': float(1 - row['wick_ratio'])
                })
        return pd.DataFrame(footprint)

    # ===================================================================
    # 1. Tick Velocity (burst detection)
    # ===================================================================
    def _tick_velocity(self, ticks: pd.DataFrame, candle_duration: str = '5min') -> pd.DataFrame:
        """Detect institutional bursts via timing clustering"""
        df = ticks.copy()
        df['delta_ms'] = df.index.to_series().diff().dt.total_seconds() * 1000
        
        features = np.column_stack((
            df['delta_ms'].fillna(1000),
            (df['price'] * 10000).astype(int)
        ))
        
        db = DBSCAN(eps=self.dbscan_eps_ms, min_samples=self.dbscan_min_samples).fit(features)
        df['burst_id'] = db.labels_
        
        footprint = df.groupby([pd.Grouper(freq=candle_duration), pd.Grouper(key='price', freq='0.0001')]).agg(
            burst_count=('burst_id', lambda x: (x >= 0).sum()),
            avg_intertick=('delta_ms', 'mean'),
            tick_count=('price', 'count')
        ).reset_index()
        
        footprint['velocity_score'] = footprint['burst_count'] / (footprint['avg_intertick'].replace(0, 1000) + 1)
        return footprint

    # ===================================================================
    # Main unified method (used by dashboard)
    # ===================================================================
    def generate_footprint(self,
                           ohlc: pd.DataFrame,
                           ticks: Optional[pd.DataFrame] = None,
                           use_method: str = 'hybrid') -> Dict[str, Any]:
        """
        Returns footprints ready for IPDA + ReversePeriodDetector.
        """
        results = {}

        # Always compute PREV (most reliable fallback)
        if use_method in ['hybrid', 'prev']:
            results['prev'] = self._prev_synthetic(ohlc)

        # Tick velocity when ticks are available
        if use_method in ['hybrid', 'velocity'] and ticks is not None:
            results['tick_velocity'] = self._tick_velocity(ticks)

        # Enrich main footprint with volume_score (B/I/X/U/D/W,w) for Symbolic Encoder
        main_fp = results.get('prev')
        if main_fp is not None and not main_fp.empty:
            main_fp['volume_score'] = pd.qcut(
                main_fp['volume'], 
                q=7, 
                labels=['B', 'I', 'X', 'U', 'D', 'W', 'w'],
                duplicates='drop'
            )
            results['enriched'] = main_fp

        return results

    def get_volume_features(self, ohlc: pd.DataFrame) -> pd.DataFrame:
        """Quick method for ReversePeriodDetector and risk gates"""
        fp = self.generate_footprint(ohlc=ohlc, use_method='prev')
        return fp.get('enriched', pd.DataFrame())
