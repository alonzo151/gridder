import pandas as pd
import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Tuple
from src.logger import setup_logger

logger = setup_logger()

class GridCalculator:
    def __init__(self, config: Dict[str, Any], price_tick: float, size_tick: float = None):
        self.config = config
        self.price_tick = price_tick
        self.size_tick = size_tick or 0.000001  # Default size tick if not provided
        self.spot_entry_price = config['spot_entry_price']
        self.spot_down_range_percent = config['spot_down_range_percent']
        self.spot_up_range_percent = config['spot_up_range_percent']
        self.spot_orders_diff_percent = config['spot_orders_diff_percent']
        self.spot_order_size_quote = config['spot_order_size_quote']
        
        logger.info(f"Initialized Grid Calculator with price_tick: {price_tick}, size_tick: {self.size_tick}")

    def round_to_tick(self, value, tick):
        """Round value to the nearest tick using Decimal precision"""
        value = Decimal(str(value))
        tick = Decimal(str(tick))
        return float((value / tick).to_integral_value(rounding=ROUND_HALF_UP) * tick)

    def calculate_grid_orders(self) -> Tuple[pd.DataFrame, float, float]:
        min_spot_price = self.spot_entry_price * (1 - self.spot_down_range_percent / 100)
        max_spot_price = self.spot_entry_price * (1 + self.spot_up_range_percent / 100)
        
        min_spot_price = self.round_to_tick(min_spot_price, self.price_tick)
        max_spot_price = self.round_to_tick(max_spot_price, self.price_tick)
        
        logger.info(f"Grid range: {min_spot_price:.8f} - {max_spot_price:.8f}")
        
        orders_data = []
        current_price = max_spot_price
        previous_price = None
        
        while current_price >= min_spot_price:
            current_price = self.round_to_tick(current_price, self.price_tick)
            
            order_size_base_raw = self.spot_order_size_quote / current_price
            order_size_base = self.round_to_tick(order_size_base_raw, self.size_tick)
            
            order_size_quote = order_size_base * current_price
            
            orders_data.append({
                'price': current_price,
                'order_size_base': order_size_base,
                'order_size_quote': order_size_quote
            })
            
            previous_price = current_price
            next_price = current_price * (1 - self.spot_orders_diff_percent / 100)
            next_price = self.round_to_tick(next_price, self.price_tick)
            if next_price >= current_price:
                next_price = current_price - self.price_tick
            current_price = next_price
        
        orders_df = pd.DataFrame(orders_data)
        orders_df = orders_df.sort_values('price').reset_index(drop=True)
        orders_df = self._calculate_balances(orders_df)
        
        entry_index = self._find_entry_index(orders_df)
        base_needed, quote_needed = self._calculate_initial_funds(orders_df, entry_index)
        
        logger.info(f"Generated {len(orders_df)} grid orders")
        logger.info(f"Initial funds needed - Base: {base_needed:.6f}, Quote: {quote_needed:.2f}")
        
        return orders_df, base_needed, quote_needed

    def _calculate_balances(self, orders_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate balances ensuring no negative balances are allowed"""
        orders_df = orders_df.sort_values('price').reset_index(drop=True)
        
        orders_df['base_balance'] = 0.0
        orders_df['quote_balance'] = 0.0
        
        
        cumulative_base = 0.0
        for i in range(len(orders_df) - 1, -1, -1):  # Start from highest price
            orders_df.iloc[i, orders_df.columns.get_loc('base_balance')] = cumulative_base
            cumulative_base += orders_df.iloc[i]['order_size_base']
        
        cumulative_quote = 0.0
        for i in range(len(orders_df)):  # Start from lowest price
            orders_df.iloc[i, orders_df.columns.get_loc('quote_balance')] = cumulative_quote
            cumulative_quote += orders_df.iloc[i]['order_size_quote']
        
        return orders_df

    def _find_entry_index(self, orders_df: pd.DataFrame) -> int:
        price_differences = abs(orders_df['price'] - self.spot_entry_price)
        return price_differences.idxmin()

    def _calculate_initial_funds(self, orders_df: pd.DataFrame, entry_index: int) -> Tuple[float, float]:
        """Calculate total funds needed based on max balances (no negative balances allowed)"""
        max_base_needed = orders_df['base_balance'].max()
        max_quote_needed = orders_df['quote_balance'].max()
        
        base_needed = max_base_needed
        quote_needed = max_quote_needed
        
        return base_needed, quote_needed

    def get_orders_for_price_range(self, orders_df: pd.DataFrame, current_price: float, 
                                 max_orders: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
        buy_orders = orders_df[orders_df['price'] < current_price].tail(max_orders)
        sell_orders = orders_df[orders_df['price'] > current_price].head(max_orders)
        
        return buy_orders, sell_orders
