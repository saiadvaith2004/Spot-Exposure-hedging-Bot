# This module provides functions to route orders across multiple exchanges and estimate transaction costs.
from api_clients.bybit import get_bybit_orderbook
from api_clients.okx import get_okx_orderbook
from api_clients.deribit import get_deribit_options  

# --- Transaction Cost Estimation ---
def estimate_transaction_cost(orderbook, qty, fee_rate=0.0006):
    # Estimate total transaction cost including slippage and fees.
    slippage = estimate_slippage(orderbook, qty)
    # Calculate mid price from best bid and ask
    mid_price = (float(orderbook['result']['a'][0][0]) + float(orderbook['result']['b'][0][0])) / 2
    fee = qty * mid_price * fee_rate
    return {"slippage": slippage, "fee": fee, "total_cost": slippage * qty + fee}

def estimate_slippage(orderbook, qty, side="buy"):
    # Estimate slippage by walking the orderbook.
    if side == "buy":
        levels = orderbook['result']['a']  # Asks for buying
        best_price = float(levels[0][0])
    else:
        levels = orderbook['result']['b']  # Bids for selling
        best_price = float(levels[0][0])
    qty_remaining = qty
    total_cost = 0.0
    qty_filled = 0.0
    for price, size, *_ in levels:
        price = float(price)
        size = float(size)
        if qty_remaining <= size:
            # Fill remaining quantity at this level
            total_cost += qty_remaining * price
            qty_filled += qty_remaining
            break
        else:
            # Fill entire level and continue
            total_cost += size * price
            qty_filled += size
            qty_remaining -= size
    # Check if we have sufficient liquidity
    if qty_filled < qty:
        return None
    # Calculate average execution price and slippage
    avg_exec_price = total_cost / qty
    slippage_percent = (avg_exec_price - best_price) / best_price
    return slippage_percent

def smart_order_router(symbol, side, qty, price=None):
    # Route orders to the best venue based on price and liquidity.
    # Fetch orderbooks from multiple venues
    bybit_ob = get_bybit_orderbook(symbol)
    okx_ob = get_okx_orderbook(symbol.replace("USDT", "-USDT-SWAP")) 
    deribit_ob = get_deribit_options(symbol) 
    venues = []
    # Check Bybit availability and pricing
    if bybit_ob and bybit_ob.get("result"):
        if side.lower() == "buy":
            price_bybit = float(bybit_ob["result"]["a"][0][0])
        else:
            price_bybit = float(bybit_ob["result"]["b"][0][0])
        venues.append(("Bybit", price_bybit))
    # Check OKX availability and pricing
    if okx_ob and okx_ob.get("data"):
        ob = okx_ob["data"][0]
        if side.lower() == "buy":
            price_okx = float(ob["asks"][0][0])
        else:
            price_okx = float(ob["bids"][0][0])
        venues.append(("OKX", price_okx))
    # Check Deribit availability (placeholder for options)
    if deribit_ob and deribit_ob.get("result"):
        # TODO: Implement options pricing logic
        pass  
    # Select best venue based on side
    if side.lower() == "buy":
        best = min(venues, key=lambda x: x[1])  # Lowest price for buying
    else:
        best = max(venues, key=lambda x: x[1])  # Highest price for selling
    print(f"Routing {side.upper()} order for {qty} {symbol} to {best[0]} at price {best[1]}")
    return {"venue": best[0], "price": best[1], "status": "simulated"}
