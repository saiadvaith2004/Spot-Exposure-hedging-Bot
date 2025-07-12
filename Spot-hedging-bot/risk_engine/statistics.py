import numpy as np

def calculate_correlation(prices1, prices2):
    return np.corrcoef(prices1, prices2)[0, 1]

def calculate_beta(spot_returns, perp_returns):
    cov = np.cov(spot_returns, perp_returns)
    beta = cov[0, 1] / np.var(perp_returns)
    return beta
