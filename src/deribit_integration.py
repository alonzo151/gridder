import sys
import os
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
import time
from typing import Dict, Any, List
from src.logger import setup_logger

logger = setup_logger()

class DeribitIntegration:
    def __init__(self, api_key: str = "", api_secret: str = "", test_mode: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.test_mode = test_mode
        self.base_url = "https://www.deribit.com"
        self.session = requests.Session()
        
        logger.info(f"Initialized Deribit integration in {'test' if test_mode else 'live'} mode")

    def _make_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v2/public/{method}"
        try:
            response = self.session.get(url, params=params)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as http_err:
                logger.error(f"Deribit API HTTP error: {http_err}")
                logger.error(f"Deribit API response content: {response.text}")
                if self.test_mode:
                    logger.warning(f"Deribit API failed in test mode, returning empty result: {http_err}")
                    return {}
                raise
            result = response.json()
            if result.get('error'):
                logger.error(f"Deribit API error in response: {result['error']}")
                logger.error(f"Full response: {result}")
                raise Exception(f"Deribit API error: {result['error']}")
            return result.get('result', {})
        except requests.exceptions.RequestException as e:
            logger.error(f"Deribit API request failed: {e}")
            if self.test_mode:
                logger.warning(f"Deribit API failed in test mode, returning empty result: {e}")
                return {}
            raise

    def get_option_orderbook(self, instrument_name: str) -> Dict[str, Any]:
        params = {"instrument_name": instrument_name}
        response = self._make_request("get_order_book", params)
        
        orderbook = {
            "instrument_name": instrument_name,
            "bids": response.get("bids", []),
            "asks": response.get("asks", []),
            "timestamp": response.get("timestamp", int(time.time() * 1000))
        }
        
        logger.debug(f"Option orderbook for {instrument_name}: {orderbook}")
        return orderbook

    def get_option_price(self, instrument_name: str) -> Dict[str, float]:
        params = {"instrument_name": instrument_name}
        response = self._make_request("ticker", params)
        
        price_data = {
            "bid_price": response.get("best_bid_price", 0.0),
            "ask_price": response.get("best_ask_price", 0.0),
            "mark_price": response.get("mark_price", 0.0),
            "last_price": response.get("last_price", 0.0)
        }
        
        logger.debug(f"Option price for {instrument_name}: {price_data}")
        return price_data

    def price_for_volume(self, instrument_name: str, volume: float, side: str = "sell") -> float:
        try:
            orderbook = self.get_option_orderbook(instrument_name)
            
            if side == "sell":
                orders = orderbook["bids"]
            else:
                orders = orderbook["asks"]
            
            remaining_volume = volume
            total_cost = 0.0
            
            for price, available_volume in orders:
                if remaining_volume <= 0:
                    break
                
                volume_to_take = min(remaining_volume, available_volume)
                total_cost += volume_to_take * price
                remaining_volume -= volume_to_take
            
            if remaining_volume > 0:
                logger.warning(f"Insufficient liquidity for volume {volume} on {side} side")
                return 0.0
            
            execution_price = total_cost / volume if volume > 0 else 0.0
            logger.debug(f"Execution price for {volume} {instrument_name} on {side} side: {execution_price}")
            return execution_price
        except Exception as e:
            if self.test_mode:
                fallback_price = 1500.0
                logger.warning(f"Failed to get option price for {instrument_name} in test mode, using fallback {fallback_price}: {e}")
                return fallback_price
            else:
                raise

    def list_instruments(self, currency: str = "BTC", kind: str = "option") -> list:
        """List available instruments for a given currency and kind (option/future/perpetual)"""
        params = {"currency": currency, "kind": kind, "expired": "false"}
        result = self._make_request("get_instruments", params)
        instruments = result if isinstance(result, list) else []
        logger.info(f"Found {len(instruments)} instruments for {currency} {kind}")
        return instruments


# python src/deribit_integration.py --list --currency BTC --kind option --test
# if __name__ == "__main__":
#     import argparse
#     parser = argparse.ArgumentParser(description="Deribit Integration Utility")
#     parser.add_argument('--list', action='store_true', help='List available BTC option instruments')
#     parser.add_argument('--currency', type=str, default='BTC', help='Currency (default: BTC)')
#     parser.add_argument('--kind', type=str, default='option', help='Instrument kind (option/future/perpetual)')
#     parser.add_argument('--test', action='store_true', help='Use testnet')
#     args = parser.parse_args()
#
#     deribit = DeribitIntegration(test_mode=args.test)
#     if args.list:
#         instruments = deribit.list_instruments(currency=args.currency, kind=args.kind)
#         for inst in instruments:
#             print(inst['instrument_name'])
#
