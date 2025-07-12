#This bot allows users to connect their Binance testnet accounts, check balances, and perform automated hedging.
import asyncio
import ccxt
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Configuration ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') 
user_data = {}

# --- Exchange Connection Functions ---
def get_binance_exchange(api_key, secret, futures=False):
   # Initialize and return a Binance exchange instance (spot or futures).
    try:
        if futures:
            # Set up futures exchange with testnet configuration
            exchange = ccxt.binanceusdm({
                'apiKey': api_key,
                'secret': secret,
                'enableRateLimit': True,
                'testnet': True,
                'options': {
                    'defaultType': 'future',
                    'test': True,
                },
                'urls': {
                    'api': {
                        'fapi': 'https://testnet.binancefuture.com/fapi/v2',
                    }
                }
            })
            logger.info(f"Initialized Binance USDM Futures testnet exchange for API key {api_key[:10]}...")
            return exchange
        else:
            # Set up spot exchange with testnet configuration
            exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': secret,
                'enableRateLimit': True,
                'testnet': True,
                'urls': {
                    'api': {
                        'public': 'https://testnet.binance.vision/api/v3',
                        'private': 'https://testnet.binance.vision/api/v3'
                    }
                }
            })
            logger.info(f"Initialized Binance Spot testnet exchange for API key {api_key[:10]}...")
            return exchange
    except ccxt.AuthenticationError as e:
        logger.error(f"Authentication error initializing exchange for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Invalid API key or permissions: {e}. Generate a new key at https://testnet.binance.vision/")
    except ccxt.NetworkError as e:
        logger.error(f"Network error initializing exchange for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Network error: {e}. Check your internet connection or Binance testnet status.")
    except Exception as e:
        logger.error(f"Unexpected error initializing exchange for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Error initializing exchange: {e}")
def get_btc_spot_balance(api_key, secret):
    #Fetch BTC balance from Binance spot account.
    exchange = get_binance_exchange(api_key, secret, futures=False)
    try:
        balance = exchange.fetch_balance()
        if 'total' not in balance:
            logger.error(f"Invalid balance response for API key {api_key[:10]}...: {balance}")
            raise ValueError("Invalid balance response from Binance")
        btc_balance = balance['total'].get('BTC', 0.0)
        logger.info(f"Fetched spot balance for API key {api_key[:10]}...: {btc_balance} BTC")
        return float(btc_balance)
    except ccxt.AuthenticationError as e:
        logger.error(f"Authentication error fetching spot balance for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Invalid API key or permissions: {e}. Please generate a new key at https://testnet.binance.vision/")
    except ccxt.NetworkError as e:
        logger.error(f"Network error fetching spot balance for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Network error: {e}. Check your internet connection or Binance testnet status.")
    except Exception as e:
        logger.error(f"Unexpected error fetching spot balance for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Error fetching spot balance: {e}")

def get_btc_futures_position(api_key, secret):
    # Fetch BTC futures position from Binance futures account.
    exchange = get_binance_exchange(api_key, secret, futures=True)
    try:
        positions = exchange.fapiPrivateV2GetPositionRisk({'symbol': 'BTCUSDT'})
        if not isinstance(positions, list):
            logger.error(f"Invalid positions response for API key {api_key[:10]}...: {positions}")
            raise ValueError("Invalid positions response from Binance")
        for pos in positions:
            if not isinstance(pos, dict) or 'symbol' not in pos or 'positionAmt' not in pos:
                logger.warning(f"Invalid position data: {pos}")
                continue
            if pos['symbol'] == 'BTCUSDT':
                position_amt = float(pos['positionAmt'])
                logger.info(f"Fetched futures position for API key {api_key[:10]}...: {position_amt} BTCUSDT")
                return position_amt
        logger.info(f"No BTCUSDT futures position found for API key {api_key[:10]}...")
        return 0.0
    except ccxt.AuthenticationError as e:
        logger.error(f"Authentication error fetching futures position for API key {api_key[:10]}...: {e}")
        raise ValueError(
            f"Invalid API key or permissions: {e}. "
            "Please generate a new key at https://testnet.binance.vision/ with futures permissions."
        )
    except ccxt.NetworkError as e:
        logger.error(f"Network error fetching futures position for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Network error: {e}. Check your internet connection or Binance testnet status.")
    except Exception as e:
        logger.error(f"Unexpected error fetching futures position for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Error fetching futures position: {e}")

