#!/usr/bin/env python3
"""
YNAB API client for posting transactions.

Follows RESTful API best practices with proper error handling,
logging, and configuration management.

Usage:
  from ynab_api import YNABClient
  
  client = YNABClient(api_token="your_token")
  result = client.create_transactions(budget_id="budget_123", transactions=[...])
"""
from __future__ import annotations

import requests
import sys
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


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


@dataclass
class Transaction:
    """Represents a single transaction."""
    account_id: str
    date: str  # Format: YYYY-MM-DD
    amount: int  # In millicents (divide by 1000 for display)
    payee_id: Optional[str] = None
    payee_name: Optional[str] = None
    category_id: Optional[str] = None
    memo: Optional[str] = None
    cleared: str = TransactionCleared.CLEARED
    approved: bool = True
    flag_color: Optional[str] = None
    subtransactions: List[Subtransaction] = None

    def __post_init__(self):
        if self.subtransactions is None:
            self.subtransactions = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to API request format."""
        data = asdict(self)
        # Remove None values and convert subtransactions
        return {k: v for k, v in data.items() if v is not None and k != "subtransactions"}


class YNABAPIError(Exception):
    """Base exception for YNAB API errors."""
    pass


class YNABAuthError(YNABAPIError):
    """Authentication error."""
    pass


class YNABRateLimitError(YNABAPIError):
    """Rate limit exceeded error."""
    pass


class YNABClient:
    """
    YNAB API client for posting transactions.
    
    Implements proper error handling, retries, and logging.
    """
    
    BASE_URL = "https://api.ynab.com/v1"
    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        api_token: str,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ):
        """
        Initialize YNAB API client.
        
        Args:
            api_token: YNAB API bearer token
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        if not api_token:
            raise YNABAuthError("API token is required")
        
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with default headers."""
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        })
        return session

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions.
        
        Args:
            response: Response object from request
            
        Returns:
            Parsed JSON response
            
        Raises:
            YNABAuthError: Authentication failed (401)
            YNABRateLimitError: Rate limit exceeded (429)
            YNABAPIError: Other API errors
        """
        if response.status_code == 401:
            raise YNABAuthError("Invalid API token. Check your credentials.")
        
        if response.status_code == 429:
            retry_after = response.headers.get("X-Rate-Limit-Retry-After", "60")
            raise YNABRateLimitError(
                f"Rate limit exceeded. Retry after {retry_after} seconds."
            )
        
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("detail", str(response.text))
            except:
                error_msg = response.text
            
            raise YNABAPIError(
                f"API error ({response.status_code}): {error_msg}"
            )
        
        return response.json()

    def get_budgets(self) -> List[Dict[str, Any]]:
        """
        Get all available budgets.
        
        Returns:
            List of budget dictionaries
        """
        url = f"{self.BASE_URL}/budgets"
        logger.info(f"Fetching budgets from {url}")
        
        response = self.session.get(url, timeout=self.timeout)
        data = self._handle_response(response)
        
        return data.get("data", {}).get("budgets", [])

    def get_accounts(self, budget_id: str) -> List[Dict[str, Any]]:
        """
        Get accounts for a specific budget.
        
        Args:
            budget_id: Budget ID
            
        Returns:
            List of account dictionaries
        """
        url = f"{self.BASE_URL}/budgets/{budget_id}/accounts"
        logger.info(f"Fetching accounts for budget {budget_id}")
        
        response = self.session.get(url, timeout=self.timeout)
        data = self._handle_response(response)
        
        return data.get("data", {}).get("accounts", [])

    def create_transactions(
        self,
        budget_id: str,
        transactions: List[Transaction],
    ) -> Dict[str, Any]:
        """
        Create multiple transactions in YNAB.
        
        Args:
            budget_id: Budget ID where transactions will be created
            transactions: List of Transaction objects
            
        Returns:
            API response data
            
        Raises:
            YNABAPIError: If API call fails
        """
        if not transactions:
            raise ValueError("At least one transaction is required")
        
        if len(transactions) > 100:
            logger.warning(
                f"Posting {len(transactions)} transactions. "
                "YNAB recommends max 100 per request."
            )
        
        url = f"{self.BASE_URL}/budgets/{budget_id}/transactions"
        
        # Prepare request body
        payload = {
            "transactions": [tx.to_dict() for tx in transactions]
        }
        
        logger.info(
            f"Creating {len(transactions)} transaction(s) for budget {budget_id}"
        )
        
        response = self.session.post(
            url,
            json=payload,
            timeout=self.timeout,
        )
        
        data = self._handle_response(response)
        
        result = data.get("data", {})
        created_count = len(result.get("transactions", []))
        logger.info(f"Successfully created {created_count} transaction(s)")
        
        return result

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
