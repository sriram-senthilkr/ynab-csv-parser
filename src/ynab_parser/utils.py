"""
Type hints and validation utilities for YNAB Parser.

Provides type-safe operations and validation helpers.
"""

from typing import Dict, Any, Optional, List, TypeVar, Callable
from datetime import datetime

T = TypeVar('T')


def validate_date_format(date_str: str, format_str: str = "%Y-%m-%d") -> bool:
    """
    Validate date string format.

    Args:
        date_str: Date string to validate
        format_str: Expected format

    Returns:
        True if valid
    """
    try:
        datetime.strptime(date_str, format_str)
        return True
    except ValueError:
        return False


def validate_account_id(account_id: str) -> bool:
    """
    Validate YNAB account ID format.

    Args:
        account_id: Account ID to validate

    Returns:
        True if valid (non-empty string)
    """
    return bool(account_id and account_id.strip())


def validate_amount_millicents(amount: int) -> bool:
    """
    Validate amount in millicents.

    Args:
        amount: Amount to validate

    Returns:
        True if valid integer
    """
    return isinstance(amount, int)


def safe_get(
    data: Dict[str, Any],
    key: str,
    default: Optional[T] = None,
    type_check: Optional[type] = None,
) -> T:
    """
    Safely get dictionary value with type checking.

    Args:
        data: Dictionary to access
        key: Key to get
        default: Default value if key not found
        type_check: Optional type to verify

    Returns:
        Value or default
    """
    value = data.get(key, default)

    if value is not None and type_check and not isinstance(value, type_check):
        return default

    return value
