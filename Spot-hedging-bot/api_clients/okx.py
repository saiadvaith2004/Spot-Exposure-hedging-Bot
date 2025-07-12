import requests

def get_okx_orderbook(symbol="BTC-USDT-SWAP"):
    url = f"https://www.okx.com/api/v5/market/books?instId={symbol}&sz=5"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()
