#!/usr/bin/env python3

import sys
sys.path.append('.')

from src.config_validator import ConfigValidator
from src.grid_calculator import GridCalculator
from src.binance_integration import BinanceIntegration

def test_implementation():
    print("Testing Gridder implementation...")
    
    try:
        validator = ConfigValidator()
        config = validator.validate_config('config/test_config.json')
        print('✓ Configuration validation passed')
    except Exception as e:
        print(f'✗ Configuration validation failed: {e}')
        return False
    
    try:
        binance = BinanceIntegration(test_mode=True)
        price_tick = binance.get_price_tick('BTCFDUSD')
        print(f'✓ Price tick retrieved: {price_tick}')
    except Exception as e:
        print(f'✗ Binance integration failed: {e}')
        return False
    
    try:
        grid_calc = GridCalculator(config, price_tick)
        orders_df, base_needed, quote_needed = grid_calc.calculate_grid_orders()
        print(f'✓ Grid calculator generated {len(orders_df)} orders')
        print(f'✓ Initial funds needed - Base: {base_needed:.6f}, Quote: {quote_needed:.2f}')
    except Exception as e:
        print(f'✗ Grid calculator failed: {e}')
        return False
    
    print("All tests passed!")
    return True

if __name__ == "__main__":
    success = test_implementation()
    sys.exit(0 if success else 1)
