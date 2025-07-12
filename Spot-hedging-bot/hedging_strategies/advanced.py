import matplotlib.pyplot as plt
import io

def iron_condor(qty, lower_put_strike, lower_put_price, lower_call_strike, lower_call_price, upper_call_strike, upper_call_price, upper_put_strike, upper_put_price):
    prices = [lower_put_strike * 0.8 + i * (upper_call_strike * 1.2 - lower_put_strike * 0.8) / 100 for i in range(101)]
    payoff = []
    for S in prices:
        result = 0
        result += max(lower_put_strike - S, 0) - lower_put_price
        result -= max(S - lower_call_strike, 0) - lower_call_price
        result -= max(S - upper_call_strike, 0) - upper_call_price
        result += max(upper_put_strike - S, 0) - upper_put_price
        payoff.append(qty * result)
    return prices, payoff

def butterfly(qty, lower_strike, lower_price, mid_strike, mid_price, upper_strike, upper_price):
    prices = [lower_strike * 0.8 + i * (upper_strike * 1.2 - lower_strike * 0.8) / 100 for i in range(101)]
    payoff = []
    for S in prices:
        result = 0
        result += max(S - lower_strike, 0) - lower_price
        result -= 2 * (max(S - mid_strike, 0) - mid_price)
        result += max(S - upper_strike, 0) - upper_price
        payoff.append(qty * result)
    return prices, payoff

def straddle(qty, strike, call_price, put_price):
    prices = [strike * 0.5 + i * (strike * 1.5 - strike * 0.5) / 100 for i in range(101)]
    payoff = []
    for S in prices:
        result = max(S - strike, 0) + max(strike - S, 0) - call_price - put_price
        payoff.append(qty * result)
    return prices, payoff
