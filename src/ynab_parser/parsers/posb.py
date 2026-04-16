"""
POSB CSV parser for transaction imports.

Converts POSB transaction history to YNAB format.
"""

import csv
from io import StringIO
from typing import List, Optional, Iterator, Dict, Tuple
from pathlib import Path

from . import BankCSVParser, ParserFactory
from ..core.models import CSVRow
from ..core.exceptions import ParserError
from ..core.logging_config import get_logger

logger = get_logger("parsers.posb")


class POSBParser(BankCSVParser):
    """Parser for POSB transaction CSVs."""

    BANK_NAME = "posb"

    def parse_file(self, file_path: str) -> List[CSVRow]:
        """
        Parse POSB CSV file.

        Args:
            file_path: Path to POSB CSV file

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
                message=f"Failed to parse POSB CSV: {e}",
                error_code="PARSE_FAILED",
                details={"file": file_path},
            )

    def parse_text(self, content: str, source_name: str = "<upload>") -> List[CSVRow]:
        """Parse POSB CSV text content."""
        try:
            reader = csv.reader(StringIO(content))
            transactions = list(self._extract_transactions(reader))
            logger.info(f"Parsed {len(transactions)} transactions from {source_name}")
            return transactions
        except Exception as e:
            raise ParserError(
                message=f"Failed to parse POSB CSV: {e}",
                error_code="PARSE_FAILED",
                details={"file": source_name},
            )

    def _extract_transactions(self, reader) -> Iterator[CSVRow]:
        """
        Extract transactions from CSV reader.

        Expects format with header: Transaction Date, Merchant, Amount, Balance

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
            if first_col == "Transaction Date":
                header = [c.strip() for c in row]
                header_found = True
                logger.debug(f"Found POSB header: {header}")
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

            date_str = data.get("Transaction Date", "").strip()
            debit_amount = data.get("Debit Amount", "").strip()
            credit_amount = data.get("Credit Amount", "").strip()

            # Parse date to MM/DD/YYYY (POSB exports use `10 Jan 2026` format)
            date = self.parse_date(date_str, ("%d %b %Y", "%d/%m/%Y"))
            if not date:
                logger.debug(f"Skipping row with invalid date: {date_str}")
                return None

            payee, memo = self._extract_payee_and_memo(data)

            # Determine if debit or credit
            outflow = self._format_amount(debit_amount)
            inflow = self._format_amount(credit_amount)

            # Skip zero transactions
            if not outflow and not inflow:
                logger.debug(f"Skipping zero transaction: {date}")
                return None

            return CSVRow(
                date=date,
                payee=payee,
                memo=memo,
                outflow=outflow,
                inflow=inflow,
            )

        except Exception as e:
            logger.warning(f"Failed to parse POSB row: {e}")
            return None

    def _extract_payee_and_memo(self, data: Dict[str, str]) -> Tuple[str, str]:
        """Derive payee and memo text from the available POSB columns."""
        detail_fields = [
            "Transaction Ref1",
            "Transaction Ref2",
            "Transaction Ref3",
            "Client Reference",
            "Additional Reference",
            "Misc Reference",
        ]

        detail_values = [
            data.get(field, "").strip()
            for field in detail_fields
            if data.get(field, "").strip()
        ]
        reference = data.get("Reference", "").strip()

        primary_desc = detail_values[0] if detail_values else reference
        payee = self.clean_description(primary_desc)
        if not payee:
            payee = "Unknown"

        memo_candidates: List[str] = []
        seen = set()

        def _remember(value: Optional[str]) -> None:
            if value and value not in seen:
                memo_candidates.append(value)
                seen.add(value)

        # Preserve transaction code/context before additional references
        if reference and reference != primary_desc:
            _remember(reference)
        for value in detail_values:
            if value == primary_desc:
                continue
            _remember(value)

        memo = " | ".join(memo_candidates)
        return payee, memo

    @staticmethod
    def _format_amount(amount_str: Optional[str]) -> Optional[str]:
        """
        Format amount for YNAB format.

        Args:
            amount_str: Amount as string

        Returns:
            Formatted amount or None if empty
        """
        amount = POSBParser.parse_amount(amount_str)
        if amount is None or amount == 0:
            return None
        return f"{amount:.2f}"


# Register parser
ParserFactory.register_parser("posb", POSBParser)
