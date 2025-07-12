from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.logger import logger

def get_hedge_buttons():
    keyboard = [
        [InlineKeyboardButton("Hedge Now", callback_data='hedge_now')],
        [InlineKeyboardButton("Adjust Threshold", callback_data='adjust_threshold')],
        [InlineKeyboardButton("View Analytics", callback_data='view_analytics')]
    ]
    return InlineKeyboardMarkup(keyboard)
