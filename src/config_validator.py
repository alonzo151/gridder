import json
import os
from typing import Dict, Any, List
from src.logger import setup_logger

logger = setup_logger()

class ConfigValidator:
    def __init__(self):
        self.required_fields = {
            'trading_mode': str,
            'binance_api_key': str,
            'binance_api_secret': str,
            'deribit_api_key': str,
            'deribit_api_secret': str,
            'daily_roi_target_for_exit': float,
            'call_option_name': str,
            'call_option_size_base': float,
            'call_option_initial_cost_base': float,
            'put_option_name': str,
            'put_option_initial_cost_base': float,
            'put_option_size_base': float,
            'grid_max_open_orders': int,
            'grid_mode_loop_sleep': float,
            'spot_entry_price': float,
            'spot_down_range_percent': float,
            'spot_up_range_percent': float,
            'spot_order_size_quote': float,
            'spot_orders_diff_percent': float,
            'spot_market': str
        }
        
        self.test_mode_optional_fields = [
            'binance_api_key',
            'binance_api_secret',
            'deribit_api_key',
            'deribit_api_secret'
        ]

    def validate_config(self, config_path: str) -> Dict[str, Any]:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        
        self._validate_required_fields(config)
        self._validate_field_types(config)
        self._validate_trading_mode(config)
        self._validate_ranges(config)
        self._validate_positive_values(config)
        
        logger.info("Configuration validation passed")
        return config

    def _validate_required_fields(self, config: Dict[str, Any]):
        missing_fields = []
        
        for field, field_type in self.required_fields.items():
            if field not in config:
                if config.get('trading_mode') == 'test' and field in self.test_mode_optional_fields:
                    continue
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {missing_fields}")

    def _validate_field_types(self, config: Dict[str, Any]):
        type_errors = []
        
        for field, expected_type in self.required_fields.items():
            if field in config:
                if not isinstance(config[field], expected_type):
                    type_errors.append(f"{field} should be {expected_type.__name__}, got {type(config[field]).__name__}")
        
        if type_errors:
            raise ValueError(f"Type validation errors: {type_errors}")

    def _validate_trading_mode(self, config: Dict[str, Any]):
        valid_modes = ['test', 'live']
        if config['trading_mode'] not in valid_modes:
            raise ValueError(f"trading_mode must be one of {valid_modes}, got {config['trading_mode']}")

    def _validate_ranges(self, config: Dict[str, Any]):
        if config['spot_down_range_percent'] <= 0 or config['spot_down_range_percent'] >= 100:
            raise ValueError("spot_down_range_percent must be between 0 and 100")
        
        if config['spot_up_range_percent'] <= 0 or config['spot_up_range_percent'] >= 100:
            raise ValueError("spot_up_range_percent must be between 0 and 100")
        
        if config['spot_orders_diff_percent'] <= 0:
            raise ValueError("spot_orders_diff_percent must be positive")
        
        if config['daily_roi_target_for_exit'] <= 0:
            raise ValueError("daily_roi_target_for_exit must be positive")

    def _validate_positive_values(self, config: Dict[str, Any]):
        positive_fields = [
            'spot_entry_price',
            'spot_order_size_quote',
            'call_option_size_base',
            'call_option_initial_cost_base',
            'put_option_initial_cost_base',
            'put_option_size_base',
            'grid_mode_loop_sleep'
        ]
        
        for field in positive_fields:
            if field in config and config[field] <= 0:
                raise ValueError(f"{field} must be positive, got {config[field]}")
        
        if config['grid_max_open_orders'] <= 0:
            raise ValueError("grid_max_open_orders must be positive")
