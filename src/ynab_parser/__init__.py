"""
YNAB CSV Parser - A comprehensive YNAB integration tool.

This package provides:
- Bank CSV parsing and normalization
- YNAB API client with retry logic
- Transaction processing pipeline
- Configuration management
- Extensible architecture for future features (Telegram bot, etc.)
"""

__version__ = "2.0.0"
__author__ = "YNAB Parser Contributors"

from .core.exceptions import (
    YNABParserError,
    ConfigurationError,
    ValidationError,
    ParserError,
    APIError,
    YNABAuthError,
    YNABRateLimitError,
)
from .core.models import Transaction, Account, Budget
from .core.config import ConfigManager
from .core.api import YNABClient

__all__ = [
    "YNABParserError",
    "ConfigurationError",
    "ValidationError",
    "ParserError",
    "APIError",
    "YNABAuthError",
    "YNABRateLimitError",
    "Transaction",
    "Account",
    "Budget",
    "ConfigManager",
    "YNABClient",
]
