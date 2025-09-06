import logging
import sys
from typing import Optional
from pathlib import Path

def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    service_name: str = "content-moderator"
) -> logging.Logger:
    """
    Configure comprehensive logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        service_name: Service name for log formatting
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add structured logging for production
    class StructuredFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                'timestamp': self.formatTime(record),
                'level': record.levelname,
                'logger': record.name,
                'function': f"{record.funcName}:{record.lineno}",
                'message': record.getMessage(),
                'service': service_name
            }
            
            if hasattr(record, 'request_id'):
                log_data['request_id'] = record.request_id
            if hasattr(record, 'user_email'):
                log_data['user_email'] = record.user_email
            if hasattr(record, 'classification'):
                log_data['classification'] = record.classification
                
            return f"[{record.levelname}] {record.getMessage()} | {log_data}"
    
    # Use structured formatter for file logs
    if log_file:
        file_handler.setFormatter(StructuredFormatter())
    
    return logger

# Initialize default logger
logger = setup_logging()
