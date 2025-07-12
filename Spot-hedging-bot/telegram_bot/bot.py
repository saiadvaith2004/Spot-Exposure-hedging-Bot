"""
Telegram Bot for Portfolio Risk Management and Hedging

This bot allows users to monitor crypto positions, visualize risk, simulate options strategies, and execute hedges via Bybit.
"""

import asyncio
import json
import logging
import os
import requests
import ccxt
import matplotlib.pyplot as plt
import io
import numpy as np
import pandas as pd
from risk_engine.portfolio import aggregate_greeks
from hedging_strategies.advanced import collar, straddle
from hedging_strategies.advanced import iron_condor, butterfly, straddle
from analytics.visualizations import plot_correlation_matrix
import matplotlib.pyplot as plt
from delta_neutral import compute_hedge_size 
from risk_engine.greeks import get_greeks
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)
from api_clients.bybit import place_bybit_order, get_bybit_orderbook
from utils.storage import save_positions, load_positions, log_trade
from utils.logger import logger
from order_execution.smart_router import estimate_slippage
import time

# --- Global State ---
monitoring_tasks = {}
positions = load_positions()  # Load user positions from storage
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
price_dict = {}

# --- Visualization Utilities ---
# plot_var_drawdown: Plots the equity curve and annotates with VaR and max drawdown

def plot_var_drawdown(equity_curve):
    # equity_curve: list or np.array of portfolio equity values over time
    import matplotlib.pyplot as plt, io
    from risk_engine.metrics import calculate_var, calculate_max_drawdown
    var = calculate_var(equity_curve)  # Calculate Value at Risk
    drawdown = calculate_max_drawdown(equity_curve)  # Calculate max drawdown
    plt.figure(figsize=(8,4))
    plt.plot(equity_curve, label="Equity Curve")
    plt.title(f"VaR: {var:.2f}, Max Drawdown: {drawdown:.2%}")
    plt.legend()
    buf = io.BytesIO()  # Create a buffer to hold the image
    plt.savefig(buf, format='png')  # Save the plot to the buffer
    buf.seek(0)  # Rewind buffer to the beginning
    plt.close()  # Close the plot to free memory
    return buf  # Returns a BytesIO buffer containing the plot image

# fetch_historical_prices: Fetches historical price data for a given symbol from Binance using ccxt

def fetch_historical_prices(symbol, limit=100):
    exchange = ccxt.binance()
    # Fetch OHLCV data (Open, High, Low, Close, Volume)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=limit)
    # Extract closing prices from OHLCV data
    closes = [candle[4] for candle in ohlcv]
    return closes  # List of closing prices

# --- Price Data Initialization ---
for symbol in symbols:
    prices = fetch_historical_prices(symbol, limit=100) 
    price_dict[symbol] = prices
symbols = ["BTC/USDT", "ETH/USDT"]
price_dict = {}
for symbol in symbols:
    price_dict[symbol.replace("/", "")] = fetch_historical_prices(symbol)

# --- Telegram Bot Command Handlers ---

async def simulate_strategy(update, context):
    # Simulate and plot payoff for options strategies: iron_condor, butterfly, straddle.
    try:
        args = context.args
        strategy = args[0].lower()
        if strategy == "iron_condor":
            qty = float(args[1])
            lp_strike, lp_price = float(args[2]), float(args[3])
            lc_strike, lc_price = float(args[4]), float(args[5])
            uc_strike, uc_price = float(args[6]), float(args[7])
            up_strike, up_price = float(args[8]), float(args[9])
            prices, payoff = iron_condor(qty, lp_strike, lp_price, lc_strike, lc_price, uc_strike, uc_price, up_strike, up_price)
            title = f"Iron Condor Payoff"
        elif strategy == "butterfly":
            qty = float(args[1])
            lower_strike, lower_price = float(args[2]), float(args[3])
            mid_strike, mid_price = float(args[4]), float(args[5])
            upper_strike, upper_price = float(args[6]), float(args[7])
            prices, payoff = butterfly(qty, lower_strike, lower_price, mid_strike, mid_price, upper_strike, upper_price)
            title = f"Butterfly Payoff"
        elif strategy == "straddle":
            qty = float(args[1])
            strike = float(args[2])
            call_price = float(args[3])
            put_price = float(args[4])
            prices, payoff = straddle(qty, strike, call_price, put_price)
            title = f"Straddle Payoff"
        else:
            await update.message.reply_text("Supported: iron_condor, butterfly, straddle")
            return
        buf = io.BytesIO()
        plt.figure(figsize=(8,4))
        plt.plot(prices, payoff)
        plt.title(title)
        plt.xlabel("Underlying Price")
        plt.ylabel("Payoff")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        await update.message.reply_photo(photo=buf, caption=f"{strategy.capitalize()} payoff chart")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}\nUsage:\n"
            "/simulate_strategy iron_condor <qty> <lp_strike> <lp_price> <lc_strike> <lc_price> <uc_strike> <uc_price> <up_strike> <up_price>\n"
            "/simulate_strategy butterfly <qty> <lower_strike> <lower_price> <mid_strike> <mid_price> <upper_strike> <upper_price>\n"
            "/simulate_strategy straddle <qty> <strike> <call_price> <put_price>")

