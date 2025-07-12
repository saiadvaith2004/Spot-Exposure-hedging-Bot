# This module provides functions to calculate delta for various position types and hedging scenarios.
from utils.logger import logger
import math

def calculate_delta(position_size, spot_price, hedge_price, instrument_type="spot", option_data=None):
    # Calculate the delta of a position with support for different instrument types.
    if instrument_type == "spot":
        # For spot positions, delta is simply the position size
        return position_size
    elif instrument_type == "futures":
        # For futures, delta is position size (1:1 relationship)
        return position_size
    elif instrument_type in ["call", "put"]:
        # For options, calculate delta using Black-Scholes Greeks
        if option_data is None:
            logger.warning("Option data not provided, using position size as delta")
            return position_size
        try:
            from risk_engine.greeks import get_greeks
            option_type = "c" if instrument_type == "call" else "p"
            greeks = get_greeks(
                option_type,
                option_data.get('S', spot_price),
                option_data.get('K', spot_price),
                option_data.get('T', 1.0),
                option_data.get('r', 0.02),
                option_data.get('sigma', 0.3)
            )
            # Delta for options includes both the option delta and position size
            option_delta = greeks.get('delta', 0)
            return position_size * option_delta
        except Exception as e:
            logger.error(f"Error calculating option delta: {e}")
            return position_size
    elif instrument_type == "portfolio":
        # For portfolio delta, sum up all individual deltas
        if isinstance(position_size, dict):
            total_delta = 0
            for symbol, pos_size in position_size.items():
                # Recursively calculate delta for each position
                pos_delta = calculate_delta(pos_size, spot_price, hedge_price, "spot")
                total_delta += pos_delta
            return total_delta
        else:
            return position_size
    else:
        logger.warning(f"Unknown instrument type: {instrument_type}, using position size as delta")
        return position_size

def calculate_hedge_delta(current_delta, target_delta=0):
    # Calculate the required hedge size to achieve target delta.
    hedge_size = target_delta - current_delta
    return hedge_size

def calculate_delta_exposure(positions, spot_prices):
    # Calculate total delta exposure across multiple positions.
    total_delta = 0
    for symbol, position in positions.items():
        pos_size = position.get('size', 0)
        instrument_type = position.get('type', 'spot')
        spot_price = spot_prices.get(symbol, 0)
        option_data = position.get('option_data')
        pos_delta = calculate_delta(pos_size, spot_price, spot_price, instrument_type, option_data)
        total_delta += pos_delta
    return total_delta
