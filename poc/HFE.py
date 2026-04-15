import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class TokenState:
    letter: str
    description: str
    rarity_score: float

class HighFidelityEncoder:
    """
    High-Fidelity Symbolic Encoder: Transforms OHLCV -> A-Z Token Stream.
    Uses 3-dimensional geometric quantization (3x3x3 = 27 states, clipped to 26).
    """
    def __init__(self):
        # A-Z mapping based on (Direction, Body Strength, Wick Asymmetry)
        self.alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.letter_map = self._generate_letter_map()

    def _generate_letter_map(self) -> Dict[int, str]:
        # Mapping geometric indices to the English alphabet [4, 6]
        return {i: self.alphabet[i] for i in range(26)}

    def encode_candle(self, open_p, high_p, low_p, close_p, atr) -> str:
        """
        Quantizes a single candle into its geometric state [6, 7].
        """
        body = close_p - open_p
        abs_body = abs(body)
        candle_range = high_p - low_p
        
        # Dimension 1: Direction (Bull, Neutral, Bear)
        if abs_body < (0.1 * atr): direction = 1  # Neutral
        elif body > 0: direction = 0              # Bull
        else: direction = 2                       # Bear

        # Dimension 2: Body Strength (Small, Medium, Large) [6]
        if abs_body < (0.3 * atr): strength = 0   # Small
        elif abs_body < (0.7 * atr): strength = 1 # Medium
        else: strength = 2                        # Large

        # Dimension 3: Wick Asymmetry (Lower, Balanced, Upper)
        upper_wick = high_p - max(open_p, close_p)
        lower_wick = min(open_p, close_p) - low_p
        wick_diff = upper_wick - lower_wick
        
        if abs(wick_diff) < (0.1 * atr): wick = 1 # Balanced
        elif wick_diff > 0: wick = 2              # Upper-dominant
        else: wick = 0                            # Lower-dominant

        # Calculate Composite Index: (dir * 9) + (str * 3) + wick
        composite_idx = (direction * 9) + (strength * 3) + wick
        
        # Clip to 26 for A-Z mapping [6]
        final_idx = min(composite_idx, 25)
        return self.letter_map[final_idx]

    def get_token_stream(self, df: pd.DataFrame, atr_period=14) -> List[str]:
        """
        Converts a DataFrame of OHLCV into a continuous token string [3].
        """
        # Calculate ATR for normalization [4]
        high_low = df['high'] - df['low']
        high_cp = np.abs(df['high'] - df['close'].shift())
        low_cp = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        atr = tr.rolling(window=atr_period).mean().fillna(tr)

        tokens = []
        for i in range(len(df)):
            token = self.encode_candle(
                df['open'].iloc[i], df['high'].iloc[i], 
                df['low'].iloc[i], df['close'].iloc[i], 
                atr.iloc[i]
            )
            tokens.append(token)
        return tokens

