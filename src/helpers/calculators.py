from src.logger import setup_logger
from src.database import SimulativeDatabase

logger = setup_logger()

class Calculator:
    def __init__(self, data_dir: str = "data"):
        self.database = SimulativeDatabase(data_dir)

    def calculate_spot_realized_pnl(self, trades: list) -> float:
        """
        Calculate realized spot PnL for a given bot using FIFO matching.
        Assumes 'trades' table has 'side' ('buy'/'sell'), 'price', 'quantity'.
        """
        if not trades:
            return 0.0

        # Sort trades by timestamp
        trades = sorted(trades, key=lambda x: x['timestamp'])
        open_positions = []  # Each entry: [quantity, price]
        realized_pnl = 0.0
        # sum all buy trades
        for trade in trades:
            side = trade['side'].lower()
            qty = float(trade['quantity'])
            price = float(trade['price'])

            if side == 'buy':
                open_positions.append([qty, price])
            elif side == 'sell':
                qty_to_close = qty
                while qty_to_close > 0 and open_positions:
                    open_qty, open_price = open_positions[0]
                    matched_qty = min(open_qty, qty_to_close)
                    pnl = (price - open_price) * matched_qty
                    realized_pnl += pnl
                    open_positions[0][0] -= matched_qty
                    qty_to_close -= matched_qty
                    if open_positions[0][0] == 0:
                        open_positions.pop(0)
                # If selling more than held, ignore excess (or handle as needed)
        return realized_pnl