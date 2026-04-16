"""
Services for the local upload UI.

Provides:
- live budget/account loading from YNAB
- uploaded CSV preview parsing
- explicit-account uploads without filename-based mapping
"""

from __future__ import annotations

import csv
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
        """Parse an uploaded CSV and persist the preview in memory."""
        bank = self._detect_bank(content)
        if bank == "ocbc":
            parser = OCBCParser()
        elif bank == "posb":
            parser = POSBParser()
        else:
            raise ParserError(
                message="Unsupported or unrecognized bank CSV format",
                error_code="UNSUPPORTED_BANK",
            )

        transactions = parser.parse_text(content, source_name=file_name)
        warning_count = self._estimate_warning_count(bank, content, len(transactions))
        warnings = []
        if warning_count:
            warnings.append(
                f"{warning_count} row(s) were skipped because they could not be parsed."
            )

        preview_id = uuid4().hex
        session = PreviewSession(
            preview_id=preview_id,
            file_name=file_name,
            bank=bank,
            transactions=transactions,
            warning_count=warning_count,
            warnings=warnings,
        )
        self._preview_sessions[preview_id] = session

        return {
            "preview_id": preview_id,
            "file_name": file_name,
            "bank": bank.upper(),
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

    def _detect_bank(self, content: str) -> str:
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

    @staticmethod
    def _row_to_dict(row: CSVRow) -> Dict[str, Any]:
        return {
            "date": row.date,
            "payee": row.payee,
            "memo": row.memo,
            "outflow": row.outflow or "",
            "inflow": row.inflow or "",
        }
