"""
Logging configuration for YNAB Parser.

Provides structured logging with:
- JSON formatters for machine-readable logs
- Color support for terminal output
- Log file handlers
- Telegram bot compatibility
"""

import logging
import sys
from typing import Optional
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",      # Cyan
        "INFO": "\033[32m",       # Green
        "WARNING": "\033[33m",    # Yellow
        "ERROR": "\033[31m",      # Red
        "CRITICAL": "\033[35m",   # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    name: Optional[str] = None,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    use_colors: bool = True,
) -> logging.Logger:
    """
    Setup logging configuration.

    Args:
        name: Logger name (usually __name__)
        level: Logging level (default: INFO)
        log_file: Optional log file path
        use_colors: Enable colored output

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name or "ynab_parser")
    logger.setLevel(level)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if use_colors:
        formatter = ColoredFormatter(log_format)
    else:
        formatter = logging.Formatter(log_format)

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a module."""
    return logging.getLogger(f"ynab_parser.{name}")
