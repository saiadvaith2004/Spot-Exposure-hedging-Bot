#This module provides functions for calculating various risk metrics including VaR and option Greeks.
from utils.logger import logger
import numpy as np
import math

def calculate_var(returns, confidence=0.99):
    # Calculate Value at Risk (VaR) for a given confidence level.
    try:
        return np.percentile(returns, (1 - confidence) * 100)
    except Exception as e:
        logger.error(f"Exception in calculate_var: {e}")
        return None

def _normal_cdf(x):
    #Standard normal cumulative distribution function.
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def _normal_pdf(x):
    #Standard normal probability density function.
    return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)

def _black_scholes_d1_d2(S, K, T, r, sigma):
    #Calculate d1 and d2 for Black-Scholes formula.
    d1 = (math.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*math.sqrt(T))
    d2 = d1 - sigma*math.sqrt(T)
    return d1, d2

def calculate_gamma(option_data):
    # Calculate Gamma (second derivative of option price with respect to underlying price).
    try:
        S = option_data['S']  # Current stock price
        K = option_data['K']  # Strike price
        T = option_data['T']  # Time to expiration (in years)
        r = option_data['r']  # Risk-free rate
        sigma = option_data['sigma']  # Volatility
        option_type = option_data.get('option_type', 'call')
        d1, d2 = _black_scholes_d1_d2(S, K, T, r, sigma)
        gamma = _normal_pdf(d1) / (S * sigma * math.sqrt(T))
        return gamma
    except Exception as e:
        logger.error(f"Exception in calculate_gamma: {e}")
        return 0.0

def calculate_theta(option_data):
   # Calculate Theta (rate of change of option price with respect to time).
    try:
        S = option_data['S']
        K = option_data['K']
        T = option_data['T']
        r = option_data['r']
        sigma = option_data['sigma']
        option_type = option_data.get('option_type', 'call')
        d1, d2 = _black_scholes_d1_d2(S, K, T, r, sigma)
        if option_type.lower() == 'call':
            theta = (-S * _normal_pdf(d1) * sigma / (2 * math.sqrt(T)) 
                    - r * K * math.exp(-r * T) * _normal_cdf(d2))
        else:  # put
            theta = (-S * _normal_pdf(d1) * sigma / (2 * math.sqrt(T)) 
                    + r * K * math.exp(-r * T) * _normal_cdf(-d2))
        return theta
    except Exception as e:
        logger.error(f"Exception in calculate_theta: {e}")
        return 0.0

def calculate_vega(option_data):
    # Calculate Vega (rate of change of option price with respect to volatility).
    try:
        S = option_data['S']
        K = option_data['K']
        T = option_data['T']
        r = option_data['r']
        sigma = option_data['sigma']
        option_type = option_data.get('option_type', 'call')
        d1, d2 = _black_scholes_d1_d2(S, K, T, r, sigma)
        vega = S * math.sqrt(T) * _normal_pdf(d1)
        return vega
    except Exception as e:
        logger.error(f"Exception in calculate_vega: {e}")
        return 0.0
