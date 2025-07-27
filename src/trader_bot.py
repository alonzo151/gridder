import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from src.logger import setup_logger
from src.binance_integration import BinanceIntegration
from src.deribit_integration import DeribitIntegration
from src.grid_calculator import GridCalculator
from src.database import SimulativeDatabase

logger = setup_logger()

class TraderBot:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bot_name = self._generate_bot_name()
        self.test_mode = config['trading_mode'] == 'test'
        self.running = False
        self.start_time = datetime.utcnow()
        
        self.binance = BinanceIntegration(
            api_key=config.get('binance_api_key', ''),
            api_secret=config.get('binance_api_secret', ''),
            test_mode=self.test_mode
        )
        
        self.deribit = DeribitIntegration(
            api_key=config.get('deribit_api_key', ''),
            api_secret=config.get('deribit_api_secret', ''),
            test_mode=self.test_mode
        )
        
        self.database = SimulativeDatabase()
        
        spot_price_tick = self.binance.get_price_tick(config['spot_market'])
        self.grid_calculator = GridCalculator(config, spot_price_tick)
        
        self.orders_df, self.base_needed, self.quote_needed = self.grid_calculator.calculate_grid_orders()
        
        self.simulated_balances = {
            'BTC': self.base_needed,
            'FDUSD': self.quote_needed
        }
        
        self.open_orders = []
        self.buy_trades = 0
        self.sell_trades = 0
        self.realized_pnl = 0.0
        self.last_pnl_check = datetime.utcnow()
        
        logger.info(f"Initialized TraderBot: {self.bot_name}")

    def _generate_bot_name(self) -> str:
        timestamp = int(datetime.utcnow().timestamp())
        return f"{self.config['spot_entry_price']}_{timestamp}"

    def start(self):
        if not self._verify_sufficient_funds():
            logger.error("Insufficient funds to start trading")
            return False
        
        self.running = True
        logger.info(f"Starting bot {self.bot_name}")
        
        for index, order_row in self.orders_df.iterrows():
            order_data = {
                'order_index': index,
                'base_balance': order_row['base_balance'],
                'quote_balance': order_row['quote_balance'],
                'price': order_row['price'],
                'order_size_base': order_row['order_size_base'],
                'order_size_quote': order_row['order_size_quote'],
                'base_needed_total': self.base_needed,
                'quote_needed_total': self.quote_needed
            }
            self.database.save_to_db('grid_orders', order_data, self.bot_name)
        
        try:
            while self.running:
                self._trading_loop()
                time.sleep(self.config['grid_mode_loop_sleep'])
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot stopped due to error: {e}")
        finally:
            self._shutdown()

    def _verify_sufficient_funds(self) -> bool:
        if self.test_mode:
            return True
        
        balances = self.binance.get_account_balance()
        btc_balance = balances.get('BTC', 0)
        fdusd_balance = balances.get('FDUSD', 0)
        
        if btc_balance < self.base_needed or fdusd_balance < self.quote_needed:
            logger.warning(f"Insufficient funds - Need BTC: {self.base_needed}, FDUSD: {self.quote_needed}")
            logger.warning(f"Available - BTC: {btc_balance}, FDUSD: {fdusd_balance}")
            return False
        
        return True

    def _trading_loop(self):
        try:
            current_balances = self._get_current_balances()
            current_price = self._get_current_price()
            
            self._check_boundary_crossing(current_price)
            self._manage_grid_orders(current_balances, current_price)
            
            if datetime.utcnow() - self.last_pnl_check >= timedelta(minutes=1):
                self._check_pnl()
                self.last_pnl_check = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")

    def _get_current_balances(self) -> Dict[str, float]:
        if self.test_mode:
            return self._calculate_simulated_balances()
        else:
            return self.binance.get_account_balance()
    
    def _calculate_simulated_balances(self) -> Dict[str, float]:
        """Calculate dynamic balances based on current price and grid orders that would have been executed"""
        current_price = self._get_current_market_price()
        
        btc_balance = self.base_needed
        fdusd_balance = self.quote_needed
        
        for _, order in self.orders_df.iterrows():
            order_price = order['price']
            order_size_base = order['order_size_base']
            order_size_quote = order['order_size_quote']
            
            if current_price > order_price:
                if order['base_balance'] < self.base_needed:  # This indicates it's a buy order
                    btc_balance += order_size_base
                    fdusd_balance -= order_size_quote
            else:
                if order['base_balance'] > 0:  # This indicates it's a sell order
                    btc_balance -= order_size_base
                    fdusd_balance += order_size_quote
        
        return {
            'BTC': max(0, btc_balance),  # Ensure non-negative
            'FDUSD': max(0, fdusd_balance)  # Ensure non-negative
        }

    def _get_current_price(self) -> float:
        orderbook = self.binance.get_orderbook(self.config['spot_market'])
        return (orderbook['bid_price'] + orderbook['ask_price']) / 2
    
    def _get_current_market_price(self) -> float:
        """Get current market price - separate method to avoid circular dependency in simulated balance calculation"""
        try:
            orderbook = self.binance.get_orderbook(self.config['spot_market'])
            return (orderbook['bid_price'] + orderbook['ask_price']) / 2
        except Exception as e:
            logger.warning(f"Failed to get current market price, using entry price: {e}")
            return self.config['spot_entry_price']

    def _check_boundary_crossing(self, current_price: float):
        min_price = self.orders_df['price'].min()
        max_price = self.orders_df['price'].max()
        
        if current_price < min_price:
            logger.warning(f"Price {current_price} crossed lower boundary {min_price}")
        elif current_price > max_price:
            logger.warning(f"Price {current_price} crossed upper boundary {max_price}")

    def _manage_grid_orders(self, balances: Dict[str, float], current_price: float):
        btc_balance = balances.get('BTC', 0)
        
        buy_orders, sell_orders = self.grid_calculator.get_orders_for_price_range(
            self.orders_df, current_price, self.config['grid_max_open_orders']
        )
        
        self._place_missing_orders(buy_orders, 'BUY', current_price)
        self._place_missing_orders(sell_orders, 'SELL', current_price)

    def _place_missing_orders(self, orders: pd.DataFrame, side: str, current_price: float):
        for _, order in orders.iterrows():
            order_price = order['price']
            order_size = order['order_size_base']
            
            if self._should_place_order(order_price, side, current_price):
                self._place_order(side, order_size, order_price)

    def _should_place_order(self, order_price: float, side: str, current_price: float) -> bool:
        if side == 'BUY' and order_price >= current_price:
            return False
        if side == 'SELL' and order_price <= current_price:
            return False
        
        for existing_order in self.open_orders:
            if abs(existing_order['price'] - order_price) < self.binance.get_price_tick(self.config['spot_market']):
                return False
        
        return True

    def _place_order(self, side: str, quantity: float, price: float):
        try:
            if self.test_mode:
                order = {
                    'orderId': len(self.open_orders) + 1,
                    'symbol': self.config['spot_market'],
                    'side': side,
                    'quantity': quantity,
                    'price': price,
                    'status': 'NEW'
                }
                self.open_orders.append(order)
                if side == 'BUY':
                    self.buy_trades += 1
                else:
                    self.sell_trades += 1
                logger.info(f"Simulated order placed: {side} {quantity} at {price}")
            else:
                order = self.binance.place_order(
                    symbol=self.config['spot_market'],
                    side=side,
                    order_type='LIMIT',
                    quantity=quantity,
                    price=price,
                    time_in_force='GTC'
                )
                self.open_orders.append(order)
                if side == 'BUY':
                    self.buy_trades += 1
                else:
                    self.sell_trades += 1
                logger.info(f"Order placed: {order}")
                
        except Exception as e:
            logger.error(f"Failed to place order: {e}")

    def _check_pnl(self):
        spot_pnl = self._calculate_spot_pnl()
        options_data = self._calculate_options_pnl()
        total_pnl = spot_pnl + options_data['total_pnl']
        
        running_days = max(1, (datetime.utcnow() - self.start_time).days)
        daily_pnl = total_pnl / running_days
        
        initial_investment = self.quote_needed + self.config['call_option_initial_cost_base'] + self.config['put_option_initial_cost_base']
        daily_roi = daily_pnl / initial_investment if initial_investment > 0 else 0
        
        self.database.save_to_db('spot_stats', {
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': spot_pnl,
            'buy_trades': self.buy_trades,
            'sell_trades': self.sell_trades,
            'total_trades': self.buy_trades + self.sell_trades
        }, self.bot_name)
        
        self.database.save_to_db('options_stats', {
            'call_unrealized_pnl': options_data['call_pnl'],
            'put_unrealized_pnl': options_data['put_pnl'],
            'total_options_pnl': options_data['total_pnl']
        }, self.bot_name)
        
        logger.info(f"PnL Check - Spot: {spot_pnl:.2f}, Options: {options_data['total_pnl']:.2f}, Total: {total_pnl:.2f}")
        logger.info(f"Call PnL: {options_data['call_pnl']:.2f}, Put PnL: {options_data['put_pnl']:.2f}")
        logger.info(f"Daily ROI: {daily_roi:.4f} ({daily_roi*100:.2f}%)")
        
        if daily_roi >= self.config['daily_roi_target_for_exit']:
            logger.info("Daily ROI target reached, entering take profit mode")
            self._enter_take_profit_mode()

    def _calculate_spot_pnl(self) -> float:
        current_price = self._get_current_price()
        balances = self._get_current_balances()
        
        btc_balance = balances.get('BTC', 0)
        fdusd_balance = balances.get('FDUSD', 0)
        
        initial_value = self.base_needed * self.config['spot_entry_price'] + self.quote_needed
        current_value = btc_balance * current_price + fdusd_balance
        
        return current_value - initial_value + self.realized_pnl

    def _calculate_options_pnl(self) -> Dict[str, float]:
        try:
            call_price = self.deribit.price_for_volume(
                self.config['call_option_name'],
                self.config['call_option_size_base'],
                'sell'
            )
            
            put_price = self.deribit.price_for_volume(
                self.config['put_option_name'],
                self.config['put_option_size_base'],
                'sell'
            )
            
            call_pnl = (call_price - self.config['call_option_initial_cost_base']) * self.config['call_option_size_base']
            put_pnl = (put_price - self.config['put_option_initial_cost_base']) * self.config['put_option_size_base']
            
            return {
                'call_pnl': call_pnl,
                'put_pnl': put_pnl,
                'total_pnl': call_pnl + put_pnl
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate options PnL: {e}")
            return {
                'call_pnl': 0.0,
                'put_pnl': 0.0,
                'total_pnl': 0.0
            }

    def _enter_take_profit_mode(self):
        logger.info("Entering take profit mode")
        self.running = False
        
        try:
            self._close_all_positions()
            final_pnl = self._calculate_final_pnl()
            logger.info(f"Final PnL: {final_pnl:.2f} FDUSD")
            
        except Exception as e:
            logger.error(f"Error in take profit mode: {e}")

    def _close_all_positions(self):
        for order in self.open_orders:
            try:
                if not self.test_mode:
                    self.binance.cancel_order(order['symbol'], order['orderId'])
                logger.info(f"Cancelled order: {order['orderId']}")
            except Exception as e:
                logger.error(f"Failed to cancel order {order['orderId']}: {e}")
        
        balances = self._get_current_balances()
        btc_balance = balances.get('BTC', 0)
        
        if btc_balance > 0:
            try:
                if not self.test_mode:
                    self.binance.place_order(
                        symbol=self.config['spot_market'],
                        side='SELL',
                        order_type='MARKET',
                        quantity=btc_balance
                    )
                logger.info(f"Sold {btc_balance} BTC at market price")
            except Exception as e:
                logger.error(f"Failed to sell BTC: {e}")

    def _calculate_final_pnl(self) -> float:
        spot_pnl = self._calculate_spot_pnl()
        options_data = self._calculate_options_pnl()
        return spot_pnl + options_data['total_pnl']

    def _shutdown(self):
        logger.info(f"Shutting down bot {self.bot_name}")
        final_pnl = self._calculate_final_pnl()
        
        self.database.save_to_db('bot_shutdown', {
            'final_pnl': final_pnl,
            'buy_trades': self.buy_trades,
            'sell_trades': self.sell_trades,
            'total_trades': self.buy_trades + self.sell_trades,
            'running_time_hours': (datetime.utcnow() - self.start_time).total_seconds() / 3600
        }, self.bot_name)
