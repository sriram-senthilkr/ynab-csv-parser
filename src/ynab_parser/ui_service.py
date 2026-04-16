"""
Services for the local upload UI.

Provides:
- live budget/account loading from YNAB
- uploaded CSV preview parsing
- explicit-account uploads without filename-based mapping
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from io import StringIO
from typing import Any, Dict, List
from uuid import uuid4

from .converter import TransactionConverter
from .core.api import YNABClient
from .core.config import ConfigManager
from .core.exceptions import ConfigurationError, ParserError
from .core.logging_config import get_logger
from .core.models import CSVRow
from .parsers.ocbc import OCBCParser
from .parsers.posb import POSBParser

logger = get_logger("ui_service")


@dataclass
class PreviewSession:
    """Transient parsed upload state kept in memory for a single UI session."""

    preview_id: str
    file_name: str
    bank: str
    source_format: str
    transactions: List[CSVRow]
    warning_count: int
    warnings: List[str]


class UploadUIService:
    """Application service backing the one-page upload UI."""

    def __init__(self, env_file: str = ".env"):
        self.config = ConfigManager(env_file)
        self._preview_sessions: Dict[str, PreviewSession] = {}

    def get_budgets(self) -> List[Dict[str, str]]:
        """Fetch budgets from YNAB."""
        with YNABClient(self.config.get_api_token()) as client:
            budgets = client.get_budgets()
        return [{"id": budget.id, "name": budget.name} for budget in budgets]

    def get_accounts(self, budget_id: str) -> List[Dict[str, Any]]:
        """Fetch accounts for a chosen budget."""
        with YNABClient(self.config.get_api_token()) as client:
            accounts = client.get_accounts(budget_id)
        return [
            {
                "id": account.id,
                "name": account.name,
                "type": account.type,
                "closed": account.closed,
                "on_budget": account.on_budget,
            }
            for account in accounts
        ]

    def preview_upload(self, file_name: str, content: str) -> Dict[str, Any]:
        """Parse an uploaded file and persist the preview in memory."""
        source_format = self._detect_source_format(file_name, content)
        bank = self._detect_bank(content, source_format)

        if source_format == "ofx":
            transactions = self._parse_ofx(content, source_name=file_name)
            warning_count = 0
            warnings: List[str] = []
        elif bank == "ocbc":
            parser = OCBCParser()
            transactions = [
                self._prepare_row_for_display(row, source_format)
                for row in parser.parse_text(content, source_name=file_name)
            ]
            warning_count = self._estimate_warning_count(bank, content, len(transactions))
            warnings = []
            if warning_count:
                warnings.append(
                    f"{warning_count} row(s) were skipped because they could not be parsed."
                )
        elif bank == "posb":
            parser = POSBParser()
            transactions = [
                self._prepare_row_for_display(row, source_format)
                for row in parser.parse_text(content, source_name=file_name)
            ]
            warning_count = self._estimate_warning_count(bank, content, len(transactions))
            warnings = []
            if warning_count:
                warnings.append(
                    f"{warning_count} row(s) were skipped because they could not be parsed."
                )
        else:
            raise ParserError(
                message="Unsupported or unrecognized upload format",
                error_code="UNSUPPORTED_UPLOAD",
            )

        preview_id = uuid4().hex
        session = PreviewSession(
            preview_id=preview_id,
            file_name=file_name,
            bank=bank,
            source_format=source_format,
            transactions=transactions,
            warning_count=warning_count,
            warnings=warnings,
        )
        self._preview_sessions[preview_id] = session

        return {
            "preview_id": preview_id,
            "file_name": file_name,
            "bank": bank.upper(),
            "source_format": source_format.upper(),
            "row_count": len(transactions),
            "warning_count": warning_count,
            "warnings": warnings,
            "transactions": [self._row_to_dict(tx) for tx in transactions],
        }

    def upload_preview(
        self,
        preview_id: str,
        budget_id: str,
        account_id: str,
    ) -> Dict[str, Any]:
        """Upload a previewed set of transactions to a selected YNAB account."""
        session = self._preview_sessions.get(preview_id)
        if not session:
            raise ConfigurationError(
                message="Preview session not found or has expired",
                error_code="MISSING_PREVIEW",
            )

        converter = TransactionConverter({})
        transactions = []
        skipped = 0

        for row in session.transactions:
            tx = converter.csv_to_transaction_for_account(row, account_id)
            if tx:
                transactions.append(tx)
            else:
                skipped += 1

        if not transactions:
            raise ParserError(
                message="No valid transactions are available to upload",
                error_code="EMPTY_UPLOAD",
            )

        with YNABClient(self.config.get_api_token()) as client:
            result = client.create_transactions(budget_id, transactions)

        return {
            "uploaded": len(transactions),
            "skipped": skipped,
            "bank": session.bank.upper(),
            "file_name": session.file_name,
            "response": {
                "transaction_count": len(result.get("transactions", [])),
                "duplicate_import_ids": result.get("duplicate_import_ids", []),
            },
        }

    def _detect_source_format(self, file_name: str, content: str) -> str:
        """Detect whether an uploaded file is CSV or OFX."""
        if file_name.lower().endswith(".ofx"):
            return "ofx"
        if "<OFX>" in content.upper():
            return "ofx"
        return "csv"

    def _detect_bank(self, content: str, source_format: str) -> str:
        """Detect the upload source type from content."""
        if source_format == "ofx":
            return "ofx"

        """Detect a supported bank parser from the CSV header rows."""
        reader = csv.reader(StringIO(content))
        for row in reader:
            if not row:
                continue
            first = row[0].strip() if row[0] else ""
            if first == "Transaction date":
                return "ocbc"
            if first == "Transaction Date":
                return "posb"
        return ""

    def _estimate_warning_count(
        self,
        bank: str,
        content: str,
        parsed_count: int,
    ) -> int:
        """Estimate how many non-empty candidate rows were skipped during parsing."""
        reader = csv.reader(StringIO(content))
        header_found = False
        candidate_rows = 0
        header_marker = "Transaction date" if bank == "ocbc" else "Transaction Date"

        for row in reader:
            if not row:
                continue
            first = row[0].strip() if row[0] else ""
            if first == header_marker:
                header_found = True
                continue
            if not header_found:
                continue
            if any(cell.strip() for cell in row):
                candidate_rows += 1

        return max(candidate_rows - parsed_count, 0)

    def _parse_ofx(self, content: str, source_name: str = "<upload>") -> List[CSVRow]:
        """Parse a minimal OFX transaction payload into normalized preview rows."""
        blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", content, flags=re.IGNORECASE | re.DOTALL)
        if not blocks:
            raise ParserError(
                message="No OFX transactions were found in the uploaded file",
                error_code="EMPTY_OFX",
                details={"file": source_name},
            )

        transactions: List[CSVRow] = []
        for block in blocks:
            amount_text = self._extract_ofx_tag(block, "TRNAMT")
            date_text = self._extract_ofx_tag(block, "DTPOSTED")
            payee = self._extract_ofx_tag(block, "NAME") or self._extract_ofx_tag(block, "PAYEE")
            memo = self._extract_ofx_tag(block, "MEMO")

            if not amount_text or not date_text:
                continue

            try:
                amount = float(amount_text.replace(",", ""))
            except ValueError:
                continue

            mmddyyyy = self._parse_ofx_date(date_text)
            outflow = f"{abs(amount):.2f}" if amount < 0 else ""
            inflow = f"{amount:.2f}" if amount > 0 else ""
            if not outflow and not inflow:
                continue

            transactions.append(
                CSVRow(
                    date=mmddyyyy,
                    payee=(payee or "Unknown").strip(),
                    memo=(memo or "").strip(),
                    outflow=outflow,
                    inflow=inflow,
                )
            )

        if not transactions:
            raise ParserError(
                message="The OFX file did not contain any uploadable transactions",
                error_code="EMPTY_OFX",
                details={"file": source_name},
            )

        logger.info("Parsed %s transactions from %s", len(transactions), source_name)
        return transactions

    @staticmethod
    def _extract_ofx_tag(block: str, tag: str) -> str:
        """Extract a simple OFX tag value from a statement block."""
        match = re.search(
            rf"<{tag}>([^<\r\n]+)",
            block,
            flags=re.IGNORECASE,
        )
        return match.group(1).strip() if match else ""

    @staticmethod
    def _parse_ofx_date(value: str) -> str:
        """Convert OFX dates such as 20260309120000 or 20260309 to MM/DD/YYYY."""
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 8:
            raise ParserError(
                message=f"Invalid OFX date: {value}",
                error_code="INVALID_OFX_DATE",
            )
        year, month, day = digits[:4], digits[4:6], digits[6:8]
        return f"{month}/{day}/{year}"

    @staticmethod
    def _prepare_row_for_display(row: CSVRow, source_format: str) -> CSVRow:
        """Apply format-specific transforms before previewing and uploading."""
        if source_format == "csv":
            return CSVRow(
                date=row.date,
                payee=row.memo,
                memo=row.payee,
                outflow=row.outflow,
                inflow=row.inflow,
                extra_fields=row.extra_fields.copy(),
            )
        return row

    @staticmethod
    def _row_to_dict(row: CSVRow) -> Dict[str, Any]:
        return {
            "date": row.date,
            "payee": row.payee,
            "memo": row.memo,
            "outflow": row.outflow or "",
            "inflow": row.inflow or "",
        }
