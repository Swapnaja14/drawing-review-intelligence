"""
src/infrastructure/logging/logger.py
Centralized application logging configuration.
"""

import logging
import sys

def get_logger(name: str = "UCCAnalyzer") -> logging.Logger:
    """
    Returns a configured logger instance for the application.

    Args:
        name: Name of the module logger.

    Returns:
        logging.Logger: Configured logger.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
