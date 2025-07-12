#This module provides functions to compute realized, unrealized, and total P&L from a trade log and price history, with support for trading fees and slippage.
def compute_pnl(trade_log, price_history, fee_rate=0.0, slippage_rate=0.0):
    # Calculate realized, unrealized, and total P&L for a set of trades, including fees and slippage.
    pnl = 0
    realized = 0
    unrealized = 0
    total_fees = 0
    total_slippage = 0
    for trade in trade_log:
        symbol = trade['symbol']
        qty = trade['qty']
        price = trade['price']
        side = trade['side']
        # Use the latest price for unrealized P&L
        current_price = price_history[symbol][-1]
        trade_value = abs(qty * price)
        fee = trade_value * fee_rate
        slippage = trade_value * slippage_rate
        total_fees += fee
        total_slippage += slippage
        if side.lower() == 'buy':
            # Buying: cash outflow, unrealized gain if price rises
            realized -= qty * price + fee + slippage
            unrealized += qty * (current_price - price)
        else:
            # Selling: cash inflow, unrealized loss if price rises
            realized += qty * price - fee - slippage
            unrealized -= qty * (current_price - price)
    pnl = realized + unrealized
    return {
        "realized": realized,
        "unrealized": unrealized,
        "total": pnl,
        "total_fees": total_fees,
        "total_slippage": total_slippage
    }

def compute_multi_leg_pnl(trade_legs, price_history, fee_rate=0.0, slippage_rate=0.0):
    # Calculate P&L for multi-leg trades (e.g., spreads, straddles, iron condors).
    total_realized = 0
    total_unrealized = 0
    total_fees = 0
    total_slippage = 0
    leg_pnls = []
    for leg in trade_legs:
        symbol = leg['symbol']
        qty = leg['qty']
        price = leg['price']
        side = leg['side']
        leg_type = leg.get('leg_type', 'spot')  
        current_price = price_history[symbol][-1]
        trade_value = abs(qty * price)
        fee = trade_value * fee_rate
        slippage = trade_value * slippage_rate
        # Calculate leg-specific P&L
        if side.lower() == 'buy':
            realized = -(qty * price + fee + slippage)
            unrealized = qty * (current_price - price)
        else:
            realized = qty * price - fee - slippage
            unrealized = -(qty * (current_price - price))
        total_realized += realized
        total_unrealized += unrealized
        total_fees += fee
        total_slippage += slippage
        leg_pnls.append({
            'symbol': symbol,
            'leg_type': leg_type,
            'realized': realized,
            'unrealized': unrealized,
            'total': realized + unrealized
        })
    return {
        "realized": total_realized,
        "unrealized": total_unrealized,
        "total": total_realized + total_unrealized,
        "total_fees": total_fees,
        "total_slippage": total_slippage,
        "legs": leg_pnls
    }

def compute_portfolio_pnl(positions, price_history, fee_rate=0.0, slippage_rate=0.0):
    #Calculate portfolio-level P&L with position sizing and correlation adjustments.
    portfolio_realized = 0
    portfolio_unrealized = 0
    total_fees = 0
    total_slippage = 0
    position_pnls = {}
    for symbol, position in positions.items():
        qty = position['qty']
        avg_price = position['avg_price']
        side = position['side']
        current_price = price_history[symbol][-1]
        trade_value = abs(qty * avg_price)
        fee = trade_value * fee_rate
        slippage = trade_value * slippage_rate
        if side.lower() == 'long':
            realized = -(qty * avg_price + fee + slippage)
            unrealized = qty * (current_price - avg_price)
        else:  # short
            realized = qty * avg_price - fee - slippage
            unrealized = -(qty * (current_price - avg_price))
        portfolio_realized += realized
        portfolio_unrealized += unrealized
        total_fees += fee
        total_slippage += slippage
        position_pnls[symbol] = {
            'realized': realized,
            'unrealized': unrealized,
            'total': realized + unrealized,
            'current_price': current_price,
            'avg_price': avg_price
        }
    # Calculate portfolio risk metrics
    total_pnl = portfolio_realized + portfolio_unrealized
    portfolio_value = sum(pos['qty'] * price_history[sym][-1] for sym, pos in positions.items())
    return {
        "realized": portfolio_realized,
        "unrealized": portfolio_unrealized,
        "total": total_pnl,
        "total_fees": total_fees,
        "total_slippage": total_slippage,
        "portfolio_value": portfolio_value,
        "positions": position_pnls
    }