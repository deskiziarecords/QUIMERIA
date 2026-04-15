import numpy as np
from scipy.fft import rfft, angle
from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class RiskTelemetry:
    lambdas: Dict[str, bool] = field(default_factory=dict)
    r_score: float = 0.0
    u_t: int = 1  # 1 = Authorized, 0 = Halted
    status: str = "NOMINAL"

class MetacognitiveShield:
    """
    7-λ Risk Matrix: The Veto Authority of the Sovereign Market Kernel.
    Enforces the 'Golden Rule of Survival': Halt if geometry breaks.
    """
    def __init__(self, thresholds: dict = None):
        self.weights = np.array([0.25, 0.15, 0.30, 0.15, 0.10, 0.05, 0.00]) # Example institutional weights
        self.tau_halt = 0.65 # Severity threshold for u_t = 0
        self.thresholds = thresholds or {
            "v_ratio": 0.7, 
            "phase_limit": np.pi / 2, 
            "body_ratio": 0.75,
            "dxy_div": 0.2
        }

    def evaluate_matrix(self, market_data: dict, ipda_context: dict) -> RiskTelemetry:
        l = {}
        # λ1: Phase Entrapment - Volatility ratio < 0.7 [10]
        l['lambda1'] = (market_data['vol_integral'] / market_data['atr20']) < self.thresholds['v_ratio']
        
        # λ2: Temporal Alignment - Killzone failure/drift [11]
        l['lambda2'] = market_data['is_killzone'] and (market_data['vol_decay'] > 0.5)
        
        # λ3: Spectral Inversion - FFT Phase > pi/2 [12]
        phi_l5 = angle(rfft(market_data['price_window'])[13])
        l['lambda3'] = np.abs(phi_l5 - ipda_context['phi_l1']) > self.thresholds['phase_limit']
        
        # λ4: Confluence Collapse - High confidence, negative expectancy [14]
        l['lambda4'] = market_data['conf_score'] > 0.6 and market_data['expected_pnl'] < 0
        
        # λ5: Potential Gradient - Liquidity field inversion (dot product < 0) [14]
        l['lambda5'] = np.dot(market_data['grad_u'], market_data['grad_u_hist']) < 0
        
        # λ6: Displacement Veto - Large body (>75%) conflicting with intent [15, 16]
        l['lambda6'] = (market_data['body_ratio'] > self.thresholds['body_ratio']) and \
                       (market_data['direction'] != ipda_context['intent'])
        
        # λ7: Macro Causality - DXY divergence check [17]
        l['lambda7'] = (ipda_context['pair'] == "EUR_USD") and \
                       (market_data['dxy_change'] > self.thresholds['dxy_div']) and \
                       (ipda_context['intent'] == "BUY")

        # R-Score: Weighted Summation [18]
        firing_bits = np.array([float(val) for val in l.values()])
        r_score = np.sum(firing_bits * self.weights[:len(firing_bits)])
        
        # Control Logic: u_t = 0 if R-Score > 0.65 or λ6/λ3 Veto [15, 19]
        u_t = 0 if (r_score > self.tau_halt or l['lambda6'] or l['lambda3']) else 1
        
        status = "HALTED" if u_t == 0 else "NOMINAL"
        if l['lambda6']: status += ": DISPLACEMENT VETO"
        elif l['lambda3']: status += ": SPECTRAL INVERSION"

        return RiskTelemetry(lambdas=l, r_score=r_score, u_t=u_t, status=status)

