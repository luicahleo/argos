"""
ARGOS - Logging Configuration
Logs are cleared on each startup for clean trace reading
"""

import os
import logging
from datetime import datetime

# Create logs directory if not exists
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Log file path
LOG_FILE = os.path.join(LOGS_DIR, 'argos.log')


class ArgosFormatter(logging.Formatter):
    """Custom formatter for ARGOS logs"""
    
    def format(self, record):
        # Add custom fields
        record.class_method = f"{record.module}.{record.funcName}"
        return super().format(record)


def setup_logger(name: str = 'argos', level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return the ARGOS logger.
    Log file is cleared on each startup for clean trace.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # File handler - mode='w' clears the file on each startup
    file_handler = logging.FileHandler(
        LOG_FILE,
        mode='w',  # 'w' = write mode (clears file), 'a' = append mode
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # Formatter
    formatter = ArgosFormatter(
        fmt='[%(asctime)s] %(levelname)s - %(class_method)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Create default logger instance
logger = setup_logger()


def log_request(endpoint: str, data: dict = None, client_ip: str = None):
    """Log incoming API request"""
    msg = f"Request to {endpoint}"
    if client_ip:
        msg += f" from {client_ip}"
    if data:
        # Don't log full base64 images
        safe_data = {k: (v[:50] + '...' if isinstance(v, str) and len(v) > 50 else v) 
                     for k, v in data.items()}
        msg += f" | Data keys: {list(safe_data.keys())}"
    logger.info(msg)


def log_response(endpoint: str, success: bool, details: str = None, duration_ms: float = None):
    """Log API response"""
    status = "SUCCESS" if success else "FAILED"
    msg = f"Response from {endpoint}: {status}"
    if details:
        msg += f" | {details}"
    if duration_ms:
        msg += f" | Duration: {duration_ms:.2f}ms"
    
    if success:
        logger.info(msg)
    else:
        logger.warning(msg)


def log_error(endpoint: str, error: Exception, context: str = None):
    """Log error with traceback"""
    msg = f"Error in {endpoint}: {str(error)}"
    if context:
        msg += f" | Context: {context}"
    logger.error(msg, exc_info=True)


def log_model_operation(operation: str, model: str, duration_ms: float = None):
    """Log DeepFace model operations"""
    msg = f"Model operation: {operation} | Model: {model}"
    if duration_ms:
        msg += f" | Duration: {duration_ms:.2f}ms"
    logger.info(msg)
