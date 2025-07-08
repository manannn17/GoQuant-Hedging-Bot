import requests

def get_okx_orderbook(symbol="BTC-USDT-SWAP", depth=5):
    url = f"https://www.okx.com/api/v5/market/books?instId={symbol}&sz={depth}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["data"][0]
    else:
        return None

def get_okx_ticker(symbol="BTC-USDT-SWAP"):
    url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["data"][0]
    else:
        return None
