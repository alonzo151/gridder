import os
import json
from datetime import datetime
from typing import Dict, Any, List
from src.logger import setup_logger

logger = setup_logger()

class SimulativeDatabase:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.max_file_size = 5 * 1024 * 1024
        os.makedirs(self.data_dir, exist_ok=True)
        logger.info(f"Initialized simulative database in {self.data_dir}")

    def save_to_db(self, table_name: str, data: Dict[str, Any], bot_name: str, bot_run: str = None):
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        record = {
            "timestamp": timestamp,
            "bot_name": bot_name,
            "bot_run": bot_run,
            **data
        }
        
        file_path = self._get_current_file_path(table_name)
        
        try:
            with open(file_path, 'a') as f:
                f.write(json.dumps(record) + '\n')
            
            if self._get_file_size(file_path) > self.max_file_size:
                self._rotate_file(table_name)
                
            logger.debug(f"Saved data to {table_name}: {record}")
            
        except Exception as e:
            logger.error(f"Failed to save data to {table_name}: {e}")
            raise

    def _get_current_file_path(self, table_name: str) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        filename = f"{table_name}_{timestamp}.jsonl"
        return os.path.join(self.data_dir, filename)

    def _get_file_size(self, file_path: str) -> int:
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0

    def _rotate_file(self, table_name: str):
        current_time = datetime.utcnow()
        timestamp = current_time.strftime("%Y%m%d_%H%M%S")
        old_filename = f"{table_name}_{current_time.strftime('%Y%m%d')}.jsonl"
        new_filename = f"{table_name}_{timestamp}.jsonl"
        
        old_path = os.path.join(self.data_dir, old_filename)
        new_path = os.path.join(self.data_dir, new_filename)
        
        try:
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                logger.info(f"Rotated file {old_filename} to {new_filename}")
        except Exception as e:
            logger.error(f"Failed to rotate file {old_filename}: {e}")

    def read_table(self, table_name: str, bot_name: str = None, bot_run: str = None) -> List[Dict[str, Any]]:
        records = []
        
        for filename in os.listdir(self.data_dir):
            if filename.startswith(f"{table_name}_") and filename.endswith(".jsonl"):
                file_path = os.path.join(self.data_dir, filename)
                
                try:
                    with open(file_path, 'r') as f:
                        for line in f:
                            if line.strip():
                                record = json.loads(line.strip())
                                if bot_name is None or record.get('bot_name') == bot_name:
                                    if bot_run is None or record.get('bot_run') == bot_run:
                                        records.append(record)
                except Exception as e:
                    logger.error(f"Failed to read file {filename}: {e}")
        
        return sorted(records, key=lambda x: x['timestamp'])

    def save_run_config(self, bot_name: str, bot_run: str, config: Dict[str, Any]):
        """Save bot run configuration to runs table"""
        safe_config = {k: v for k, v in config.items() 
                      if not any(sensitive in k.lower() for sensitive in ['api_key', 'api_secret', 'password'])}
        
        self.save_to_db('runs', {
            'config': safe_config
        }, bot_name, bot_run)

    def get_available_bot_names(self) -> List[str]:
        """Get list of unique bot names"""
        bot_names = set()
        for table in ['trades', 'spot_stats', 'options_stats', 'runs']:
            records = self.read_table(table)
            for record in records:
                if 'bot_name' in record and record['bot_name']:
                    bot_names.add(record['bot_name'])
        return sorted(list(bot_names))

    def get_bot_runs(self, bot_name: str) -> List[Dict[str, Any]]:
        """Get list of runs for a specific bot"""
        runs = self.read_table('runs', bot_name)
        return sorted(runs, key=lambda x: x['timestamp'], reverse=True)

    def get_latest_bot_run(self) -> Dict[str, str]:
        """Get the latest bot name and bot run"""
        runs = self.read_table('runs')
        if not runs:
            return {'bot_name': None, 'bot_run': None}
        
        latest_run = max(runs, key=lambda x: x['timestamp'])
        return {'bot_name': latest_run['bot_name'], 'bot_run': latest_run['bot_run']}
