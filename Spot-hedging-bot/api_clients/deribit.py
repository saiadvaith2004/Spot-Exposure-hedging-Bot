import requests

def get_deribit_options(symbol="BTC-PERPETUAL"):
    url = f"https://www.deribit.com/api/v2/public/get_instruments?currency={symbol.split('-')[0]}&kind=option"
    resp = requests.get(url)
    return resp.json()
