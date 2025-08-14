"""
Logging utilities for PHASe application
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler


class Logger:
    def __init__(self, app_name):
        self.app_name = app_name
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.DEBUG)
        self.setup_logging()

    def get_log_path(self, filename):
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin':
                return os.path.join(os.path.expanduser('~/Library/Logs'), self.app_name, filename)
            else:
                return os.path.join(os.path.dirname(sys.executable), 'logs', filename)
        else:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs', filename)

    def setup_logging(self):
        log_file = self.get_log_path('app.log')
        log_dir = os.path.dirname(log_file)
        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
        console_handler = logging.StreamHandler()

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger


def exception_handler(logger, exc_type, exc_value, exc_traceback):
    """Global exception handler"""
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.exit(1)


# Initialize application logger
app_logger = Logger('PHASe').get_logger()
