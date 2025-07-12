import numpy as np

def calculate_var(returns, confidence=0.99):
    return np.percentile(returns, (1 - confidence) * 100)

def calculate_max_drawdown(equity_curve):
    peak = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - peak) / peak
    return drawdown.min()