def hedge_btc_position(api_key, secret, spot_qty, hedge_ratio=1.0):
    # Place a hedge order to offset spot BTC position with futures.
    exchange = get_binance_exchange(api_key, secret, futures=True)
    try:
        hedge_qty = spot_qty * hedge_ratio
        if hedge_qty == 0:
            logger.info(f"No position to hedge for API key {api_key[:10]}...")
            return {"status": "no_hedge_needed", "message": "No position to hedge"}
        # Place market sell order to hedge long spot position
        order = exchange.create_market_sell_order('BTCUSDT', abs(hedge_qty))
        logger.info(f"Hedge order placed for API key {api_key[:10]}...: {order}")
        return order
    except ccxt.AuthenticationError as e:
        logger.error(f"Authentication error placing hedge for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Invalid API key or permissions: {e}")
    except ccxt.NetworkError as e:
        logger.error(f"Network error placing hedge for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Network error: {e}")
    except Exception as e:
        logger.error(f"Error placing hedge for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Error placing hedge: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message and instructions."""
    await update.message.reply_text(
        "Welcome to the Risk Management Bot!\n"
        "Use /connect <api_key> <secret> to connect your Binance testnet account.\n"
        "Then use /balance to check your BTC position or /hedge to hedge it."
    )

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Connect user's Binance testnet account.
    if len(context.args) != 2:
        await update.message.reply_text("Please provide API key and secret: /connect <api_key> <secret>")
        return
    api_key, secret = context.args[0].strip(), context.args[1].strip()
    user_id = update.effective_user.id
    logger.info(f"User {user_id} attempting to connect with API key {api_key[:10]}...")
    user_data[user_id] = {'api_key': api_key, 'secret': secret}
    spot_valid = False
    futures_valid = False
    error_message = ""
    try:
        exchange = get_binance_exchange(api_key, secret, futures=False)
        exchange.fetch_ticker('BTC/USDT')  # Test connectivity
        spot_valid = True
        logger.info(f"Spot connectivity validated for user {user_id}")
    except Exception as e:
        error_message += f"Spot connectivity test failed: {str(e)}\n"
        logger.warning(f"Spot connectivity test failed for API key {api_key[:10]}...: {e}")
    try:
        exchange = get_binance_exchange(api_key, secret, futures=True)
        exchange.fapiPrivateGetAccount()  
        futures_valid = True
        logger.info(f"Futures connectivity validated for user {user_id}")
    except Exception as e:
        error_message += f"Futures connectivity test failed: {str(e)}\n"
        logger.warning(f"Futures connectivity test failed for API key {api_key[:10]}...: {e}")
    success_message = "Connected successfully! Use /balance to check your position."
    if error_message:
        success_message += f"\nWarning: Some connectivity issues detected:\n{error_message}"
        success_message += "You may face issues with /balance or /hedge. Ensure your API key has reading and futures permissions at https://testnet.binance.vision/."
    await update.message.reply_text(success_message)
    logger.info(f"User {user_id} connected with API key {api_key[:10]}... Spot valid: {spot_valid}, Futures valid: {futures_valid}")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check user's BTC spot balance and futures position.
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested balance")
    creds = user_data.get(user_id)
    if not creds:
        logger.warning(f"No credentials found for user {user_id}")
        await update.message.reply_text("Connect your account first with /connect.")
        return
    spot_btc = 0.0
    futures_btc = 0.0
    error_message = ""
    # Fetch spot balance
    try:
        logger.info(f"Fetching spot balance for API key {creds['api_key'][:10]}...")
        spot_btc = get_btc_spot_balance(creds['api_key'], creds['secret'])
    except ValueError as e:
        logger.error(f"ValueError fetching spot balance for API key {creds['api_key'][:10]}...: {e}")
        error_message += f"Spot balance error: {str(e)}\n"
    except ccxt.AuthenticationError as e:
        logger.error(f"AuthenticationError fetching spot balance for API key {creds['api_key'][:10]}...: {e}")
        error_message += f"Spot authentication error: {str(e)}. Ensure API key has reading permissions.\n"
    except ccxt.NetworkError as e:
        logger.error(f"NetworkError fetching spot balance for API key {creds['api_key'][:10]}...: {e}")
        error_message += f"Spot network error: {str(e)}. Check your internet connection.\n"
    except Exception as e:
        logger.error(f"Unexpected error fetching spot balance for API key {creds['api_key'][:10]}...: {e}")
        error_message += f"Unexpected spot error: {str(e)}\n"
    # Fetch futures position
    try:
        logger.info(f"Fetching futures position for API key {creds['api_key'][:10]}...")
        futures_btc = get_btc_futures_position(creds['api_key'], creds['secret'])
    except ValueError as e:
        logger.error(f"ValueError fetching futures position for API key {creds['api_key'][:10]}...: {e}")
        error_message += f"Futures position error: {str(e)}\n"
    except ccxt.AuthenticationError as e:
        logger.error(f"AuthenticationError fetching futures position for API key {creds['api_key'][:10]}...: {e}")
        error_message += f"Futures authentication error: {str(e)}. Ensure API key has futures permissions.\n"
    except ccxt.NetworkError as e:
        logger.error(f"NetworkError fetching futures position for API key {creds['api_key'][:10]}...: {e}")
        error_message += f"Futures network error: {str(e)}. Check your internet connection.\n"
    except Exception as e:
        logger.error(f"Unexpected error fetching futures position for API key {creds['api_key'][:10]}...: {e}")
        error_message += f"Unexpected futures error: {str(e)}\n"
    # Calculate net delta and prepare response
    delta = spot_btc + futures_btc
    response = ""
    if spot_btc is not None:
        response += f"BTC Spot Balance: {spot_btc:.6f}\n"
    if futures_btc is not None:
        response += f"BTC Futures Position: {futures_btc:.6f}\n"
    if spot_btc is not None and futures_btc is not None:
        response += f"Net Delta: {delta:.6f}\n"
        response += "Use /hedge to set up an automated hedge."    
    if error_message:
        response += f"\nErrors encountered:\n{error_message}"
        response += "Please generate a new key at https://testnet.binance.vision/ with reading and futures permissions and use /connect <api_key> <secret>." 
    await update.message.reply_text(response)
    logger.info(f"Balance response sent to user {user_id}: Spot={spot_btc}, Futures={futures_btc}, Delta={delta}")

async def hedge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Show hedge ratio selection buttons.
    keyboard = [
        [InlineKeyboardButton("Hedge 100%", callback_data='hedge_1.0')],
        [InlineKeyboardButton("Hedge 80%", callback_data='hedge_0.8')],
        [InlineKeyboardButton("Hedge 50%", callback_data='hedge_0.5')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Select hedge ratio:', reply_markup=reply_markup)

async def hedge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Handle hedge ratio selection and execute hedge order.
    query = update.callback_query
    await query.answer()
    hedge_ratio = float(query.data.split('_')[1])
    creds = user_data.get(query.from_user.id)
    if not creds:
        await query.edit_message_text("Connect your account first with /connect.")
        return
    try:
        spot_btc = get_btc_spot_balance(creds['api_key'], creds['secret'])
        if spot_btc == 0:
            await query.edit_message_text("No BTC in your spot account to hedge.")
            return
        order = hedge_btc_position(creds['api_key'], creds['secret'], spot_btc, hedge_ratio)
        await query.edit_message_text(
            f"Hedged {hedge_ratio*100:.0f}% of your BTC spot position with a short futures order.\n"
            f"Order info: {order}"
        )
    except ValueError as e:
        logger.error(f"ValueError in hedge_callback for API key {creds['api_key'][:10]}...: {e}")
        await query.edit_message_text(f"Error placing hedge: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in hedge_callback for API key {creds['api_key'][:10]}...: {e}")
        await query.edit_message_text(f"Unexpected error placing hedge: {str(e)}")

async def monitor_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Monitor risk levels and alert when delta exceeds threshold.
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /monitor_risk <symbol> <position_size> <threshold>")
        return
    symbol, position_size, threshold = context.args[0], float(context.args[1]), float(context.args[2])
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Starting risk monitoring for {symbol} with position size {position_size} and threshold {threshold}.")
    while True:
        try:
            creds = user_data.get(chat_id)
            if not creds:
                await update.message.reply_text("Connect your account first with /connect.")
                return
            spot_btc = get_btc_spot_balance(creds['api_key'], creds['secret'])
            futures_btc = get_btc_futures_position(creds['api_key'], creds['secret'])
            delta = spot_btc + futures_btc
            if abs(delta) > threshold:
                await update.message.reply_text(
                    f"Risk Alert! Delta ({delta:.6f}) exceeds threshold ({threshold}) for {symbol}."
                )
            await asyncio.sleep(30)  # Check every 30 seconds
        except ValueError as e:
            logger.error(f"ValueError in monitor_risk for API key {creds.get('api_key', 'unknown')[:10]}...: {e}")
            await update.message.reply_text(f"Error in risk monitoring: {str(e)}")
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Unexpected error in monitor_risk for API key {creds.get('api_key', 'unknown')[:10]}...: {e}")
            await asyncio.sleep(30)

def main():
    #Initialize and start the Telegram bot.
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        logger.info("Bot initialized successfully")
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('connect', connect))
        application.add_handler(CommandHandler('balance', balance))
        application.add_handler(CommandHandler('monitor_risk', monitor_risk))
        application.add_handler(CommandHandler('hedge', hedge))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, connect))
        application.add_handler(CallbackQueryHandler(hedge_callback, pattern='^hedge_'))
        application.run_polling()
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        raise e

if __name__ == '__main__':
    main()