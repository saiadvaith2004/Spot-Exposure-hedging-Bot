from utils.logger import logger
def compute_hedge_size(total_delta, hedge_fraction=0.5):
    return -total_delta * hedge_fraction  