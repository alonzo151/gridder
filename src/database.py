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

    def save_to_db(self, table_name: str, data: Dict[str, Any], bot_name: str):
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        record = {
            "timestamp": timestamp,
            "bot_name": bot_name,
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

    def read_table(self, table_name: str, bot_name: str = None) -> List[Dict[str, Any]]:
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
                                    records.append(record)
                except Exception as e:
                    logger.error(f"Failed to read file {filename}: {e}")
        
        return sorted(records, key=lambda x: x['timestamp'])