async def correlation_chart(update, context):
    # Generate and send a correlation matrix chart for a set of crypto symbols.
    chat_id = update.effective_chat.id
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    price_dict = {}
    for symbol in symbols:
        try:
            price_dict[symbol.replace("/", "")] = fetch_historical_prices(symbol, limit=100)
        except Exception as e:
            await update.message.reply_text(f"Error fetching prices for {symbol}: {e}")
            return
    df = pd.DataFrame(price_dict)
    corr_matrix = df.corr()
    buf = io.BytesIO()
    plt.figure(figsize=(6, 5))
    plt.imshow(corr_matrix.values, cmap='coolwarm', interpolation='none')
    plt.colorbar()
    plt.xticks(range(len(corr_matrix.columns)), corr_matrix.columns, rotation=45)
    plt.yticks(range(len(corr_matrix.index)), corr_matrix.index)
    plt.title("Correlation Matrix")
    plt.tight_layout()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    await update.message.reply_photo(photo=buf, caption="Portfolio correlation matrix")

async def risk_chart(update, context):
    # Plot and send a bar chart of position deltas for the user.
    chat_id = update.effective_chat.id
    user_positions = positions.get(chat_id, {})
    deltas = [pos.get("delta", 0) for pos in user_positions.values()]
    labels = list(user_positions.keys())
    plt.figure(figsize=(8, 4))
    plt.bar(labels, deltas)
    plt.title("Position Deltas")
    plt.xlabel("Asset")
    plt.ylabel("Delta")
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    await update.message.reply_photo(photo=buf, caption="Your position deltas")
async def hedge_history(update, context):
    # Shows the hedge history for a given asset and timeframe.
    chat_id = update.effective_chat.id
    try:
        asset = context.args[0].upper()
        timeframe = context.args[1]
        with open("trade_logs.json", "r") as f:
            logs = json.load(f)
        user_logs = logs.get(str(chat_id), [])
        asset_logs = [t for t in user_logs if t["asset"] == asset]
        msg = f"Hedge history for {asset}:\n"
        for trade in asset_logs:
            msg += f"{trade}\n"
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Exception in hedge_history: {e}")
        await update.message.reply_text("Usage: /hedge_history <asset> <timeframe>")

async def monitor_position(chat_id, symbol, position_size, threshold, app):
    # Monitors a position for a user and triggers a hedge if the delta exceeds the threshold.
    target_delta = 0
    hedge_fraction = 1.0  # Fraction of delta to hedge
    last_hedge_time = 0  # Track last hedge to avoid spam
    hedge_cooldown = 300  # 5 minutes between hedges
    while True:
        try:
            price = get_bybit_price(symbol)
            delta = position_size  # For now, delta is just the position size
            current_time = time.time()
            # If the delta exceeds the threshold, compute the hedge size and execute
            if abs(delta - target_delta) > threshold and (current_time - last_hedge_time) > hedge_cooldown:
                hedge_size = compute_hedge_size(delta - target_delta, hedge_fraction)  
                # Determine hedge direction (sell if long, buy if short)
                hedge_side = "Sell" if delta > target_delta else "Buy"
                # Place the hedge order
                hedge_result = place_bybit_order(symbol, hedge_side, abs(hedge_size), demo=False)   
                if hedge_result and hedge_result.get("status") == "success":
                    # Log successful hedge
                    logger.info(f"Hedge executed: {hedge_side} {abs(hedge_size)} {symbol}")
                    last_hedge_time = current_time
                    # Notify user via Telegram
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=f"🛡️ Hedge Executed!\n"
                             f"Symbol: {symbol}\n"
                             f"Action: {hedge_side}\n"
                             f"Size: {abs(hedge_size):.4f}\n"
                             f"Price: {price:.2f}\n"
                             f"New Delta: {delta - hedge_size:.4f}"
                    )
                else:
                    # Log failed hedge
                    error_msg = hedge_result.get("error", "Unknown error") if hedge_result else "No response"
                    logger.error(f"Hedge failed for {symbol}: {error_msg}") 
                    # Notify user of hedge failure
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=f"Hedge Failed!\n"
                             f"Symbol: {symbol}\n"
                             f"Error: {error_msg}\n"
                             f"Current Delta: {delta:.4f}"
                    )
            await asyncio.sleep(30)  # Wait before checking again
        except Exception as e:
            logger.error(f"Error in dynamic rebalancing: {e}")
            await asyncio.sleep(30)
