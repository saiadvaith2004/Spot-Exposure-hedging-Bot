"""
Main entry point for Bybit orderbook fetching and simple delta calculation.

This script fetches the BTCUSDT orderbook from Bybit and logs the spot price and delta for a given position size.

Author: N SAI ADVAITH
"""

import logging
import requests
from utils.logger import logger

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# --- Configurable Parameters ---
position_size = 2  # TODO: Make position_size configurable via CLI or config file

# --- Bybit Orderbook Fetcher ---
def get_bybit_orderbook(symbol="BTCUSDT"):
    """
    Fetch the orderbook for a given symbol from Bybit.
    Returns the JSON response or None if there's an error.
    """
    try:
        url = f"https://api.bybit.com/v5/market/orderbook?category=linear&symbol={symbol}&limit=5"
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Exception in get_bybit_orderbook: {e}")
        return None

# --- Main Script Logic ---
if __name__ == "__main__":
    # Fetch the orderbook and calculate delta
    orderbook = get_bybit_orderbook("BTCUSDT")
    if orderbook is not None and orderbook.get("result") and orderbook["result"].get("a"):
        asks = orderbook['result']['a']
        spot_price = float(asks[0][0])  # Take the best ask price
        delta = position_size  # For now, delta is just the position size
        logging.info(f"Fetched Bybit BTC price: {spot_price}")
        logging.info(f"Calculated delta for position {position_size}: {delta}")
    else:
        logging.warning("Skipping risk calculation due to missing Bybit price data.")

