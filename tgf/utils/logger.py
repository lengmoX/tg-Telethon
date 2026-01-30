"""
Logging Configuration for TGF
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


# Default format
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str = "tgf",
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console: bool = True
) -> logging.Logger:
    """Setup and configure logger
    
    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        console: Whether to output to console
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "tgf") -> logging.Logger:
    """Get existing logger or create new one"""
    logger = logging.getLogger(name)
    
    # If logger has no handlers, set up basic config
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(handler)
    
    return logger


def get_log_file_path(logs_dir: Path, prefix: str = "tgf") -> Path:
    """Generate log file path with date"""
    date_str = datetime.now().strftime("%Y%m%d")
    return logs_dir / f"{prefix}_{date_str}.log"
