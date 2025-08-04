import time
from multiprocessing.dummy import current_process

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from src.logger import setup_logger
from src.binance_integration import BinanceIntegration
from src.deribit_integration import DeribitIntegration
from src.grid_calculator import GridCalculator
from src.database import SimulativeDatabase
from src.table_schema_manager import TableSchemaManager

logger = setup_logger()

class TraderBot:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bot_name = config.get('bot_name', 'DefaultBot')
        self.bot_run = self._generate_bot_run()
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
        
        self.spot_price_tick = self.binance.get_price_tick(config['spot_market'])
        self.spot_size_tick = self.binance.get_size_tick(config['spot_market'])
        self.grid_calculator = GridCalculator(config, self.spot_price_tick, self.spot_size_tick)
        
        self.orders_df, self.base_needed, self.quote_needed = self.grid_calculator.calculate_grid_orders()
        
        self.simulated_balances = {
            'BTC': self.base_needed,
            'FDUSD': self.quote_needed
        }
        
        self.open_orders = []
        self.buy_trades = 0
        self.sell_trades = 0
        self.realized_pnl = 0.0
        self.last_pnl_check = datetime.utcnow() - timedelta(minutes=1)
        self.last_price = None
        self.last_simulated_balances = None
        self.last_trade = None
        
        logger.info(f"Initialized TraderBot: {self.bot_name}")

    def _generate_bot_run(self) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return timestamp

    def start(self):
        if not self._verify_sufficient_funds():
            logger.error("Insufficient funds to start trading")
            return False
        
        self.running = True
        logger.info(f"Starting bot {self.bot_name}")
        
        self.database.save_run_config(self.bot_name, self.bot_run, self.config)
        
        for index, order_row in self.orders_df.iterrows():
            order_data = {
                'order_index': index,
                'base_balance': order_row['base_balance'],
                'quote_balance': order_row['quote_balance'],
                'price': order_row['price'],
                'order_size_base': order_row['order_size_base'],
                'order_size_quote': order_row['order_size_quote'],
                'base_needed_total': self.base_needed,
                'quote_needed_total': self.quote_needed,
                'mode': 'test' if self.test_mode else 'live'
            }
            # self.database.save_to_db('grid_orders', order_data, self.bot_name)
        
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
            bid, ask = self._get_current_bid_ask()
            current_mid_price = (bid + ask) / 2
            current_balances = self._get_current_balances(current_mid_price)
            current_open_orders = self.binance.get_open_orders(self.config['spot_market']) if not self.test_mode else self.open_orders


            self._check_boundary_crossing(current_mid_price)
            self._manage_grid_orders(current_balances, bid, ask, self.last_simulated_balances, current_open_orders)
            
            if datetime.utcnow() - self.last_pnl_check >= timedelta(minutes=1):
                self._check_pnl()
                self.last_pnl_check = datetime.utcnow()
            self.last_simulated_balances = current_balances
        except Exception as e:
            logger.error(f"Error in trading loop: {e}")

    def _get_current_balances(self, current_price) -> Dict[str, float]:
        if self.test_mode:
            return self._calculate_simulated_balances(current_price)
        else:
            return self.binance.get_account_balance()
    
    def _calculate_simulated_balances(self, current_price) -> Dict[str, float]:
        """Calculate dynamic balances based on current price and grid orders that would have been executed"""
        # get the btc balance from orders_df by using current_price
        max_price = self.orders_df['price'].max()
        min_price = self.orders_df['price'].min()
        if current_price < min_price:
            expected_quote_balance = 0
            expected_base_balance = self.base_needed
        elif current_price > max_price:
            expected_quote_balance = self.quote_needed
            expected_base_balance = 0
        else:
            filtterd_orders = self.orders_df[self.orders_df['price'] <= current_price]
            row = filtterd_orders.iloc[-1] if not filtterd_orders.empty else None
            expected_base_balance = 0
            expected_quote_balance = 0
            if row is not None:
                expected_base_balance = row['base_balance']
                expected_quote_balance = row['quote_balance']

        return {
            'BTC': max(0, expected_base_balance),  # Ensure non-negative
            'FDUSD': max(0, expected_quote_balance)  # Ensure non-negative
        }

    def _get_current_bid_ask(self) -> float:
        try:
            orderbook = self.binance.get_orderbook(self.config['spot_market'])
            return orderbook['bid_price'],  orderbook['ask_price']
        except Exception as e:
            logger.warning(f"Failed to get current price, using entry price: {e}")
            return self.config['spot_entry_price']

    def _get_current_mid_price(self) -> float:
        bid , ask = self._get_current_bid_ask()
        return (bid + ask) / 2 if bid and ask else None

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

    def _manage_grid_orders(self, balances: Dict[str, float], bid: float, ask: float,
                            last_balances: Optional[Dict[str, float]], current_open_orders: List[Dict[str, Any]]):
        btc_balance = balances.get('BTC', 0)
        mid_price = (bid + ask) / 2
        if not self.test_mode:
            # Live mode: compare desired orders to actual open orders
            current_price_based_on_balance = self.orders_df[self.orders_df['base_balance'] <= btc_balance].iloc[0][
                'price'] if not self.orders_df.empty else mid_price
            buy_orders, sell_orders = self.grid_calculator.get_orders_for_price_range(
                self.orders_df, current_price_based_on_balance, self.config['grid_max_open_orders'], self.last_trade
            )

            # Use client_order_id for open order identification
            open_order_client_ids = {o.get('client_order_id') for o in current_open_orders if o.get('client_order_id')}
            for side, orders in [('BUY', buy_orders), ('SELL', sell_orders)]:
                for _, order in orders.iterrows():
                    grid_price = order['price']
                    client_order_id = f"{self.bot_name}_{grid_price}"  # Compose client_order_id
                    if client_order_id not in open_order_client_ids:
                        price_to_send = None
                        if side == 'BUY':
                            price_to_send = min(grid_price, bid)
                        if side == 'SELL':
                            price_to_send = max(grid_price, ask)
                        if not price_to_send:
                            logger.warning(f"Skipping order placement for {side} at {grid_price} due to price mismatch")
                            continue
                        self._place_order(side, order['order_size_base'], price_to_send, client_order_id=client_order_id)
                        # Save trade to DB for live mode
                        trade_data = {
                            'timestamp': datetime.utcnow().isoformat(),
                            'side': side,
                            'price': price_to_send,
                            'quantity': order['order_size_base'],
                            'bot_name': self.bot_name,
                            'mode': 'live'
                        }
                        self.database.save_to_db('trades', trade_data, self.bot_name, self.bot_run)
                        self.last_trade = trade_data
        else:
            # Test mode: compare current to previous BTC balance
            if last_balances is not None:
                prev_btc = last_balances.get('BTC', 0)
                diff = btc_balance - prev_btc
                # If BTC increased, assume buy orders filled; if decreased, sell orders filled
                if diff != 0:
                    # Find which orders would have been filled
                    if diff > 0:
                        # find filled orders out from self.open_orders
                        filled_orders = [o for o in self.open_orders if o['side'] == 'BUY' and o['price'] > bid]
                        # sort filled orders by price descending
                        filled_orders.sort(key=lambda x: x['price'], reverse=True)
                        for order in filled_orders:
                            self.buy_trades += 1
                            trade_data = {
                                'timestamp': datetime.utcnow().isoformat(),
                                'side': 'BUY',
                                'price': order['price'],
                                'quantity': order['quantity'],
                                'bot_name': self.bot_name,
                                'mode': 'test'
                            }
                            logger.info(f"Buying trade at price {order['price']}")
                            self.database.save_to_db('trades', trade_data, self.bot_name, self.bot_run)
                            # remove the order from open_orders
                            self.open_orders = [o for o in self.open_orders if o['orderId'] != order['orderId']]
                            self.last_trade = trade_data
                    else:
                        # Sell orders filled
                        filled_orders = [o for o in self.open_orders if o['side'] == 'SELL' and o['price'] < ask]
                        # sort filled orders by price ascending
                        filled_orders.sort(key=lambda x: x['price'])
                        for order in filled_orders:
                            self.sell_trades += 1
                            logger.info(f"Selling trade at price {order['price']}")
                            trade_data = {
                                'timestamp': datetime.utcnow().isoformat(),
                                'side': 'SELL',
                                'price': order['price'],
                                'quantity': order['quantity'],
                                'bot_name': self.bot_name,
                                'mode': 'test'
                            }
                            self.database.save_to_db('trades', trade_data, self.bot_name, self.bot_run)
                            self.open_orders = [o for o in self.open_orders if o['orderId'] != order['orderId']]
                            self.last_trade = trade_data

            # Place missing orders based on simulated open orders

            buy_orders, sell_orders = self.grid_calculator.get_orders_for_price_range(
                self.orders_df, mid_price, self.config['grid_max_open_orders']
            )
            open_order_prices = {(o['price'], o['side']) for o in self.open_orders}
            for side, orders in [('BUY', buy_orders), ('SELL', sell_orders)]:
                for _, order in orders.iterrows():
                    if (order['price'], side) not in open_order_prices:
                        if self.last_trade and self.last_trade['price'] == order['price']:
                            logger.debug(f"Skipping order placement for {side} at {order['price']} due to last trade price match")
                            continue
                        self._place_order(side, order['order_size_base'], order['price'])

    def _place_missing_orders(self, orders: pd.DataFrame, side: str, current_price: float):
        if orders.empty:
            return
            
        orders_sorted = orders.copy()
        orders_sorted['distance_from_price'] = abs(orders_sorted['price'] - current_price)
        orders_sorted = orders_sorted.sort_values('distance_from_price', ascending=False)
        
        for _, order in orders_sorted.iterrows():
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
            if abs(existing_order['price'] - order_price) < self.spot_price_tick:
                return False
        
        return True

    def _place_order(self, side: str, quantity: float, price: float, client_order_id: Optional[str] = None):
        try:
            if self.test_mode:
                order = {
                    'orderId': int(time.time() * 1000),
                    'symbol': self.config['spot_market'],
                    'side': side,
                    'quantity': quantity,
                    'price': price,
                    'status': 'NEW',
                    'client_order_id': client_order_id
                }
                self.open_orders.append(order)
                logger.info(f"Simulated order placed: {side} {quantity} at {price}")
            else:
                order = self.binance.place_order(
                    symbol=self.config['spot_market'],
                    side=side,
                    order_type='LIMIT',
                    quantity=quantity,
                    price=price,
                    time_in_force='GTC',
                    post_only=True,
                    client_order_id=client_order_id
                )
                self.open_orders.append(order)
                logger.info(f"Order placed: {order}")
                
        except Exception as e:
            logger.error(f"Failed to place order: {e}")

    def _check_pnl(self):
        spot_realized_pnl = self.calculate_spot_realized_pnl(self.bot_name)
        spot_unrealized_pnl = self._calculate_spot_unrealized_pnl()
        options_data = self._calculate_options_pnl()
        total_pnl = spot_unrealized_pnl + options_data['total_pnl']
        
        running_days = max(1, (datetime.utcnow() - self.start_time).days)
        daily_pnl = total_pnl / running_days
        
        initial_investment = self.quote_needed + self.config['call_option_initial_cost_base'] + self.config['put_option_initial_cost_base']
        daily_roi = daily_pnl / initial_investment if initial_investment > 0 else 0
        
        self.database.save_to_db('spot_stats', {
            'realized_pnl': self.realized_pnl,
            'spot_unrealized_pnl': spot_unrealized_pnl,
            'spot_realized_pnl': spot_realized_pnl,
            'buy_trades': self.buy_trades,
            'sell_trades': self.sell_trades,
            'total_trades': self.buy_trades + self.sell_trades,
            'mode': 'test' if self.test_mode else 'live'
        }, self.bot_name, self.bot_run)
        
        self.database.save_to_db('options_stats', {
            'call_unrealized_pnl': options_data['call_pnl'],
            'put_unrealized_pnl': options_data['put_pnl'],
            'total_options_pnl': options_data['total_pnl'],
            'mode': 'test' if self.test_mode else 'live'
        }, self.bot_name, self.bot_run)
        
        logger.info(f"PnL Check - Spot: {spot_unrealized_pnl:.2f}, Options: {options_data['total_pnl']:.2f}, Total: {total_pnl:.2f}")
        logger.info(f"Call PnL: {options_data['call_pnl']:.2f}, Put PnL: {options_data['put_pnl']:.2f}")
        logger.info(f"Daily ROI: {daily_roi:.4f} ({daily_roi*100:.2f}%)")
        
        if daily_roi >= self.config['daily_roi_target_for_exit']:
            logger.info("Daily ROI target reached, entering take profit mode")
            self._enter_take_profit_mode()

    def _calculate_spot_unrealized_pnl(self) -> float:
        current_price = self._get_current_mid_price()
        balances = self._get_current_balances(current_price)
        btc_balance = balances.get('BTC', 0)
        fdusd_balance = balances.get('FDUSD', 0)
        initial_value = self.base_needed * self.config['spot_entry_price'] + self.quote_needed
        current_value = btc_balance * current_price + fdusd_balance
        return current_value - initial_value + self.realized_pnl

    def calculate_spot_realized_pnl(self, bot_name: str) -> float:
        """
        Calculate realized spot PnL for a given bot using FIFO matching.
        Assumes 'trades' table has 'side' ('buy'/'sell'), 'price', 'quantity'.
        """
        trades = self.database.read_table('trades', bot_name)
        if not trades:
            return 0.0

        # Sort trades by timestamp
        trades = sorted(trades, key=lambda x: x['timestamp'])
        open_positions = []  # Each entry: [quantity, price]
        realized_pnl = 0.0
        # sum all buy trades
        buy_trades_base = sum(float(trade['quantity']) for trade in trades if trade['side'].lower() == 'buy')
        buy_trades_quote = sum(float(trade['quantity']) * float(trade['price']) for trade in trades if trade['side'].lower() == 'buy')
        # sum all sell trades
        sell_trades_base = sum(float(trade['quantity']) for trade in trades if trade['side'].lower() == 'sell')
        sell_trades_quote = sum(float(trade['quantity']) * float(trade['price']) for trade in trades if trade['side'].lower() == 'sell')
        if buy_trades_base == 0 or sell_trades_base == 0:
            logger.warning("No trades found for PnL calculation")
            return 0.0
        realized_pnl = ((sell_trades_quote / sell_trades_base) - (buy_trades_quote / buy_trades_base))  * min(sell_trades_base, buy_trades_base)
        # for trade in trades:
        #     side = trade['side'].lower()
        #     qty = float(trade['quantity'])
        #     price = float(trade['price'])
        #
        #     if side == 'buy':
        #         open_positions.append([qty, price])
        #     elif side == 'sell':
        #         qty_to_close = qty
        #         while qty_to_close > 0 and open_positions:
        #             open_qty, open_price = open_positions[0]
        #             matched_qty = min(open_qty, qty_to_close)
        #             pnl = (price - open_price) * matched_qty
        #             realized_pnl += pnl
        #             open_positions[0][0] -= matched_qty
        #             qty_to_close -= matched_qty
        #             if open_positions[0][0] == 0:
        #                 open_positions.pop(0)
        #         # If selling more than held, ignore excess (or handle as needed)
        return realized_pnl

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
            # Convert BTC PnL to FDUSD using current spot price
            bid, ask = self._get_current_bid_ask()
            call_pnl_btc = (call_price - self.config['call_option_initial_cost_base'] / self.config['call_option_size_base']) * self.config['call_option_size_base']
            put_pnl_btc = (put_price - self.config['put_option_initial_cost_base'] / self.config['put_option_size_base']) * self.config['put_option_size_base']
            call_pnl = call_pnl_btc * bid
            put_pnl = put_pnl_btc * bid
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
        balances = self._get_current_balances(self._get_current_mid_price())
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
        spot_pnl = self._calculate_spot_unrealized_pnl()
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
            'running_time_hours': (datetime.utcnow() - self.start_time).total_seconds() / 3600,
            'mode': 'test' if self.test_mode else 'live'
        }, self.bot_name, self.bot_run)
