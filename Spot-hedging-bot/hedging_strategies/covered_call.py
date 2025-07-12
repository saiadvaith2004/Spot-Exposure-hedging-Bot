def covered_call(spot_position, call_option):
    return {"cost": call_option["price"], "strike": call_option["strike"], "expiry": call_option["expiry"]}