async def add_option(update, context):
    # Add an option position for the user and calculate Greeks.
    chat_id = update.effective_chat.id
    try:
        symbol = context.args[0].upper()
        position_size = float(context.args[1])
        threshold = float(context.args[2])
        S = float(context.args[3])         # Spot price
        K = float(context.args[4])         # Strike price
        t = float(context.args[5])         # Time to expiry
        r = float(context.args[6])         # Risk-free rate
        sigma = float(context.args[7])     # Volatility
        option_type = context.args[8]      # 'call' or 'put'
        greeks = get_greeks(option_type, S, K, t, r, sigma)
        # Store the position and Greeks for the user
        positions.setdefault(chat_id, {})
        positions[chat_id][symbol] = {
            "position_size": position_size,
            "threshold": threshold,
            "delta": position_size,
            "gamma": 0.0,
            "theta": 0.0,
            "vega": 0.0,
        }
        save_positions(positions)
        await update.message.reply_text(f"Option position for {symbol} added with Greeks: {greeks}")
    except Exception as e:
        logger.error(f"Exception in add_option: {e}")
        await update.message.reply_text("Usage: /add_option <symbol> <position_size> <threshold> <spot> <strike> <t> <r> <sigma> <option_type>")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Use /monitor_risk <symbol> <position_size> <threshold> to start monitoring."
    )

async def set_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        strategy = context.args[0]
        positions.setdefault(chat_id, {})
        positions[chat_id]["strategy"] = strategy
        save_positions(positions)
        await update.message.reply_text(f"Strategy set to {strategy}")
    except Exception as e:
        logger.error(f"Exception in set_strategy: {e}")
        await update.message.reply_text("Usage: /set_strategy <strategy>")

async def set_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        symbol = context.args[1].upper() if len(context.args) > 1 else None
        new_threshold = float(context.args[0])
        if chat_id not in positions or not symbol or symbol not in positions[chat_id]:
            await update.message.reply_text("No active position to adjust threshold for. Usage: /set_threshold <threshold> <symbol>")
            return
        positions[chat_id][symbol]["threshold"] = new_threshold
        save_positions(positions)
        await update.message.reply_text(f"Threshold for {symbol} updated to {new_threshold}.")
    except Exception as e:
        logger.error(f"Exception in set_threshold: {e}")
        await update.message.reply_text("Usage: /set_threshold <threshold> <symbol>")

async def auto_hedge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        strategy = context.args[0]
        threshold = float(context.args[1])
        positions.setdefault(chat_id, {})
        positions[chat_id]["auto_hedge"] = {"strategy": strategy, "threshold": threshold}
        save_positions(positions)
        await update.message.reply_text(f"Auto-hedge started with strategy {strategy} and threshold {threshold}.")
    except Exception as e:
        logger.error(f"Exception in auto_hedge: {e}")
        await update.message.reply_text("Usage: /auto_hedge <strategy> <threshold>")

async def hedge_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        asset = context.args[0].upper()
        pos = positions.get(chat_id, {})
        asset_status = pos.get(asset)
        if asset_status:
            msg = f"Status for {asset}:\n{asset_status}"
        else:
            msg = f"No active hedge for {asset}."
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Exception in hedge_status: {e}")
        await update.message.reply_text("Usage: /hedge_status <asset>")

async def hedge_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        asset = context.args[0].upper()
        timeframe = context.args[1]
        msg = f"Hedge history for {asset} over {timeframe}:\n(No real data yet)"
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Exception in hedge_history: {e}")
        await update.message.reply_text("Usage: /hedge_history <asset> <timeframe>")


async def portfolio(update, context):
    # Show portfolio analytics and all active positions for the user.
    chat_id = update.effective_chat.id
    try:
        user_positions = positions.get(chat_id, {})
        if not user_positions:
            await update.message.reply_text("You have no active positions.")
            return
        totals = aggregate_greeks(user_positions)
        msg = "Portfolio Analytics\n"
        msg += "\n".join(
            f"{k.capitalize()}: {v:.4f}" for k, v in totals.items()
        )
        msg += "\n\n*Positions:*\n"
        for symbol, pos in user_positions.items():
            msg += f"{symbol}: {pos}\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Exception in portfolio: {e}")
        await update.message.reply_text("Error fetching portfolio analytics.")

user_settings = {} 

async def set_hedge_fraction(update, context):
    # Set the fraction of delta to hedge for the user.
    chat_id = update.effective_chat.id
    try:
        fraction = float(context.args[0])
        user_settings.setdefault(chat_id, {})["hedge_fraction"] = fraction
        await update.message.reply_text(f"Hedge fraction set to {fraction}")
    except Exception as e:
        await update.message.reply_text("Usage: /set_hedge_fraction <fraction>")

