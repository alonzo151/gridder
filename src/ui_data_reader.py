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
