"""
OCBC CSV parser for transaction imports.

Converts OCBC transaction history to YNAB format.
"""

import csv
from typing import List, Optional, Iterator, Dict, Tuple
from pathlib import Path

from . import BankCSVParser, ParserFactory
from ..core.models import CSVRow
from ..core.exceptions import ParserError
from ..core.logging_config import get_logger

logger = get_logger("parsers.ocbc")


class OCBCParser(BankCSVParser):
    """Parser for OCBC transaction CSVs."""

    BANK_NAME = "ocbc"

    def parse_file(self, file_path: str) -> List[CSVRow]:
        """
        Parse OCBC CSV file.

        Args:
            file_path: Path to OCBC CSV file

        Returns:
            List of CSVRow objects

        Raises:
            ParserError: If file cannot be parsed
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise ParserError(
                    message=f"File not found: {file_path}",
                    error_code="FILE_NOT_FOUND",
                )

            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                transactions = list(self._extract_transactions(reader))

            logger.info(f"Parsed {len(transactions)} transactions from {path.name}")
            return transactions

        except ParserError:
            raise
        except Exception as e:
            raise ParserError(
                message=f"Failed to parse OCBC CSV: {e}",
                error_code="PARSE_FAILED",
                details={"file": file_path},
            )

    def _extract_transactions(self, reader) -> Iterator[CSVRow]:
        """
        Extract transactions from CSV reader.

        Expects format with header: Transaction date, Reference, Debit, Credit

        Yields:
            CSVRow objects
        """
        header = None
        header_found = False

        for row in reader:
            if not row:
                continue

            first_col = row[0].strip() if row else ""

            # Look for header row
            if first_col == "Transaction date":
                header = [c.strip() for c in row]
                header_found = True
                logger.debug(f"Found OCBC header: {header}")
                continue

            # Only process rows after header found
            if not header_found:
                continue

            # Skip empty rows
            if not any(cell.strip() for cell in row):
                continue

            # Parse transaction
            tx = self._parse_row(row, header)
            if tx:
                yield tx

    def _parse_row(self, row: List[str], header: List[str]) -> Optional[CSVRow]:
        """
        Parse single transaction row.

        Args:
            row: CSV row values
            header: Column headers

        Returns:
            CSVRow or None if invalid
        """
        try:
            # Map values to headers
            data = {h: (row[i] if i < len(row) else "") for i, h in enumerate(header)}

            date_str = data.get("Transaction date", "").strip()
            reference = data.get("Reference", "").strip()
            debit = data.get("Debit", "").strip()
            credit = data.get("Credit", "").strip()

            # Parse date to MM/DD/YYYY
            date = self.parse_date(date_str, "%d/%m/%Y")
            if not date:
                logger.debug(f"Skipping row with invalid date: {date_str}")
                return None

            # Clean description
            payee = self.clean_description(reference)
            if not payee:
                payee = "Unknown"

            # Convert amounts
            outflow = self._format_amount(debit)
            inflow = self._format_amount(credit)

            # Skip zero transactions
            if not outflow and not inflow:
                logger.debug(f"Skipping zero transaction: {date}")
                return None

            return CSVRow(
                date=date,
                payee=payee,
                memo="",
                outflow=outflow,
                inflow=inflow,
            )

        except Exception as e:
            logger.warning(f"Failed to parse OCBC row: {e}")
            return None

    @staticmethod
    def _format_amount(amount_str: Optional[str]) -> Optional[str]:
        """
        Format amount for YNAB format.

        Args:
            amount_str: Amount as string

        Returns:
            Formatted amount or None if empty
        """
        amount = OCBCParser.parse_amount(amount_str)
        if amount is None or amount == 0:
            return None
        return f"{amount:.2f}"


# Register parser
ParserFactory.register_parser("ocbc", OCBCParser)
