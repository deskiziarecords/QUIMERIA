import jax
import jax.numpy as jnp
from typing import Dict, Tuple

class OBNFEEngine:
    """
    OBNFE: Online Bayesian Network Fusion Engine.
    Functions as the Bayesian Kill Switch for detecting Reverse Regimes.
    """
    def __init__(self, alpha_persist: float = 0.90, tau_halt: float = 0.65):
        self.alpha = alpha_persist  # Regime persistence parameter
        self.tau = tau_halt         # Bayesian Halt Threshold
        # Transition Matrix P: [[Normal->Normal, Normal->Reverse], [Reverse->Normal, Reverse->Reverse]]
        self.P = jnp.array([[self.alpha, 1 - self.alpha], 
                             [1 - self.alpha, self.alpha]])
        self.posterior_z1 = 0.05    # Initial belief of being in Reverse Period

    @jax.jit
    def update_posterior(self, lambda_firings: jnp.ndarray, theta: jnp.ndarray, phi: jnp.ndarray) -> float:
        """
        Performs Bayesian Recursive Update.
        lambda_firings: Binary array of 7-lambda sensor states.
        theta: Sensor reliability in Reverse Regime (P(Li=1 | Z=1)).
        phi: Sensor noise floor in Normal Regime (P(Li=1 | Z=0)).
        """
        # 1. Calculate Markov Prior (Prediction Step)
        pi_t = self.alpha * self.posterior_z1 + (1 - self.alpha) * (1 - self.posterior_z1)
        
        # 2. Likelihood of being in Reverse (Z=1) vs Normal (Z=0)
        # Likelihood = Product(P(sensor_i | regime))
        likelihood_z1 = jnp.prod(jnp.where(lambda_firings == 1, theta, 1 - theta))
        likelihood_z0 = jnp.prod(jnp.where(lambda_firings == 1, phi, 1 - phi))
        
        # 3. Apply Bayes' Rule (Update Step)
        numerator = pi_t * likelihood_z1
        denominator = (pi_t * likelihood_z1) + ((1 - pi_t) * likelihood_z0)
        
        new_posterior = numerator / (denominator + 1e-9)
        return new_posterior

    def validate_regime(self, lambdas: Dict[str, bool]) -> Dict:
        # Convert dict to jnp array for JAX processing
        firing_bits = jnp.array([float(v) for v in lambdas.values()])
        
        # Static weights for demonstration; in prod, these are learned
        theta = jnp.array([0.8, 0.7, 0.9, 0.75, 0.85, 0.6, 0.5]) # Reliability
        phi = jnp.array([0.1, 0.15, 0.05, 0.2, 0.1, 0.05, 0.02]) # Noise
        
        self.posterior_z1 = self.update_posterior(firing_bits, theta, phi)
        
        status = "NOMINAL" if self.posterior_z1 < self.tau else "CRITICAL: REVERSE REGIME"
        u_t = 0 if self.posterior_z1 >= self.tau else 1
        
        return {
            "posterior_probability": float(self.posterior_z1),
            "status": status,
            "u_t": u_t,
            "risk_multiplier": 1.0 if self.posterior_z1 <= 0.20 else 0.0 if self.posterior_z1 > 0.65 else 0.5
        }