async def set_rebalance_interval(update, context):
    # Set the rebalancing interval (in seconds) for the user.
    chat_id = update.effective_chat.id
    try:
        interval = int(context.args[0])
        user_settings.setdefault(chat_id, {})["rebalance_interval"] = interval
        await update.message.reply_text(f"Rebalancing interval set to {interval} seconds")
    except Exception as e:
        await update.message.reply_text("Usage: /set_rebalance_interval <seconds>")


async def hedge_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Execute a hedge immediately for the given asset and size.
    chat_id = update.effective_chat.id
    try:
        asset = context.args[0].upper()
        size = float(context.args[1])
        steps = int(context.args[2]) if len(context.args) > 2 else 1
        result = place_bybit_order(asset, "Sell", size)
        orderbook = get_bybit_orderbook(asset)
        slippage = estimate_slippage(orderbook, size)
        cost = size * slippage  
        for i in range(steps):
            partial_size = size / steps
            place_bybit_order(asset, "Sell", partial_size)
        msg = (
            f" Hedge Executed!\n"
            f"Asset: {asset}\n"
            f"Size: {size}\n"
            f"Estimated Slippage: {slippage}\n"
            f"Estimated Cost: {cost}\n"
            f"New delta: ...\n" 
        )
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Exception in hedge_now: {e}")
        await update.message.reply_text("Usage: /hedge_now <asset> <size>")

async def start_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Start monitoring a position for risk and trigger alerts/hedges as needed.
    chat_id = update.effective_chat.id
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("Usage: /monitor_risk <symbol> <position_size> <threshold>")
        return
    symbol, pos_size_str, threshold_str = args
    try:
        position_size = float(pos_size_str)
        threshold = float(threshold_str)
    except ValueError:
        await update.message.reply_text("Position size and threshold must be numbers.")
        return
    positions[chat_id] = positions.get(chat_id, {})
    positions[chat_id][symbol.upper()] = {
        "position_size": position_size,
        "threshold": threshold,
        "delta": position_size,    
        "gamma": 0.0,
        "theta": 0.0,
        "vega": 0.0,
    }
    save_positions(positions)
    if chat_id in monitoring_tasks:
        monitoring_tasks[chat_id].cancel()
    app = context.application
    task = app.create_task(monitor_position(chat_id, symbol.upper(), position_size, threshold, app))
    monitoring_tasks[chat_id] = task
    await update.message.reply_text(
        f"Monitoring started for {symbol.upper()} with position size {position_size} and threshold {threshold}."
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle inline button presses for hedging, adjusting threshold, or stopping monitoring.
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data
    if data.startswith("hedge_now"):
        _, symbol, size = data.split("|")
        result = place_bybit_order(symbol, "Sell", float(size))
        await query.edit_message_text(text=f"Hedge executed: {result}")
    elif data == "adjust_threshold":
        await query.edit_message_text(text="Send new threshold as: /set_threshold <threshold> <symbol>")
    elif data == "stop_monitoring":
        if chat_id in monitoring_tasks:
            monitoring_tasks[chat_id].cancel()
            del monitoring_tasks[chat_id]
            await query.edit_message_text(text="Monitoring stopped.")
        else:
            await query.edit_message_text(text="No active monitoring to stop.")

def get_bybit_price(symbol="BTCUSDT"):
    # Fetch the best ask price for a symbol from Bybit orderbook.
    url = f"https://api.bybit.com/v5/market/orderbook?category=linear&symbol={symbol}&limit=5"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    asks = data['result']['a']
    best_ask = float(asks[0][0])
    return best_ask

def main():
    # Set up the Telegram bot and register all command handlers.
    TOKEN = os.getenv("TELEGRAM_TOKEN") 
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("set_strategy", set_strategy))
    app.add_handler(CommandHandler("set_threshold", set_threshold))
    app.add_handler(CommandHandler("auto_hedge", auto_hedge))
    app.add_handler(CommandHandler("hedge_status", hedge_status))
    app.add_handler(CommandHandler("hedge_history", hedge_history))
    app.add_handler(CommandHandler("correlation_chart", correlation_chart))
    app.add_handler(CommandHandler("hedge_now", hedge_now))
    app.add_handler(CommandHandler("simulate_strategy", simulate_strategy))
    app.add_handler(CommandHandler("set_hedge_fraction", set_hedge_fraction))
    app.add_handler(CommandHandler("set_rebalance_interval", set_rebalance_interval))
    app.add_handler(CommandHandler("portfolio", portfolio))
    app.add_handler(CommandHandler("risk_chart",risk_chart))
    app.add_handler(CommandHandler("monitor_risk", start_monitor))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
