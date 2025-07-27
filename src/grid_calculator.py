import pandas as pd
import math
from typing import Dict, Any, Tuple
from src.logger import setup_logger

logger = setup_logger()

class GridCalculator:
    def __init__(self, config: Dict[str, Any], price_tick: float):
        self.config = config
        self.price_tick = price_tick
        self.spot_entry_price = config['spot_entry_price']
        self.spot_down_range_percent = config['spot_down_range_percent']
        self.spot_up_range_percent = config['spot_up_range_percent']
        self.spot_orders_diff_percent = config['spot_orders_diff_percent']
        self.spot_order_size_quote = config['spot_order_size_quote']
        
        logger.info("Initialized Grid Calculator")

    def calculate_grid_orders(self) -> Tuple[pd.DataFrame, float, float]:
        min_spot_price = self.spot_entry_price * (1 - self.spot_down_range_percent / 100)
        max_spot_price = self.spot_entry_price * (1 + self.spot_up_range_percent / 100)
        
        logger.info(f"Grid range: {min_spot_price:.2f} - {max_spot_price:.2f}")
        
        orders_data = []
        current_price = min_spot_price
        previous_price = None
        
        while current_price <= max_spot_price:
            if previous_price is not None and abs(current_price - previous_price) < self.price_tick:
                current_price = previous_price + self.price_tick
            
            order_size_base = self.spot_order_size_quote / current_price
            
            orders_data.append({
                'price': current_price,
                'order_size_base': order_size_base,
                'order_size_quote': self.spot_order_size_quote
            })
            
            previous_price = current_price
            next_price = current_price * (1 + self.spot_orders_diff_percent / 100)
            current_price = next_price
        
        orders_df = pd.DataFrame(orders_data)
        orders_df = self._calculate_balances(orders_df)
        
        entry_index = self._find_entry_index(orders_df)
        base_needed, quote_needed = self._calculate_initial_funds(orders_df, entry_index)
        
        logger.info(f"Generated {len(orders_df)} grid orders")
        logger.info(f"Initial funds needed - Base: {base_needed:.6f}, Quote: {quote_needed:.2f}")
        
        return orders_df, base_needed, quote_needed

    def _calculate_balances(self, orders_df: pd.DataFrame) -> pd.DataFrame:
        orders_df = orders_df.sort_values('price').reset_index(drop=True)
        
        entry_index = self._find_entry_index(orders_df)
        
        orders_df['base_balance'] = 0.0
        orders_df['quote_balance'] = 0.0
        
        base_balance = 0.0
        quote_balance = 0.0
        
        for i in range(entry_index, len(orders_df)):
            if i > entry_index:
                base_balance -= orders_df.iloc[i-1]['order_size_base']
                quote_balance += orders_df.iloc[i-1]['order_size_quote']
            
            orders_df.iloc[i, orders_df.columns.get_loc('base_balance')] = base_balance
            orders_df.iloc[i, orders_df.columns.get_loc('quote_balance')] = quote_balance
        
        base_balance = 0.0
        quote_balance = 0.0
        
        for i in range(entry_index, -1, -1):
            if i < entry_index:
                base_balance += orders_df.iloc[i+1]['order_size_base']
                quote_balance -= orders_df.iloc[i+1]['order_size_quote']
            
            orders_df.iloc[i, orders_df.columns.get_loc('base_balance')] = base_balance
            orders_df.iloc[i, orders_df.columns.get_loc('quote_balance')] = quote_balance
        
        return orders_df

    def _find_entry_index(self, orders_df: pd.DataFrame) -> int:
        price_differences = abs(orders_df['price'] - self.spot_entry_price)
        return price_differences.idxmin()

    def _calculate_initial_funds(self, orders_df: pd.DataFrame, entry_index: int) -> Tuple[float, float]:
        max_base_needed = orders_df['base_balance'].min()
        max_quote_needed = orders_df['quote_balance'].max()
        
        base_needed = abs(max_base_needed) if max_base_needed < 0 else 0
        quote_needed = max_quote_needed if max_quote_needed > 0 else 0
        
        return base_needed, quote_needed

    def get_orders_for_price_range(self, orders_df: pd.DataFrame, current_price: float, 
                                 max_orders: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
        buy_orders = orders_df[orders_df['price'] < current_price].tail(max_orders)
        sell_orders = orders_df[orders_df['price'] > current_price].head(max_orders)
        
        return buy_orders, sell_orders
