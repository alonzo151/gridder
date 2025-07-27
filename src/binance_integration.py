import requests
import time
import hmac
import hashlib
from typing import Dict, Any, List, Optional
from src.logger import setup_logger

logger = setup_logger()

class BinanceIntegration:
    def __init__(self, api_key: str = "", api_secret: str = "", test_mode: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.test_mode = test_mode
        self.base_url = "https://api.binance.com"
        self.session = requests.Session()
        
        if not test_mode and (not api_key or not api_secret):
            raise ValueError("API key and secret required for live mode")
        
        logger.info(f"Initialized Binance integration in {'test' if test_mode else 'live'} mode")

    def _generate_signature(self, query_string: str) -> str:
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _make_request(self, method: str, endpoint: str, params: Dict[str, Any] = None, signed: bool = False) -> Dict[str, Any]:
        if self.test_mode and signed and endpoint in ["/api/v3/order", "/api/v3/openOrders"]:
            logger.debug(f"Test mode: simulating {method} request to {endpoint}")
            return self._simulate_response(endpoint, params)
        
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        if params is None:
            params = {}
        
        if signed:
            if not self.api_key or not self.api_secret:
                if self.test_mode and endpoint in ["/api/v3/order", "/api/v3/openOrders"]:
                    return self._simulate_response(endpoint, params)
                else:
                    raise ValueError("API credentials required for live mode")
            
            params['timestamp'] = int(time.time() * 1000)
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            params['signature'] = self._generate_signature(query_string)
            headers['X-MBX-APIKEY'] = self.api_key
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, params=params, headers=headers)
            elif method == 'DELETE':
                response = self.session.delete(url, params=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance API request failed: {e}")
            raise

    def _simulate_response(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        if endpoint == "/api/v3/order":
            return {
                "symbol": params.get("symbol"),
                "orderId": 12345,
                "clientOrderId": "test_order",
                "status": "NEW"
            }
        elif endpoint == "/api/v3/account":
            return {
                "balances": [
                    {"asset": "BTC", "free": "1.0", "locked": "0.0"},
                    {"asset": "FDUSD", "free": "50000.0", "locked": "0.0"}
                ]
            }
        else:
            return {}

    def get_account_balance(self) -> Dict[str, float]:
        response = self._make_request('GET', '/api/v3/account', signed=True)
        balances = {}
        
        for balance in response.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            balances[asset] = free + locked
        
        logger.debug(f"Account balances: {balances}")
        return balances

    def get_orderbook(self, symbol: str) -> Dict[str, Any]:
        params = {"symbol": symbol}
        response = self._make_request('GET', '/api/v3/ticker/bookTicker', params)
        
        orderbook = {
            "symbol": response["symbol"],
            "bid_price": float(response["bidPrice"]),
            "bid_qty": float(response["bidQty"]),
            "ask_price": float(response["askPrice"]),
            "ask_qty": float(response["askQty"])
        }
        
        logger.debug(f"Orderbook for {symbol}: {orderbook}")
        return orderbook

    def get_price_tick(self, symbol: str) -> float:
        params = {"symbol": symbol}
        response = self._make_request('GET', '/api/v3/exchangeInfo', params)
        
        for symbol_info in response.get('symbols', []):
            if symbol_info['symbol'] == symbol:
                for filter_info in symbol_info.get('filters', []):
                    if filter_info['filterType'] == 'PRICE_FILTER':
                        tick_size = float(filter_info['tickSize'])
                        logger.debug(f"Price tick for {symbol}: {tick_size}")
                        return tick_size
        
        logger.warning(f"Price tick not found for {symbol}, using default 0.01")
        return 0.01

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, 
                   price: float = None, time_in_force: str = "GTC") -> Dict[str, Any]:
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "timeInForce": time_in_force
        }
        
        if price is not None:
            params["price"] = price
        
        if not self.test_mode:
            params["newOrderRespType"] = "FULL"
        
        response = self._make_request('POST', '/api/v3/order', params, signed=True)
        logger.info(f"Placed order: {response}")
        return response

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        
        response = self._make_request('DELETE', '/api/v3/order', params, signed=True)
        logger.info(f"Cancelled order: {response}")
        return response

    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        if self.test_mode:
            return []
        
        response = self._make_request('GET', '/api/v3/openOrders', params, signed=True)
        logger.debug(f"Open orders: {response}")
        return response
