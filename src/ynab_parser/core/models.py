"""
Data models for YNAB Parser.

Defines dataclasses for:
- Transactions
- Accounts
- Budgets
- API responses
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class TransactionCleared(str, Enum):
    """Transaction cleared status."""

    CLEARED = "cleared"
    UNCLEARED = "uncleared"
    RECONCILED = "reconciled"


class FlagColor(str, Enum):
    """Transaction flag colors."""

    RED = "red"
    ORANGE = "orange"
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"


@dataclass
class Subtransaction:
    """Represents a transaction subtransaction."""

    amount: int
    payee_id: Optional[str] = None
    payee_name: Optional[str] = None
    category_id: Optional[str] = None
    memo: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API request format."""
        return {
            k: v for k, v in asdict(self).items() if v is not None
        }


@dataclass
class Transaction:
    """
    Represents a single transaction.

    YNAB API amounts are in millicents (1/1000th of a cent).
    Example: $100.00 = 10000000 millicents
    """

    account_id: str
    date: str  # Format: YYYY-MM-DD
    amount: int  # In millicents
    payee_id: Optional[str] = None
    payee_name: Optional[str] = None
    category_id: Optional[str] = None
    memo: Optional[str] = None
    cleared: str = TransactionCleared.CLEARED
    approved: bool = True
    flag_color: Optional[str] = None
    subtransactions: List[Subtransaction] = field(default_factory=list)

    def validate(self) -> None:
        """Validate transaction data.

        Raises:
            ValueError: If transaction data is invalid
        """
        if not self.account_id:
            raise ValueError("account_id is required")
        if not self.date:
            raise ValueError("date is required")
        if not isinstance(self.amount, int):
            raise ValueError(f"amount must be int, got {type(self.amount)}")
        
        # Validate date format YYYY-MM-DD
        try:
            datetime.strptime(self.date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"date must be YYYY-MM-DD format, got {self.date}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to API request format.

        Returns:
            Dictionary with only non-None values
        """
        data = asdict(self)
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}

    def to_display(self) -> str:
        """Return human-readable transaction string."""
        amount_display = f"{self.amount / 1000:.2f}"
        return f"{self.date}: {self.payee_name or 'Unknown'} {amount_display}"


@dataclass
class Account:
    """Represents a YNAB account."""

    id: str
    name: str
    type: str
    on_budget: bool = True
    closed: bool = False
    balance: int = 0  # In millicents
    cleared_balance: int = 0
    uncleared_balance: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def __str__(self) -> str:
        """Return human-readable account string."""
        return f"{self.name} ({self.id})"


@dataclass
class Budget:
    """Represents a YNAB budget."""

    id: str
    name: str
    currency_format: Dict[str, Any] = field(default_factory=dict)
    date_format: Dict[str, Any] = field(default_factory=dict)
    last_modified_on: Optional[str] = None
    first_month: Optional[str] = None
    last_month: Optional[str] = None
    accounts: List[Account] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["accounts"] = [a.to_dict() for a in self.accounts]
        return data

    def __str__(self) -> str:
        """Return human-readable budget string."""
        return f"{self.name} ({self.id})"


@dataclass
class CSVRow:
    """Represents a parsed CSV row from a bank statement."""

    date: str
    payee: str
    memo: str
    outflow: Optional[str] = None
    inflow: Optional[str] = None
    extra_fields: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
