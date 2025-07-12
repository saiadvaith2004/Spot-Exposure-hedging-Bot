"""
Visualization helpers for analytics and risk reporting.

This module provides functions to plot correlation matrices and visualize risk metrics like VaR and drawdown.

Author: N SAI ADVAITH
"""

import numpy as np
import matplotlib.pyplot as plt

# --- Correlation Matrix Plot ---
def plot_correlation_matrix(price_dict):
   # Plot a correlation matrix for the given price dictionary.
    symbols = list(price_dict.keys())
    prices = np.array([price_dict[s] for s in symbols])
    corr = np.corrcoef(prices)
    plt.imshow(corr, cmap='coolwarm', interpolation='none')
    plt.colorbar()
    plt.xticks(range(len(symbols)), symbols, rotation=90)
    plt.yticks(range(len(symbols)), symbols)
    plt.title("Correlation Matrix")
    plt.tight_layout()
    plt.show()
# --- Enhanced Risk Metrics Visualization ---
def plot_var_drawdown(equity_curve):
   # Plot the equity curve with comprehensive risk metrics including VaR, drawdown, Sharpe ratio, and volatility.
   # Returns a BytesIO buffer containing the plot image.
    import matplotlib.pyplot as plt, io
    from risk_engine.metrics import calculate_var, calculate_max_drawdown
    
    # Calculate all risk metrics
    var = calculate_var(equity_curve)
    drawdown = calculate_max_drawdown(equity_curve)
    
    # Calculate additional risk metrics
    returns = np.diff(equity_curve) / equity_curve[:-1]  # Daily returns
    volatility = np.std(returns) * np.sqrt(252)  # Annualized volatility
    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
    max_drawdown_period = np.argmax(np.maximum.accumulate(equity_curve) - equity_curve)
    
    # Create enhanced plot with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # Main equity curve plot
    ax1.plot(equity_curve, label="Equity Curve", linewidth=2)
    ax1.axhline(y=equity_curve[0], color='gray', linestyle='--', alpha=0.7, label='Starting Value')
    ax1.axvline(x=max_drawdown_period, color='red', linestyle=':', alpha=0.7, label='Max Drawdown Point')
    ax1.set_title(f"Portfolio Performance & Risk Metrics")
    ax1.set_ylabel("Portfolio Value")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Risk metrics text box
    metrics_text = f"""Risk Metrics:
VaR (95%): {var:.2f}
Max Drawdown: {drawdown:.2%}
Volatility (Annual): {volatility:.2%}
Sharpe Ratio: {sharpe_ratio:.2f}
Current Value: {equity_curve[-1]:.2f}"""
    
    ax1.text(0.02, 0.98, metrics_text, transform=ax1.transAxes, 
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Drawdown plot
    running_max = np.maximum.accumulate(equity_curve)
    drawdown_series = (equity_curve - running_max) / running_max * 100
    ax2.fill_between(range(len(drawdown_series)), drawdown_series, 0, alpha=0.3, color='red')
    ax2.plot(drawdown_series, color='red', linewidth=1)
    ax2.set_title("Drawdown Over Time")
    ax2.set_xlabel("Time Period")
    ax2.set_ylabel("Drawdown (%)")
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return buf
