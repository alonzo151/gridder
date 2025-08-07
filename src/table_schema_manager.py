
from typing import Dict, List, Any, Tuple, Union

class TableSchemaManager:
    # Each field is either a string (no default) or a tuple (field, default)
    _schemas = {
        'trades': [
            'timestamp',
            'side',
            'price',
            ('quantity', 0.0),
            ('bot_name', 'unknown'),
            ('mode', 'unknown'),
            ('bot_run', 'unknown')
        ],
        'stats': [
            ('spot_unrealized_pnl', 0.0),
            ('call_unrealized_pnl', 0.0),
            ('put_unrealized_pnl', 0.0),
            ('mode', 'unknown'),
            ('bot_name', 'unknown'),
            ('bot_run', 'unknown')
        ],
        'runs': [
            ('bot_name', 'unknown'),
            ('bot_run', 'unknown'),
            ('config', 'unknown')
        ],
        'bot_shutdown': [
            ('final_pnl', 0.0),
            ('buy_trades', 0),
            ('sell_trades', 0),
            ('total_trades', 0),
            ('running_time_hours', 0.0),
            ('mode', 'unknown'),
            ('bot_name', 'unknown'),
            ('bot_run', 'unknown')
        ]
    }

    @classmethod
    def get_fields(cls, table_name: str) -> List[str]:
        return [
            f[0] if isinstance(f, tuple) else f
            for f in cls._schemas.get(table_name, [])
        ]

    @classmethod
    def get_defaults(cls, table_name: str) -> Dict[str, Any]:
        return {
            (f[0] if isinstance(f, tuple) else f): (f[1] if isinstance(f, tuple) else None)
            for f in cls._schemas.get(table_name, [])
        }

    @classmethod
    def format_data(cls, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        fields = cls.get_fields(table_name)
        defaults = cls.get_defaults(table_name)
        return {k: data.get(k, defaults.get(k)) for k in fields}

    @classmethod
    def validate_data(cls, table_name: str, data: Dict[str, Any]) -> bool:
        fields = set(cls.get_fields(table_name))
        return fields.issubset(data.keys())