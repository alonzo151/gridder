# src/migrate_tables.py
from src.logger import setup_logger
import os
import json
from src.table_schema_manager import TableSchemaManager
logger = setup_logger()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

def migrate_table(table_name: str):
    for filename in os.listdir(DATA_DIR):
        if filename.startswith(f"{table_name}_") and filename.endswith(".jsonl"):
            file_path = os.path.join(DATA_DIR, filename)
            migrated_records = []
            changed = False

            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line.strip())
                        formatted = TableSchemaManager.format_data(table_name, record)
                        # Preserve extra fields, but update missing ones
                        updated_record = {**record, **formatted}
                        if updated_record != record:
                            changed = True
                        logger.warning(f"Record {record} changed from {formatted} to {updated_record}")
                        migrated_records.append(updated_record)

            if changed:
                with open(file_path, 'w') as f:
                    for rec in migrated_records:
                        f.write(json.dumps(rec) + '\n')
                print(f"Migrated {file_path}")

def migrate_all_tables():
    for table_name in TableSchemaManager._schemas.keys():
        migrate_table(table_name)

if __name__ == "__main__":
    migrate_all_tables()