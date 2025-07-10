"""import requests

def get_bybit_ticker(symbol="BTCUSDT"):
    url = "https://api.bybit.com/v5/market/tickers"
    try:
        response = requests.get(url, params={"symbol": symbol}, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data["result"][0] if data.get("result") else None
    except Exception as e:
        print(f"[BYBIT ERROR] {e}")
        return None 
"""
"""
# src/exchanges/bybit.py

import requests

def get_bybit_ticker(symbol="BTCUSDT"):
    url = "https://api.bybit.com/v2/public/tickers"
    params = {"symbol": symbol}
    response = requests.get(url, params=params)
    data = response.json()
    return data["result"][0] if data.get("result") else None
"""
import requests

def get_bybit_ticker():
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"category": "spot", "symbol": "BTCUSDT"}
        response = requests.get(url, params=params, timeout=10)

        # Validate HTTP response
        if response.status_code != 200:
            print(f"[BYBIT ERROR] Status Code: {response.status_code}")
            print(f"Response Text: {response.text}")
            return None

        # Try decoding JSON
        try:
            data = response.json()
            return data
        except requests.exceptions.JSONDecodeError as e:
            print(f"[BYBIT JSON ERROR] {e}")
            print(f"Raw response: {response.text}")
            return None

    except Exception as e:
        print(f"[BYBIT ERROR] {e}")
        return None
