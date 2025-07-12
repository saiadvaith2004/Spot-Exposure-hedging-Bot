"""
Bybit API client utilities.

This module provides simple wrappers for placing orders and fetching orderbook data from Bybit.

Author: N SAI ADVAITH
"""

import requests
import logging
from utils.logger import logger
import os
from dotenv import load_dotenv
import time
import hmac
import hashlib
import json

# --- Environment Setup ---
load_dotenv()
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

# --- Helper: Generate Bybit Signature ---
def _generate_signature(api_secret, params):
    """
    Generate HMAC SHA256 signature for Bybit API requests.
    """
    param_str = "&".join([f"{k}={params[k]}" for k in sorted(params)])
    return hmac.new(api_secret.encode('utf-8'), param_str.encode('utf-8'), hashlib.sha256).hexdigest()

# --- Order Placement ---
def place_bybit_order(symbol, side, qty, price=None, order_type="Market", demo=True):
    """
    Place an order on Bybit. If demo=True, just print the order; if False, send a real order with authentication.

    Args:
        symbol (str): Trading symbol, e.g., 'BTCUSDT'.
        side (str): 'Buy' or 'Sell'.
        qty (float or int): Quantity to trade.
        price (float or None): Limit price (if None, market order is used).
        order_type (str): 'Market' or 'Limit'. Defaults to 'Market'.
        demo (bool): If True, do not send real order. If False, send real order to Bybit.
    Returns:
        dict: Order response or error details.
    """
    url = "https://api.bybit.com/v5/order/create"
    data = {
        "category": "linear",
        "symbol": symbol,
        "side": side.upper(),  # Bybit expects 'BUY' or 'SELL'
        "orderType": order_type,
        "qty": str(qty),
    }
    if price:
        data["price"] = str(price)  # Only include price for limit orders
    if demo:
        print(f"[DEMO] Placing {side} order for {qty} {symbol} at {price if price else 'market'}")
        return {"status": "demo", "order": data}
    try:
        # Add required authentication fields
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        body = json.dumps(data)
        sign_params = {
            "api_key": BYBIT_API_KEY,
            "timestamp": timestamp,
            "recvWindow": recv_window,
            "body": body
        }
        # Bybit v5 signature: sign = HMAC_SHA256(secret, preHash)
        pre_hash = timestamp + BYBIT_API_KEY + recv_window + body
        signature = hmac.new(BYBIT_API_SECRET.encode('utf-8'), pre_hash.encode('utf-8'), hashlib.sha256).hexdigest()
        headers = {
            "X-BAPI-API-KEY": BYBIT_API_KEY,
            "X-BAPI-SIGN": signature,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json"
        }
        resp = requests.post(url, headers=headers, data=body)
        try:
            resp.raise_for_status()
        except Exception as http_err:
            logger.error(f"HTTP error: {http_err}, Response: {resp.text}")
            return {"status": "error", "error": str(http_err), "response": resp.text}
        result = resp.json()
        # Check for Bybit API-level errors
        if result.get("retCode", 0) != 0:
            logger.error(f"Bybit API error: {result}")
            return {"status": "error", "error": result}
        return {"status": "success", "order": result}
    except Exception as e:
        logger.error(f"Exception in place_bybit_order: {e}")
        return {"status": "error", "error": str(e)}

# --- Orderbook Fetching ---
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
