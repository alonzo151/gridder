import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.database import SimulativeDatabase
from src.logger import setup_logger

logger = setup_logger()

class UIDataReader:
    def __init__(self, data_dir: str = "data"):
        self.db = SimulativeDatabase(data_dir)
    
    def _apply_time_filter(self, df: pd.DataFrame, hours_filter: Optional[int] = None) -> pd.DataFrame:
        """Apply time filtering to dataframe if hours_filter is specified"""
        if hours_filter is None or df.empty:
            return df
        
        cutoff_time = pd.Timestamp.utcnow() - timedelta(hours=hours_filter)
        return df[df['timestamp'] >= cutoff_time]
    
    def get_trades_data(self, bot_name: Optional[str] = None, bot_run: Optional[str] = None, 
                       include_all_runs: bool = False, hours_filter: Optional[int] = None) -> pd.DataFrame:
        """Get trades data formatted for chart visualization"""
        if include_all_runs:
            bot_run = None
        
        records = self.db.read_table('trades', bot_name, bot_run)
        
        if not records:
            return pd.DataFrame(columns=['timestamp', 'price', 'side', 'quantity', 'bot_name', 'bot_run'])
        
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price'] = pd.to_numeric(df['price'])
        df['quantity'] = pd.to_numeric(df['quantity'])
        
        return self._apply_time_filter(df, hours_filter)
    
    def get_options_pnl_data(self, bot_name: Optional[str] = None, bot_run: Optional[str] = None,
                            include_all_runs: bool = False, hours_filter: Optional[int] = None) -> pd.DataFrame:
        """Get options PnL data for chart visualization"""
        if include_all_runs:
            bot_run = None
        
        records = self.db.read_table('options_stats', bot_name, bot_run)
        
        if not records:
            return pd.DataFrame(columns=['timestamp', 'call_unrealized_pnl', 'put_unrealized_pnl', 'bot_name', 'bot_run'])
        
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['call_unrealized_pnl'] = pd.to_numeric(df['call_unrealized_pnl'])
        df['put_unrealized_pnl'] = pd.to_numeric(df['put_unrealized_pnl'])
        
        return self._apply_time_filter(df, hours_filter)
    
    def get_total_unrealized_pnl_data(self, bot_name: Optional[str] = None, bot_run: Optional[str] = None,
                                     include_all_runs: bool = False, hours_filter: Optional[int] = None) -> pd.DataFrame:
        """Get total unrealized PnL data (spot + options) for chart visualization"""
        if include_all_runs:
            bot_run = None
        
        spot_records = self.db.read_table('spot_stats', bot_name, bot_run)
        options_records = self.db.read_table('options_stats', bot_name, bot_run)
        
        if not spot_records and not options_records:
            return pd.DataFrame(columns=['timestamp', 'total_unrealized_pnl', 'bot_name', 'bot_run'])
        
        spot_df = pd.DataFrame(spot_records) if spot_records else pd.DataFrame()
        options_df = pd.DataFrame(options_records) if options_records else pd.DataFrame()
        
        if not spot_df.empty and not options_df.empty:
            spot_df['timestamp'] = pd.to_datetime(spot_df['timestamp'])
            options_df['timestamp'] = pd.to_datetime(options_df['timestamp'])
            
            merged_df = pd.merge_asof(
                spot_df[['timestamp', 'spot_unrealized_pnl', 'bot_name']].sort_values('timestamp'),
                options_df[['timestamp', 'total_options_pnl', 'bot_name']].sort_values('timestamp'),
                on='timestamp', 
                by='bot_name', 
                direction='nearest',
                tolerance=pd.Timedelta(seconds=1)
            )
            
            merged_df['spot_unrealized_pnl'] = merged_df['spot_unrealized_pnl'].fillna(0)
            merged_df['total_options_pnl'] = merged_df['total_options_pnl'].fillna(0)
            merged_df['total_unrealized_pnl'] = merged_df['spot_unrealized_pnl'] + merged_df['total_options_pnl']
            
            merged_df = merged_df.set_index('timestamp')
            merged_df = merged_df.groupby('bot_name')[['spot_unrealized_pnl', 'total_options_pnl', 'total_unrealized_pnl']].resample('5min').last().reset_index()
            merged_df = merged_df.dropna(subset=['total_unrealized_pnl'])
            
            result_df = merged_df[['timestamp', 'total_unrealized_pnl', 'bot_name']].sort_values('timestamp')
            return self._apply_time_filter(result_df, hours_filter)
        elif not spot_df.empty:
            spot_df['timestamp'] = pd.to_datetime(spot_df['timestamp'])
            spot_df['total_unrealized_pnl'] = spot_df['spot_unrealized_pnl']
            spot_df = spot_df.set_index('timestamp')
            spot_df = spot_df.groupby('bot_name')[['total_unrealized_pnl']].resample('5min').last().reset_index()
            result_df = spot_df[['timestamp', 'total_unrealized_pnl', 'bot_name']].dropna()
            return self._apply_time_filter(result_df, hours_filter)
        elif not options_df.empty:
            options_df['timestamp'] = pd.to_datetime(options_df['timestamp'])
            options_df['total_unrealized_pnl'] = options_df['total_options_pnl']
            options_df = options_df.set_index('timestamp')
            options_df = options_df.groupby('bot_name')[['total_unrealized_pnl']].resample('5min').last().reset_index()
            result_df = options_df[['timestamp', 'total_unrealized_pnl', 'bot_name']].dropna()
            return self._apply_time_filter(result_df, hours_filter)
        
        return pd.DataFrame(columns=['timestamp', 'total_unrealized_pnl', 'bot_name', 'bot_run'])
    
    def get_price_data(self, bot_name: Optional[str] = None, bot_run: Optional[str] = None,
                      include_all_runs: bool = False, hours_filter: Optional[int] = None) -> pd.DataFrame:
        """Get BTCFDUSD price data over time for chart visualization"""
        if include_all_runs:
            bot_run = None
        
        records = self.db.read_table('trades', bot_name, bot_run)
        
        if not records:
            return pd.DataFrame(columns=['timestamp', 'price', 'bot_name', 'bot_run'])
        
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price'] = pd.to_numeric(df['price'])
        
        price_df = df.groupby(['timestamp', 'bot_name'])['price'].mean().reset_index()
        result_df = price_df.sort_values('timestamp')
        
        return self._apply_time_filter(result_df, hours_filter)

    def get_summary_stats(self, bot_name: Optional[str] = None, bot_run: Optional[str] = None,
                         include_all_runs: bool = False, hours_filter: Optional[int] = None) -> Dict[str, Any]:
        """Get summary statistics for the dashboard"""
        if include_all_runs:
            bot_run = None
        
        spot_stats = self.db.read_table('spot_stats', bot_name, bot_run)
        options_stats = self.db.read_table('options_stats', bot_name, bot_run)
        
        if not spot_stats:
            return {
                'total_trades': 0,
                'buy_trades': 0,
                'sell_trades': 0,
                'realized_pnl': 0.0,
                'spot_realized_pnl': 0.0,
                'spot_unrealized_pnl': 0.0,
                'options_unrealized_pnl': 0.0,
                'total_unrealized_pnl': 0.0
            }
        
        latest_spot_stats = spot_stats[-1]
        latest_options_stats = options_stats[-1] if options_stats else None
        
        spot_unrealized = latest_spot_stats.get('spot_unrealized_pnl', 0.0)
        options_unrealized = latest_options_stats.get('total_options_pnl', 0.0) if latest_options_stats else 0.0
        total_unrealized = spot_unrealized + options_unrealized
        spot_realized_pnl = latest_spot_stats.get('spot_realized_pnl', 0.0)

        return {
            'total_trades': latest_spot_stats.get('total_trades', 0),
            'buy_trades': latest_spot_stats.get('buy_trades', 0),
            'sell_trades': latest_spot_stats.get('sell_trades', 0),
            'realized_pnl': latest_spot_stats.get('realized_pnl', 0.0),
            'spot_realized_pnl': spot_realized_pnl,
            'spot_unrealized_pnl': spot_unrealized,
            'options_unrealized_pnl': options_unrealized,
            'total_unrealized_pnl': total_unrealized
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

    def get_run_config(self, bot_name: str, bot_run: str) -> Dict[str, Any]:
        """Get configuration for a specific bot run"""
        runs = self.db.read_table('runs', bot_name, bot_run)
        return runs[0]['config'] if runs else {}
