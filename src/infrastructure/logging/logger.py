"""
src/infrastructure/logging/logger.py
Centralized application logging configuration integrated with Config Management.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from typing import Optional


def get_logger(name: str = "UCCAnalyzer") -> logging.Logger:
    """
    Returns a configured logger instance for the application.
    Integrates with AppConfig for log level, file logging, rotation, and formatting.

    Args:
        name: Name of the module logger.

    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if logger is already configured
    if logger.handlers:
        return logger

    # Resolve settings from config module (with fallback if config not yet initialized)
    try:
        from src.config import get_config
        cfg = get_config().logging
        level_str = getattr(cfg, "log_level", "INFO").upper()
        log_to_console = getattr(cfg, "log_to_console", True)
        log_to_file = getattr(cfg, "log_to_file", True)
        log_format = getattr(cfg, "log_format", "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
        date_format = getattr(cfg, "date_format", "%Y-%m-%d %H:%M:%S")
        log_file_path = cfg.get_resolved_log_file() if hasattr(cfg, "get_resolved_log_file") else Path("data/logs/ucc_app.log")
        max_bytes = getattr(cfg, "max_bytes", 10 * 1024 * 1024)
        backup_count = getattr(cfg, "backup_count", 5)
    except Exception:
        level_str = "INFO"
        log_to_console = True
        log_to_file = True
        log_format = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        log_file_path = Path("data/logs/ucc_app.log")
        max_bytes = 10 * 1024 * 1024
        backup_count = 5

    level = getattr(logging, level_str, logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(log_format, datefmt=date_format)

    # 1. Console StreamHandler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 2. Rotating FileHandler
    if log_to_file:
        try:
            log_file = Path(log_file_path)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception:
            pass

    return logger
