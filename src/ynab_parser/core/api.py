"""
YNAB API client with proper error handling, retries, and logging.

Features:
- RESTful API implementation
- Automatic retry logic with exponential backoff
- Comprehensive error handling
- Context manager support
- Type hints and validation
"""

from typing import Dict, List, Any, Optional
import requests
import time
import logging

from .models import Transaction, Account, Budget
from .exceptions import (
    APIError,
    YNABAuthError,
    YNABRateLimitError,
    NotFoundError,
)


logger = logging.getLogger(__name__)


class YNABClient:
    """
    YNAB API client with retry logic and error handling.

    Implements:
    - Automatic retries with exponential backoff
    - Proper error classification
    - Rate limit handling
    - Context manager support
    - Comprehensive logging
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
            max_retries: Maximum number of retries

        Raises:
            ValueError: If api_token is empty
        """
        if not api_token or not api_token.strip():
            raise ValueError("API token is required and cannot be empty")

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

    def _handle_response(
        self,
        response: requests.Response,
        endpoint: str = "",
    ) -> Dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: Response object from request
            endpoint: Endpoint for logging

        Returns:
            Parsed JSON response

        Raises:
            YNABAuthError: Authentication failed (401)
            YNABRateLimitError: Rate limit exceeded (429)
            NotFoundError: Resource not found (404)
            APIError: Other API errors
        """
        if response.status_code == 401:
            logger.error(f"Authentication failed for {endpoint}")
            raise YNABAuthError(
                message="Invalid or expired API token",
                status_code=401,
            )

        if response.status_code == 429:
            retry_after = int(response.headers.get("X-Rate-Limit-Retry-After", "60"))
            logger.warning(
                f"Rate limit exceeded for {endpoint}. Retry after {retry_after}s"
            )
            raise YNABRateLimitError(
                message="API rate limit exceeded",
                retry_after=retry_after,
            )

        if response.status_code == 404:
            logger.warning(f"Resource not found: {endpoint}")
            raise NotFoundError(
                message=f"Resource not found: {endpoint}",
                status_code=404,
            )

        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = (
                    error_data.get("error", {}).get("detail")
                    or error_data.get("error", "")
                    or response.text
                )
            except Exception:
                error_msg = response.text or f"HTTP {response.status_code}"

            logger.error(
                f"API error for {endpoint}: {response.status_code} - {error_msg}"
            )
            raise APIError(
                message=error_msg,
                status_code=response.status_code,
                response_data=error_data if "error_data" in locals() else None,
            )

        try:
            return response.json()
        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise APIError(
                message=f"Failed to parse API response: {e}",
                status_code=response.status_code,
            )

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with automatic retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint relative to BASE_URL
            **kwargs: Additional arguments for requests

        Returns:
            Parsed JSON response

        Raises:
            APIError: If request fails after all retries
        """
        url = f"{self.BASE_URL}{endpoint}"
        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            try:
                logger.debug(f"{method} {url} (attempt {attempt + 1}/{self.max_retries})")

                if method == "GET":
                    response = self.session.get(url, timeout=self.timeout, **kwargs)
                elif method == "POST":
                    response = self.session.post(url, timeout=self.timeout, **kwargs)
                elif method == "PATCH":
                    response = self.session.patch(url, timeout=self.timeout, **kwargs)
                elif method == "DELETE":
                    response = self.session.delete(url, timeout=self.timeout, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                return self._handle_response(response, endpoint)

            except YNABRateLimitError as e:
                # For rate limiting, wait and retry
                last_error = e
                wait_time = e.retry_after + (2 ** attempt)  # Exponential backoff
                logger.info(f"Rate limited. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                attempt += 1

            except (APIError, requests.RequestException) as e:
                last_error = e
                if isinstance(e, APIError) and e.status_code in (401, 404):
                    # Don't retry auth or not found errors
                    raise
                # For other errors, retry with backoff
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Request failed: {e}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                attempt += 1

        # All retries exhausted
        if last_error:
            logger.error(f"Request failed after {self.max_retries} attempts: {last_error}")
            raise last_error

        raise APIError(message="Request failed: Unknown error")

    def get_budgets(self) -> List[Budget]:
        """
        Get all available budgets.

        Returns:
            List of Budget objects

        Raises:
            APIError: If request fails
        """
        logger.info("Fetching budgets")
        data = self._make_request("GET", "/budgets")
        
        budgets = []
        for budget_data in data.get("data", {}).get("budgets", []):
            budget = Budget(
                id=budget_data["id"],
                name=budget_data["name"],
                currency_format=budget_data.get("currency_format", {}),
                date_format=budget_data.get("date_format", {}),
                last_modified_on=budget_data.get("last_modified_on"),
                first_month=budget_data.get("first_month"),
                last_month=budget_data.get("last_month"),
            )
            budgets.append(budget)

        logger.info(f"Retrieved {len(budgets)} budget(s)")
        return budgets

    def get_accounts(self, budget_id: str) -> List[Account]:
        """
        Get accounts for a specific budget.

        Args:
            budget_id: Budget ID

        Returns:
            List of Account objects

        Raises:
            APIError: If request fails
        """
        logger.info(f"Fetching accounts for budget {budget_id}")
        data = self._make_request("GET", f"/budgets/{budget_id}/accounts")

        accounts = []
        for account_data in data.get("data", {}).get("accounts", []):
            account = Account(
                id=account_data["id"],
                name=account_data["name"],
                type=account_data.get("type", ""),
                on_budget=account_data.get("on_budget", True),
                closed=account_data.get("closed", False),
                balance=account_data.get("balance", 0),
                cleared_balance=account_data.get("cleared_balance", 0),
                uncleared_balance=account_data.get("uncleared_balance", 0),
            )
            accounts.append(account)

        logger.info(f"Retrieved {len(accounts)} account(s)")
        return accounts

    def create_transactions(
        self,
        budget_id: str,
        transactions: List[Transaction],
    ) -> Dict[str, Any]:
        """
        Create multiple transactions in YNAB.

        Args:
            budget_id: Budget ID
            transactions: List of Transaction objects

        Returns:
            API response data

        Raises:
            ValueError: If no transactions provided
            APIError: If request fails
        """
        if not transactions:
            raise ValueError("At least one transaction is required")

        # Validate all transactions
        for tx in transactions:
            tx.validate()

        if len(transactions) > 100:
            logger.warning(
                f"Creating {len(transactions)} transactions. "
                "YNAB recommends max 100 per request."
            )

        logger.info(
            f"Creating {len(transactions)} transaction(s) for budget {budget_id}"
        )

        payload = {"transactions": [tx.to_dict() for tx in transactions]}

        data = self._make_request(
            "POST",
            f"/budgets/{budget_id}/transactions",
            json=payload,
        )

        result = data.get("data", {})
        created_count = len(result.get("transactions", []))
        logger.info(f"Successfully created {created_count} transaction(s)")

        return result

    def close(self) -> None:
        """Close the session."""
        if self.session:
            self.session.close()
            logger.debug("Session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
