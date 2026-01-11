"""
Parser interface and utilities.

Defines the contract for bank CSV parsers to ensure consistency
and enable future extensibility.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Iterator, Sequence, Union
from pathlib import Path
import re

from ..core.models import CSVRow
from ..core.exceptions import ParserError
from ..core.logging_config import get_logger

logger = get_logger("parsers")


class BankCSVParser(ABC):
    """
    Abstract base class for bank CSV parsers.

    Each bank has different CSV formats. Parsers must:
    1. Locate the header row
    2. Extract transactions
    3. Normalize to standard format (Date, Payee, Memo, Outflow, Inflow)
    """

    # Bank identifier
    BANK_NAME: str = ""

    # Expected columns in output
    OUTPUT_COLUMNS = ["Date", "Payee", "Memo", "Outflow", "Inflow"]

    @abstractmethod
    def parse_file(self, file_path: str) -> List[CSVRow]:
        """
        Parse a CSV file and return list of transactions.

        Args:
            file_path: Path to CSV file

        Returns:
            List of CSVRow objects

        Raises:
            ParserError: If parsing fails
        """
        pass

    @staticmethod
    def clean_description(desc: Optional[str]) -> str:
        """
        Clean and normalize description/payee text.

        Args:
            desc: Raw description text

        Returns:
            Cleaned description
        """
        if not desc:
            return ""

        # Collapse whitespace
        s = re.sub(r"\s+", " ", desc).strip()

        # Remove repeating trailing dates (e.g., 13/12/25)
        s = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", "", s).strip()

        # Remove long runs of non-word separators
        s = re.sub(r"[-]{2,}", "", s).strip()

        return s

    @staticmethod
    def parse_amount(amount_str: Optional[str]) -> Optional[float]:
        """
        Parse amount string to float.

        Args:
            amount_str: Amount as string with optional commas

        Returns:
            Amount as float or None if invalid
        """
        if not amount_str or not amount_str.strip():
            return None

        try:
            # Remove commas and spaces
            cleaned = amount_str.replace(",", "").replace(" ", "").strip()
            return float(cleaned)
        except ValueError:
            logger.warning(f"Failed to parse amount: {amount_str}")
            return None

    @staticmethod
    def parse_date(
        date_str: str,
        format_str: Union[str, Sequence[str]] = "%d/%m/%Y",
    ) -> Optional[str]:
        """
        Parse date string and return in MM/DD/YYYY format.

        Args:
            date_str: Date as string
            format_str: Expected date format or iterable of formats

        Returns:
            Date in MM/DD/YYYY format or None if invalid

        Note:
            YNAB parsers output dates as MM/DD/YYYY for compatibility
        """
        from datetime import datetime

        if not date_str or not date_str.strip():
            return None

        formats: Sequence[str]
        if isinstance(format_str, str):
            formats = (format_str,)
        else:
            formats = tuple(format_str)

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime("%m/%d/%Y")
            except ValueError:
                continue

        logger.warning(f"Failed to parse date: {date_str}")
        return None


class ParserFactory:
    """Factory for creating appropriate parser instances."""

    _parsers: Dict[str, type] = {}

    @classmethod
    def register_parser(cls, bank_name: str, parser_class: type) -> None:
        """
        Register a parser class for a bank.

        Args:
            bank_name: Bank identifier
            parser_class: Parser class
        """
        cls._parsers[bank_name.lower()] = parser_class
        logger.debug(f"Registered parser for {bank_name}")

    @classmethod
    def get_parser(cls, bank_name: str) -> BankCSVParser:
        """
        Get parser instance for a bank.

        Args:
            bank_name: Bank identifier

        Returns:
            Parser instance

        Raises:
            ParserError: If no parser registered for bank
        """
        parser_class = cls._parsers.get(bank_name.lower())
        if not parser_class:
            raise ParserError(
                message=f"No parser available for bank: {bank_name}",
                error_code="UNKNOWN_BANK",
                details={"available_banks": list(cls._parsers.keys())},
            )
        return parser_class()

    @classmethod
    def get_supported_banks(cls) -> List[str]:
        """Get list of supported banks."""
        return list(cls._parsers.keys())


# Auto-import parser implementations to register them
try:
    from . import ocbc  # noqa: F401
    from . import posb  # noqa: F401
except ImportError as e:
    logger.debug(f"Could not import parsers: {e}")

__all__ = ["BankCSVParser", "ParserFactory"]
