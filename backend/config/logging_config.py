# config/logging_config.py - COMPLETE FIXED VERSION

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging():
    """
    Setup logging configuration
    
    Returns:
        Configured logger instance
    """
    # Import settings with fallback
    try:
        from config.settings import settings
        log_level = getattr(settings, 'LOG_LEVEL', 'INFO').upper()
        log_to_file = getattr(settings, 'LOG_TO_FILE', True)
        try:
            log_dir = settings.LOGS_DIR
        except AttributeError:
            log_dir = Path(__file__).resolve().parents[1] / "logs"
    except (ImportError, AttributeError) as e:
        print(f"Warning: Could not import settings: {e}")
        log_level = 'INFO'
        log_to_file = True
        log_dir = Path(__file__).resolve().parents[1] / "logs"
    
    # Create logs directory
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create logs directory: {e}")
        log_to_file = False
    
    # Create logger
    logger = logging.getLogger("spectraai")
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # ========== Console Handler ==========
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Console Formatter (Colored)
    console_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # ========== File Handlers ==========
    if log_to_file:
        try:
            # File Handler (All logs)
            log_file = log_dir / f"spectraai_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # File Formatter (Detailed)
            file_format = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)
            
            # Error File Handler (Errors only)
            error_log_file = log_dir / f"spectraai_error_{datetime.now().strftime('%Y%m%d')}.log"
            error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_format)
            logger.addHandler(error_handler)
            
        except Exception as e:
            print(f"Warning: Could not setup file logging: {e}")
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


# Global logger instance
logger = setup_logging()


def get_logger(name: str = None):
    """
    Get a child logger
    
    Args:
        name: Logger name (e.g., 'routes.auth', 'services.ai')
    
    Returns:
        Logger instance
    """
    if name:
        return logger.getChild(name)
    return logger


# Convenience functions
def debug(msg: str, *args, **kwargs):
    """Log debug message"""
    logger.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Log info message"""
    logger.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Log warning message"""
    logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Log error message"""
    logger.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """Log critical message"""
    logger.critical(msg, *args, **kwargs)
