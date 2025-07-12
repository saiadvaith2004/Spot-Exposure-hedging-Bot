#This bot allows users to connect their Binance testnet accounts, check balances, and perform automated hedging.
import asyncio
import ccxt
import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
load_dotenv()
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
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
print(TELEGRAM_TOKEN)
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
                'sandbox': True,  # Enable sandbox mode for testnet
                'options': {
                    'defaultType': 'future',
                    'test': True,
                    'adjustForTimeDifference': True,
                },
                'urls': {
                    'api': {
                        'public': 'https://testnet.binancefuture.com/fapi/v1',
                        'private': 'https://testnet.binancefuture.com/fapi/v1',
                        'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                        'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
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
                'sandbox': True,  # Enable sandbox mode for testnet
                'options': {
                    'adjustForTimeDifference': True,
                },
                'urls': {
                    'api': {
                        'public': 'https://testnet.binance.vision/api/v3',
                        'private': 'https://testnet.binance.vision/api/v3',
                        'v3': 'https://testnet.binance.vision/api/v3',
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
    print("Hi ",exchange)
    try:
        # Test API connectivity first
        logger.info(f"Testing API connectivity for API key {api_key[:10]}...")
        ticker = exchange.fetch_ticker('BTC/USDT')
        logger.info(f"API connectivity test successful for API key {api_key[:10]}...")
        
        # Fetch balance
        logger.info(f"Fetching balance for API key {api_key[:10]}...")
        balance = exchange.fetch_balance()
        print("Helo ",balance)
        if 'total' not in balance:
            logger.error(f"Invalid balance response for API key {api_key[:10]}...: {balance}")
            raise ValueError("Invalid balance response from Binance")
        
        btc_balance = balance['total'].get('BTC', 0.0)
        logger.info(f"Fetched spot balance for API key {api_key[:10]}...: {btc_balance} BTC")
        return float(btc_balance)
        
    except ccxt.AuthenticationError as e:
        logger.error(f"Authentication error fetching spot balance for API key {api_key[:10]}...: {e}")
        error_msg = f"Authentication failed: {e}. "
        error_msg += "Please check:\n"
        error_msg += "1. API key and secret are correct\n"
        error_msg += "2. API key has 'Read Info' permission enabled\n"
        error_msg += "3. IP address is whitelisted (or disable IP restriction)\n"
        error_msg += "4. You're using testnet keys from https://testnet.binance.vision/"
        raise ValueError(error_msg)
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
    # Place a hedge order to offset spot BTC position with a short futures position.
    exchange = get_binance_exchange(api_key, secret, futures=True)
    try:
        hedge_qty = spot_qty * hedge_ratio
        if hedge_qty == 0:
            logger.info(f"No position to hedge for API key {api_key[:10]}...")
            return {"status": "no_hedge_needed", "message": "No position to hedge"}

        # Ensure hedge mode is enabled for the account
        try:
            account_info = exchange.fapiPrivateGetAccount()
            logger.info(f"Account info retrieved for API key {api_key[:10]}...")
        except Exception as e:
            logger.warning(f"Could not verify account settings: {e}")

        # Binance USDM futures parameters for hedge mode
        params = {
            'positionSide': 'SHORT',  # Required for hedge mode
            'timeInForce': 'GTC'  # Good Till Cancelled
        }
        
        # Round to 3 decimals for BTCUSDT (Binance requirement)
        hedge_qty = round(abs(hedge_qty), 3)
        
        # Place the hedge order (short futures to offset long spot)
        order = exchange.create_market_sell_order('BTC/USDT', hedge_qty, params)
        
        logger.info(f"Hedge order placed for API key {api_key[:10]}...: {order}")
        return {
            "status": "success",
            "order": order,
            "hedge_qty": hedge_qty,
            "hedge_ratio": hedge_ratio
        }
        
    except ccxt.AuthenticationError as e:
        logger.error(f"Authentication error placing hedge for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Invalid API key or permissions: {e}")
    except ccxt.NetworkError as e:
        logger.error(f"Network error placing hedge for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Network error: {e}")
    except ccxt.InsufficientFunds as e:
        logger.error(f"Insufficient funds for hedge order: {e}")
        raise ValueError(f"Insufficient funds for hedge order: {e}")
    except ccxt.InvalidOrder as e:
        logger.error(f"Invalid order parameters: {e}")
        raise ValueError(f"Invalid order parameters: {e}")
    except Exception as e:
        logger.error(f"Error placing hedge for API key {api_key[:10]}...: {e}")
        raise ValueError(f"Error placing hedge: {e}")

def test_api_connectivity(api_key, secret):
    results = {
        'spot': {'success': False, 'error': None},
        'futures': {'success': False, 'error': None}
    }
    
    # Test spot connectivity
    try:
        spot_exchange = get_binance_exchange(api_key, secret, futures=False)
        ticker = spot_exchange.fetch_ticker('BTC/USDT')
        balance = spot_exchange.fetch_balance()
        results['spot']['success'] = True
        logger.info(f"Spot API test successful for API key {api_key[:10]}...")
    except Exception as e:
        results['spot']['error'] = str(e)
        logger.error(f"Spot API test failed for API key {api_key[:10]}...: {e}")
    
    # Test futures connectivity
    try:
        futures_exchange = get_binance_exchange(api_key, secret, futures=True)
        account_info = futures_exchange.fapiPrivateGetAccount()
        results['futures']['success'] = True
        logger.info(f"Futures API test successful for API key {api_key[:10]}...")
    except Exception as e:
        results['futures']['error'] = str(e)
        logger.error(f"Futures API test failed for API key {api_key[:10]}...: {e}")
    
    return results

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Risk Management Bot!\n\n")

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
    print("Entered")
    keyboard = [
        [InlineKeyboardButton("Hedge 100%", callback_data='hedge_1.0')],
        [InlineKeyboardButton("Hedge 80%", callback_data='hedge_0.8')],
        [InlineKeyboardButton("Hedge 50%", callback_data='hedge_0.5')],
    ]
    print("Hedge entered")
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Select hedge ratio:', reply_markup=reply_markup)

async def hedge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Handle hedge ratio selection and execute hedge order.
    print("Call Back Entered advaith")
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
        print("If completed")
        order = hedge_btc_position(creds['api_key'], creds['secret'], spot_btc, hedge_ratio)
        print("Stored in order")
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

async def test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test API key connectivity and permissions."""
    user_id = update.effective_user.id
    creds = user_data.get(user_id)
    
    if not creds:
        await update.message.reply_text("Connect your account first with /connect <api_key> <secret>")
        return
    
    await update.message.reply_text("Testing API connectivity... Please wait.")
    
    try:
        results = test_api_connectivity(creds['api_key'], creds['secret'])
        
        response = "**API Connectivity Test Results:**\n\n"
        
        if results['spot']['success']:
            response += "**Spot Trading**: Connected successfully\n"
        else:
            response += "**Spot Trading**: Failed\n"
            response += f"Error: {results['spot']['error']}\n\n"
        
        if results['futures']['success']:
            response += " **Futures Trading**: Connected successfully\n"
        else:
            response += "**Futures Trading**: Failed\n"
            response += f"Error: {results['futures']['error']}\n\n"
        
        if results['spot']['success'] and results['futures']['success']:
            response += "\n🎉 All tests passed! You can now use /hedge and /balance commands."
        else:
            response += "\n⚠️ Some tests failed. Please check your API key permissions at https://testnet.binance.vision/"
            response += "\n\nRequired permissions:"
            response += "\n- Read Info (for spot balance)"
            response += "\n- Futures Trading (for hedge orders)"
        
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Error in test_connection for user {user_id}: {e}")
        await update.message.reply_text(f"Error testing connection: {str(e)}")

def main():
    #Initialize and start the Telegram bot.
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        print(TELEGRAM_TOKEN)
        logger.info("Bot initialized successfully")
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('connect', connect))
        application.add_handler(CommandHandler('balance', balance))
        application.add_handler(CommandHandler('monitor_risk', monitor_risk))
        application.add_handler(CommandHandler('hedge', hedge))
        application.add_handler(CommandHandler('test_connection', test_connection))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, connect))
        application.add_handler(CallbackQueryHandler(hedge_callback, pattern='^hedge_'))
        application.run_polling()
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        raise e

if __name__ == '__main__':
    main()