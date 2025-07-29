import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.database import SimulativeDatabase
from src.logger import setup_logger

logger = setup_logger()

class UIDataReader:
    def __init__(self, data_dir: str = "data"):
        self.db = SimulativeDatabase(data_dir)
    
    def get_trades_data(self, bot_name: Optional[str] = None) -> pd.DataFrame:
        """Get trades data formatted for chart visualization"""
        records = self.db.read_table('trades', bot_name)
        
        if not records:
            return pd.DataFrame(columns=['timestamp', 'price', 'side', 'quantity', 'bot_name'])
        
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price'] = pd.to_numeric(df['price'])
        df['quantity'] = pd.to_numeric(df['quantity'])
        
        return df
    
    def get_options_pnl_data(self, bot_name: Optional[str] = None) -> pd.DataFrame:
        """Get options PnL data for chart visualization"""
        records = self.db.read_table('options_stats', bot_name)
        
        if not records:
            return pd.DataFrame(columns=['timestamp', 'call_unrealized_pnl', 'put_unrealized_pnl', 'bot_name'])
        
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['call_unrealized_pnl'] = pd.to_numeric(df['call_unrealized_pnl'])
        df['put_unrealized_pnl'] = pd.to_numeric(df['put_unrealized_pnl'])
        
        return df
    
    def get_total_unrealized_pnl_data(self, bot_name: Optional[str] = None) -> pd.DataFrame:
        """Get total unrealized PnL data (spot + options) for chart visualization"""
        spot_records = self.db.read_table('spot_stats', bot_name)
        options_records = self.db.read_table('options_stats', bot_name)
        
        if not spot_records and not options_records:
            return pd.DataFrame(columns=['timestamp', 'total_unrealized_pnl', 'bot_name'])
        
        spot_df = pd.DataFrame(spot_records) if spot_records else pd.DataFrame()
        options_df = pd.DataFrame(options_records) if options_records else pd.DataFrame()
        
        if not spot_df.empty and not options_df.empty:
            spot_df['timestamp'] = pd.to_datetime(spot_df['timestamp'])
            options_df['timestamp'] = pd.to_datetime(options_df['timestamp'])
            
            merged_df = pd.merge_asof(
                spot_df[['timestamp', 'unrealized_pnl', 'bot_name']].sort_values('timestamp'),
                options_df[['timestamp', 'total_options_pnl', 'bot_name']].sort_values('timestamp'),
                on='timestamp', 
                by='bot_name', 
                direction='nearest',
                tolerance=pd.Timedelta(seconds=1)
            )
            
            merged_df['unrealized_pnl'] = merged_df['unrealized_pnl'].fillna(0)
            merged_df['total_options_pnl'] = merged_df['total_options_pnl'].fillna(0)
            merged_df['total_unrealized_pnl'] = merged_df['unrealized_pnl'] + merged_df['total_options_pnl']
            
            merged_df = merged_df.set_index('timestamp')
            merged_df = merged_df.groupby('bot_name')[['unrealized_pnl', 'total_options_pnl', 'total_unrealized_pnl']].resample('5min').last().reset_index()
            merged_df = merged_df.dropna(subset=['total_unrealized_pnl'])
            
            return merged_df[['timestamp', 'total_unrealized_pnl', 'bot_name']].sort_values('timestamp')
        elif not spot_df.empty:
            spot_df['timestamp'] = pd.to_datetime(spot_df['timestamp'])
            spot_df['total_unrealized_pnl'] = spot_df['unrealized_pnl']
            spot_df = spot_df.set_index('timestamp')
            spot_df = spot_df.groupby('bot_name')[['total_unrealized_pnl']].resample('5min').last().reset_index()
            return spot_df[['timestamp', 'total_unrealized_pnl', 'bot_name']].dropna()
        elif not options_df.empty:
            options_df['timestamp'] = pd.to_datetime(options_df['timestamp'])
            options_df['total_unrealized_pnl'] = options_df['total_options_pnl']
            options_df = options_df.set_index('timestamp')
            options_df = options_df.groupby('bot_name')[['total_unrealized_pnl']].resample('5min').last().reset_index()
            return options_df[['timestamp', 'total_unrealized_pnl', 'bot_name']].dropna()
        
        return pd.DataFrame(columns=['timestamp', 'total_unrealized_pnl', 'bot_name'])
    
    def get_price_data(self, bot_name: Optional[str] = None) -> pd.DataFrame:
        """Get BTCFDUSD price data over time for chart visualization"""
        records = self.db.read_table('trades', bot_name)
        
        if not records:
            return pd.DataFrame(columns=['timestamp', 'price', 'bot_name'])
        
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['price'] = pd.to_numeric(df['price'])
        
        price_df = df.groupby(['timestamp', 'bot_name'])['price'].mean().reset_index()
        
        return price_df.sort_values('timestamp')
    
    def get_summary_stats(self, bot_name: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics for the dashboard"""
        spot_stats = self.db.read_table('spot_stats', bot_name)
        
        if not spot_stats:
            return {
                'total_trades': 0,
                'buy_trades': 0,
                'sell_trades': 0,
                'realized_pnl': 0.0,
                'unrealized_pnl': 0.0
            }
        
        latest_stats = spot_stats[-1]
        return {
            'total_trades': latest_stats.get('total_trades', 0),
            'buy_trades': latest_stats.get('buy_trades', 0),
            'sell_trades': latest_stats.get('sell_trades', 0),
            'realized_pnl': latest_stats.get('realized_pnl', 0.0),
            'unrealized_pnl': latest_stats.get('unrealized_pnl', 0.0)
        }
    
    def get_available_bots(self) -> List[str]:
        """Get list of available bot names from all data"""
        bot_names = set()
        
        for table in ['trades', 'spot_stats', 'grid_orders', 'options_stats']:
            records = self.db.read_table(table)
            for record in records:
                if 'bot_name' in record:
                    bot_names.add(record['bot_name'])
        
        return sorted(list(bot_names))
