import json
from utils.logger import logger

def log_trade(chat_id, trade, filename="trade_logs.json"):
    try:
        try:
            with open(filename, "r") as f:
                logs = json.load(f)
        except FileNotFoundError:
            logs = {}
        logs.setdefault(str(chat_id), []).append(trade)
        with open(filename, "w") as f:
            json.dump(logs, f)
    except Exception as e:
        logger.error(f"Exception in log_trade: {e}")

def save_positions(positions, filename="positions.json"):
    try:
        with open(filename, "w") as f:
            json.dump(positions, f)
    except Exception as e:
        logger.error(f"Exception in save_positions: {e}")

def load_positions(filename="positions.json"):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

positions = load_positions()
save_positions(positions)
