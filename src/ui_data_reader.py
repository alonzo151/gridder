import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.database import SimulativeDatabase
from src.logger import setup_logger
from src.helpers.calculators import Calculator
logger = setup_logger()

class UIDataReader:
    def __init__(self, data_dir: str = "data"):
        self.db = SimulativeDatabase(data_dir)
        self.calc = Calculator()
    
    def _apply_time_filter(self, df: pd.DataFrame, hours_filter: Optional[int] = None) -> pd.DataFrame:
        """Apply time filtering to dataframe if hours_filter is specified"""
        if hours_filter is None or df.empty:
            return df
        
        cutoff_time = pd.Timestamp.utcnow() - timedelta(hours=hours_filter)
        return df[df['timestamp'] >= cutoff_time]
    
    def get_trades_data(self, bot_name: Optional[str] = None, hours_filter: Optional[int] = None) -> pd.DataFrame:
        """Get trades data formatted for chart visualization"""
        
        records = self.db.read_table('trades', bot_name)
        
        if not records:
            return pd.DataFrame(columns=['timestamp', 'price', 'side', 'quantity', 'bot_name', 'bot_run'])
        
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price'] = pd.to_numeric(df['price'])
        df['quantity'] = pd.to_numeric(df['quantity'])
        
        return self._apply_time_filter(df, hours_filter)
    
    def get_options_pnl_data(self, bot_name: Optional[str] = None, hours_filter: Optional[int] = None) -> pd.DataFrame:
        
        records = self.db.read_table('stats', bot_name)
        if hours_filter:
            records = [i for i in records if
                      pd.to_datetime(i['timestamp']) >= pd.Timestamp.utcnow() - pd.Timedelta(hours=hours_filter)]

        
        if not records:
            return pd.DataFrame(columns=['timestamp', 'call_unrealized_pnl', 'put_unrealized_pnl', 'bot_name', 'bot_run'])
        
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['call_unrealized_pnl'] = pd.to_numeric(df['call_unrealized_pnl'])
        df['put_unrealized_pnl'] = pd.to_numeric(df['put_unrealized_pnl'])
        
        return df
    
    def get_total_unrealized_pnl_data(self, bot_name: Optional[str] = None, hours_filter: Optional[int] = None) -> pd.DataFrame:
        """Get total unrealized PnL data (spot + options) for chart visualization"""

        records = self.db.read_table('stats', bot_name)
        if hours_filter:
            records = [i for i in records if
                      pd.to_datetime(i['timestamp']) >= pd.Timestamp.utcnow() - pd.Timedelta(hours=hours_filter)]

        if not records:
            return pd.DataFrame(
                columns=['timestamp', 'call_unrealized_pnl', 'put_unrealized_pnl', 'bot_name', 'bot_run'])

        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['total_unrealized_pnl'] = pd.to_numeric(df['call_unrealized_pnl']) + pd.to_numeric(df['put_unrealized_pnl']) + pd.to_numeric(df['put_unrealized_pnl'])

        return df
    
    def get_price_data(self, bot_name: Optional[str] = None, hours_filter: Optional[int] = None) -> pd.DataFrame:
        """Get BTCFDUSD price data over time for chart visualization"""

        
        records = self.db.read_table('trades', bot_name)
        
        if not records:
            return pd.DataFrame(columns=['timestamp', 'price', 'bot_name', 'bot_run'])
        
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price'] = pd.to_numeric(df['price'])
        
        price_df = df.groupby(['timestamp', 'bot_name'])['price'].mean().reset_index()
        result_df = price_df.sort_values('timestamp')
        
        return self._apply_time_filter(result_df, hours_filter)

    def normalize_first_values(self, records, keys):
        """
        For each bot_name + bot_run, set the first value of each key to zero and
        subtract its value from all subsequent values for that run.
        """
        import pandas as pd

        if not records:
            return records

        df = pd.DataFrame(records)
        if not all(k in df for k in ['bot_name', 'bot_run', *keys]):
            return records

        def adjust_group(group):
            for key in keys:
                first_value = group.iloc[0][key]
                group[key] = group[key] - first_value
                group.iloc[0, group.columns.get_loc(key)] = 0
            return group

        df = df.groupby(['bot_name', 'bot_run'], group_keys=False).apply(adjust_group)
        return df.to_dict(orient='records')

    def get_summary_stats(self, bot_name: Optional[str] = None, hours_filter: Optional[int] = None) -> Dict[str, Any]:
        """Get summary statistics for the dashboard"""
        
        stats = self.db.read_table('stats', bot_name)
        trades = self.db.read_table('trades', bot_name)
        if hours_filter:
            trades = [i for i in trades if pd.to_datetime(i['timestamp']) >= pd.Timestamp.utcnow() - pd.Timedelta(hours=hours_filter)]
        
        if not stats or not trades:
            return {
                'total_trades': 0, # run
                'buy_trades': 0, # run
                'sell_trades': 0, # run
                'realized_pnl': 0.0, # run
                'spot_realized_pnl': 0.0, # run
                'spot_unrealized_pnl': 0.0, # run
                'options_unrealized_pnl': 0.0, # all runs
                'total_unrealized_pnl': 0.0 # all runs
            }

        spot_realized_pnl = self.calc.calculate_spot_realized_pnl(trades)
        spot_unrealized_pnl = stats[-1].get('spot_unrealized_pnl', 0.0)
        options_unrealized_pnl = stats[-1].get('call_unrealized_pnl', 0.0)
        return {
            'total_trades': len(trades),
            'buy_trades': len([i for i in trades if i.get('side') == 'BUY']),
            'sell_trades': len([i for i in trades if i.get('side') == 'SELL']),
            'spot_realized_pnl': spot_realized_pnl,
            'spot_unrealized_pnl': spot_unrealized_pnl,
            'options_unrealized_pnl': options_unrealized_pnl,
            'total_unrealized_pnl': spot_unrealized_pnl + options_unrealized_pnl
        }
    
    def get_available_bot_names(self) -> List[str]:
        """Get list of available bot names"""
        return self.db.get_available_bot_names()

    def get_bot_runs(self, bot_name: str) -> List[Dict[str, Any]]:
        """Get list of runs for a specific bot"""
        return self.db.get_bot_runs(bot_name)

    def get_latest_bot_run(self) -> Dict[str, str]:
        """Get the latest bot name and bot run"""
        return self.db.get_latest_bot_run()

    def get_bot_last_config(self, bot_name: str) -> Dict[str, Any]:
        """Get configuration for a specific bot run"""
        runs = self.db.read_table('runs', bot_name)
        return runs[-1]['config'] if runs else {}
