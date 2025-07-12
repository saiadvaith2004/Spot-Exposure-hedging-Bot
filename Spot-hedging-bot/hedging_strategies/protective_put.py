from utils.logger import logger
def protective_put(spot_position, option_price, strike, expiry):
    cost = option_price
    return {"cost": cost, "strike": strike, "expiry": expiry}
