from utils.logger import logger
def execute_order_demo(symbol, side, size, price=None):
    print(f"DEMO TRADE: {side.upper()} {size} {symbol} at {price if price else 'MARKET'}")
