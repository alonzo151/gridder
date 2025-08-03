# src/table_schema_manager.py

from typing import Dict, List, Any

class TableSchemaManager:
    _schemas = {
        'trades': [
            'timestamp',
            'side',
            'price',
            'quantity',
            'bot_name',
            'mode',
            'bot_name',
            'bot_run'
        ],
        'spot_stats': [
            'realized_pnl',
            'spot_unrealized_pnl',
            'spot_realized_pnl',
            'buy_trades',
            'sell_trades',
            'total_trades',
            'mode',
            'bot_name',
            'bot_run'
        ],
        'runs': [
            'bot_name',
            'bot_run',
            'config'
        ],
        'options_stats': [
            'call_unrealized_pnl',
            'put_unrealized_pnl',
            'total_options_pnl',
            'mode',
            'bot_name',
            'bot_run'
        ],
        'bot_shutdown': [
            'final_pnl',
            'buy_trades',
            'sell_trades',
            'total_trades',
            'running_time_hours',
            'mode',
            'bot_name',
            'bot_run'
        ]
    }

    _defaults = {
        'trades': {
            'mode': 'unknown',
            'quantity': 0.0,
            'bot_name': 'unknown',
            'bot_run': 'unknown',
        },
        'spot_stats': {
            'realized_pnl': 0.0,
            'spot_unrealized_pnl': 0.0,
            'spot_realized_pnl': 0.0,
            'buy_trades': 0,
            'sell_trades': 0,
            'total_trades': 0,
            'mode': 'unknown',
            'bot_name': 'unknown',
            'bot_run': 'unknown',
        },
        'runs': {
            'bot_name': 'unknown',
            'bot_run': 'unknown',
            'config': 'unknown'
        },
        'options_stats': {
            'call_unrealized_pnl': 0.0,
            'put_unrealized_pnl': 0.0,
            'total_options_pnl': 0.0,
            'mode': 'unknown',
            'bot_name': 'unknown',
            'bot_run': 'unknown',
        },
        'bot_shutdown': {
            'final_pnl': 0.0,
            'buy_trades': 0,
            'sell_trades': 0,
            'total_trades': 0,
            'running_time_hours': 0.0,
            'mode': 'unknown',
            'bot_name': 'unknown',
            'bot_run': 'unknown',
        }
    }

    @classmethod
    def get_fields(cls, table_name: str) -> List[str]:
        return cls._schemas.get(table_name, [])

    @classmethod
    def format_data(cls, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        fields = cls.get_fields(table_name)
        defaults = cls._defaults.get(table_name, {})
        return {k: data.get(k, defaults.get(k)) for k in fields}

    @classmethod
    def validate_data(cls, table_name: str, data: Dict[str, Any]) -> bool:
        fields = set(cls.get_fields(table_name))
        return fields.issubset(data.keys())