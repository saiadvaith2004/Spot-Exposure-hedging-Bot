#This module provides functions for aggregating Greeks across positions and performing stress tests.

def aggregate_greeks(positions):
   # Sum up all Greeks (delta, gamma, theta, vega) across all positions in the portfolio.
    total = {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}
    for pos in positions.values():
        for greek in total:
            if greek in pos:
                total[greek] += pos[greek]
            elif greek == "delta" and "position_size" in pos:
                # Use position_size as delta if no explicit delta is provided
                total["delta"] += pos["position_size"]
    return total

def stress_test(user_positions, price_shock_pct):
   # Perform a stress test by applying a price shock to all positions.
    results = {}
    for symbol, pos in user_positions.items():
        # Apply the price shock to delta (simplified model)
        shocked_delta = pos["delta"] * (1 + price_shock_pct / 100)
        results[symbol] = shocked_delta
    return results
