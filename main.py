#!/usr/bin/env python3

import sys
import os
import argparse
from src.config_validator import ConfigValidator
from src.trader_bot import TraderBot
from src.logger import setup_logger

def main():
    parser = argparse.ArgumentParser(description='Gridder - Spot Grid Trading Bot with Options Protection')
    parser.add_argument('config', help='Path to configuration JSON file')
    parser.add_argument('--validate-only', action='store_true', help='Only validate configuration and exit')
    
    args = parser.parse_args()
    
    logger = setup_logger()
    
    try:
        validator = ConfigValidator()
        config = validator.validate_config(args.config)
        
        if args.validate_only:
            logger.info("Configuration validation successful")
            return 0
        
        bot = TraderBot(config)
        bot.start()
        
        return 0
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
