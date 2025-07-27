import logging
import os
from datetime import datetime, timedelta
import colorlog
import sys

class CustomFileHandler(logging.Handler):
    def __init__(self, log_dir=None):
        super().__init__()
        self.current_time = None
        self.file = None
        config_name = sys.argv[1] if len(sys.argv) > 1 else None
        if config_name:
            config_name = config_name.split(".")[0]
        else:
            config_name = 'default'
        print(sys.argv)
        process_name = sys.argv[0].split("/")[-1] if len(sys.argv) > 1 else None
        
        root_dir = os.path.abspath(os.path.dirname(__file__))
        if config_name and "/" in config_name:
            config_name = config_name.split("/")[-1]
        if process_name and "." in process_name:
            process_name = process_name.split(".")[0]
        if not process_name:
            process_name = 'default'
        if log_dir is None:
            log_dir = os.path.join(root_dir, 'logs', process_name, config_name)
        else:
            log_dir = os.path.join(root_dir, log_dir)
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.cleanup_old_logs()

    def emit(self, record):
        try:
            msg = self.format(record)
            now = datetime.now()
            timestamp = now.strftime("%Y-%m-%d-%H")
            
            if self.current_time != timestamp:
                self.current_time = timestamp
                if self.file:
                    self.file.close()
                self.file = open(os.path.join(self.log_dir, f"{self.current_time}.txt"), "a")
                self.cleanup_old_logs()
            
            self.file.write(msg + '\n')
            self.file.flush()
        except Exception:
            self.handleError(record)

    def cleanup_old_logs(self):
        now = datetime.now()
        cutoff = now - timedelta(days=14)
        
        for filename in os.listdir(self.log_dir):
            filepath = os.path.join(self.log_dir, filename)
            
            if os.path.isfile(filepath):
                try:
                    timestamp_str = datetime.strptime(filename.split('.')[0], "%Y-%m-%d-%H")
                    
                    if timestamp_str < cutoff:
                        os.remove(filepath)
                        print(f"Deleted old log file: {filepath}")
                except Exception as e:
                    print(f"Error parsing date from filename {filename}: {e}")

def setup_logger(name='my_logger'):
    logger = logging.getLogger(name)
    
    if not logger.hasHandlers():
        logger.setLevel(logging.INFO)
        
        file_handler = CustomFileHandler()
        file_handler.setLevel(logging.DEBUG)
        
        log_format = "%(log_color)s%(asctime)s|%(filename)s|%(funcName)s|%(message)s"
        
        color_formatter = colorlog.ColoredFormatter(
            log_format,
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'light_white',
                'INFO': 'light_white',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            }
        )
        file_formatter = logging.Formatter("%(asctime)s|%(filename)s|%(funcName)s|%(message)s")
        file_handler.setFormatter(file_formatter)
        
        stream_handler = colorlog.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(color_formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
    
    return logger
