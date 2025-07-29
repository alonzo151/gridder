#!/usr/bin/env python3

import sys
sys.path.append('.')

from src.database import SimulativeDatabase
from datetime import datetime, timedelta
import random

def create_sample_trades():
    """Create sample trades data for testing the UI"""
    db = SimulativeDatabase()
    
    base_time = datetime.utcnow() - timedelta(hours=1)
    base_price = 100000.0
    bot_name = "sample_bot_test"
    
    for i in range(20):
        price_change = random.uniform(-500, 500)
        price = base_price + price_change
        
        side = random.choice(['BUY', 'SELL'])
        
        quantity = random.uniform(0.0001, 0.001)
        
        timestamp = base_time + timedelta(minutes=i*3)
        
        trade_data = {
            'side': side,
            'price': price,
            'quantity': quantity,
            'mode': 'test'
        }
        
        db.save_to_db('trades', trade_data, bot_name)
        print(f"Created sample trade: {side} {quantity:.6f} at ${price:.2f}")

if __name__ == "__main__":
    create_sample_trades()
    print("Sample trades data created successfully!")
