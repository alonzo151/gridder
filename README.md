# Gridder - Spot Grid Trading Bot with Options Protection

A sophisticated Bitcoin spot grid trading bot that combines spot grid trading with options protection strategies. The system places dense grid orders in small price gaps and uses put/call options to protect against adverse price movements.

## Features

- **Spot Grid Trading**: Dense grid of buy/sell orders across a price range
- **Options Protection**: Put and call options to hedge against price movements
- **Test Mode**: Full simulation without real trading for safe testing
- **Live Mode**: Real trading with Binance and Deribit integration
- **Comprehensive Logging**: Detailed logging with file rotation
- **Database Simulation**: Local file-based storage for trade data
- **PnL Tracking**: Real-time monitoring of realized and unrealized profits
- **Automatic Take Profit**: Exits when daily ROI target is reached

## System Architecture

The system consists of several key components:

- **Trader Bot**: Main orchestrator that manages the trading loop
- **Grid Calculator**: Calculates optimal grid order placement
- **Binance Integration**: REST API wrapper for spot trading
- **Deribit Integration**: REST API wrapper for options data
- **Database**: Simulative database using local files
- **Logger**: Comprehensive logging with colored console output
- **Config Validator**: Validates all configuration parameters

## Installation

1. Clone the repository:
```bash
git clone https://github.com/alonzo151/gridder.git
cd gridder
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The system uses JSON configuration files. Two modes are supported:

### Configuration
The system uses a single configuration file `config/config.json` that supports both test and live modes:

**Test Mode** (`"trading_mode": "test"`):
- API keys can be placeholder values (not used for trading)
- Simulates order placement and balance changes
- Uses real price data from exchanges
- Safe for development and testing

**Live Mode** (`"trading_mode": "live"`):
- Requires valid Binance and Deribit API keys
- Executes real trades with real money
- Use with extreme caution

### Configuration Parameters

- `trading_mode`: "test" or "live"
- `daily_roi_target_for_exit`: Target daily ROI to trigger take profit (e.g., 0.05 = 5%)
- `spot_entry_price`: Starting price for grid calculation
- `spot_down_range_percent`: Grid range below entry price (%)
- `spot_up_range_percent`: Grid range above entry price (%)
- `spot_order_size_quote`: Size of each grid order in quote currency
- `spot_orders_diff_percent`: Price difference between grid orders (%)
- `grid_max_open_orders`: Maximum orders on each side of the grid
- `grid_mode_loop_sleep`: Sleep time between trading loops (seconds)

## Usage

### Validate Configuration
```bash
python main.py config/config.json --validate-only
```

### Run in Test Mode
Set `"trading_mode": "test"` in config/config.json, then:
```bash
python main.py config/config.json
```

### Run in Live Mode (Use with caution!)
Set `"trading_mode": "live"` and add your API credentials to config/config.json, then:
```bash
python main.py config/config.json
```

## Safety Features

- **Test Mode**: Complete simulation without real trading
- **Configuration Validation**: Comprehensive parameter validation
- **Boundary Detection**: Warns when price crosses grid boundaries
- **Automatic Shutdown**: Stops trading when ROI target is reached
- **Comprehensive Logging**: All actions are logged for audit

## Data Storage

The system stores data in local files under the `data/` directory:
- `options_stats`: Options PnL and pricing data
- `spot_stats`: Spot trading statistics
- `grid_orders`: Grid order configuration data
- `bot_shutdown`: Final bot statistics

## Logging

Logs are stored in the `logs/` directory with:
- Hourly log rotation
- 14-day retention policy
- Colored console output
- Structured log format

## Risk Warning

⚠️ **IMPORTANT**: This system trades real cryptocurrency and can result in financial loss. 

- Always test thoroughly in test mode before using live mode
- Start with small amounts in live mode
- Monitor the system closely during operation
- Understand the risks of grid trading and options strategies
- The system is provided as-is without warranty

## Development

### Project Structure
```
gridder/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── config/                 # Configuration files
│   └── config.json        # Single configuration file (test/live modes)
├── src/                    # Source code
│   ├── trader_bot.py      # Main trading bot
│   ├── grid_calculator.py # Grid order calculation
│   ├── binance_integration.py
│   ├── deribit_integration.py
│   ├── database.py        # Data storage
│   ├── logger.py          # Logging system
│   └── config_validator.py
├── data/                   # Data files (created at runtime)
└── logs/                   # Log files (created at runtime)
```

### Testing
Run the system in test mode to verify functionality:
```bash
python main.py config/config.json
```

## License

This project is provided under the MIT License. See LICENSE file for details.

## Disclaimer

This software is for educational and research purposes. Trading cryptocurrencies involves substantial risk of loss. The authors are not responsible for any financial losses incurred through the use of this software.
