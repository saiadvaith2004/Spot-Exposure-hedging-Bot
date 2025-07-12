# This module provides functions to calculate option Greeks (delta, gamma, theta, vega) using the Black-Scholes model.
from py_vollib.black_scholes.greeks.analytical import delta, gamma, theta, vega # type: ignore
from py_vollib.black_scholes.implied_volatility import implied_volatility # type: ignore
import logging

logger = logging.getLogger(__name__)

# --- Greeks Calculation ---
def get_greeks(option_type, S, K, t, r, sigma):
   # Calculate all option Greeks using the Black-Scholes model.
    try:
        # Calculate all Greeks using py_vollib's analytical functions
        return {
            "delta": delta(option_type, S, K, t, r, sigma),
            "gamma": gamma(option_type, S, K, t, r, sigma),
            "theta": theta(option_type, S, K, t, r, sigma),
            "vega": vega(option_type, S, K, t, r, sigma)
        }
    except Exception as e:
        logger.error(f"Error calculating greeks: {e}")
        # Return zero Greeks if calculation fails
        return {'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0}
