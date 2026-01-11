"""
Configuration management for YNAB Parser.

Handles:
- Environment variable loading (.env files)
- Configuration validation
- Defaults and fallbacks
- Account mapping
"""

import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv

from .exceptions import ConfigurationError
from .logging_config import get_logger

logger = get_logger("config")


class ConfigManager:
    """Manage configuration from environment and .env files."""

    # Default values
    DEFAULT_DATA_DIR = "data"
    DEFAULT_RESULTS_DIR = "results"
    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_RETRIES = 3

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            env_file: Path to .env file (default: .env)

        Raises:
            ConfigurationError: If configuration is invalid
        """
        self.env_file = env_file or ".env"
        self._load_env()

    def _load_env(self) -> None:
        """Load environment variables from .env file."""
        if Path(self.env_file).exists():
            load_dotenv(self.env_file)
            logger.info(f"Loaded configuration from {self.env_file}")
        else:
            logger.warning(
                f"Configuration file not found: {self.env_file}. "
                "Using environment variables and defaults."
            )

    @staticmethod
    def get_api_token() -> str:
        """
        Get YNAB API token.

        Returns:
            API token

        Raises:
            ConfigurationError: If token not configured
        """
        token = os.getenv("YNAB_API_TOKEN", "").strip()
        if not token or token == "your_api_token_here":
            raise ConfigurationError(
                message="YNAB_API_TOKEN not configured",
                error_code="MISSING_API_TOKEN",
                details={
                    "solution": (
                        "Set YNAB_API_TOKEN in .env file or "
                        "YNAB_API_TOKEN environment variable"
                    )
                },
            )
        return token

    @staticmethod
    def get_budget_id(override: Optional[str] = None) -> str:
        """
        Get YNAB budget ID.

        Args:
            override: Override budget ID from command line

        Returns:
            Budget ID

        Raises:
            ConfigurationError: If budget ID not configured
        """
        if override:
            return override

        budget_id = os.getenv("YNAB_BUDGET_ID", "").strip()
        if not budget_id:
            raise ConfigurationError(
                message="YNAB_BUDGET_ID not configured",
                error_code="MISSING_BUDGET_ID",
                details={
                    "solution": (
                        "Set YNAB_BUDGET_ID in .env file, "
                        "YNAB_BUDGET_ID environment variable, "
                        "or use --budget-id CLI argument"
                    )
                },
            )
        return budget_id

    @staticmethod
    def get_account_mapping() -> Dict[str, str]:
        """
        Get mapping of CSV account names to YNAB account IDs.

        Returns:
            Dictionary mapping account names to account IDs

        Note:
            Returns empty dict if no mappings configured.
            Log a warning when accounts are missing.
        """
        mapping = {}

        # Standard account name mappings
        mapping_vars = {
            "OCBC_DEFAULT": "ocbc_default",
            "POSB_EVERYDAY_USE": "posb_everyday-use",
            "POSB_MY_SAVINGS": "posb_my-savings",
        }

        found_count = 0
        for env_var, account_name in mapping_vars.items():
            account_id = os.getenv(env_var, "").strip()
            if account_id and account_id != "":
                mapping[account_name] = account_id
                found_count += 1

        if found_count == 0:
            logger.warning("No account mappings configured in .env file")

        return mapping

    @staticmethod
    def get_data_dir(override: Optional[str] = None) -> str:
        """Get data directory path."""
        if override:
            return override
        return os.getenv("DATA_DIR", ConfigManager.DEFAULT_DATA_DIR)

    @staticmethod
    def get_results_dir(override: Optional[str] = None) -> str:
        """Get results directory path."""
        if override:
            return override
        return os.getenv("RESULTS_DIR", ConfigManager.DEFAULT_RESULTS_DIR)

    @staticmethod
    def get_api_timeout() -> int:
        """Get API request timeout in seconds."""
        try:
            return int(os.getenv("YNAB_API_TIMEOUT", ConfigManager.DEFAULT_TIMEOUT))
        except ValueError:
            logger.warning(
                f"Invalid YNAB_API_TIMEOUT value. Using default: {ConfigManager.DEFAULT_TIMEOUT}"
            )
            return ConfigManager.DEFAULT_TIMEOUT

    @staticmethod
    def get_max_retries() -> int:
        """Get maximum number of API retries."""
        try:
            return int(os.getenv("YNAB_MAX_RETRIES", ConfigManager.DEFAULT_MAX_RETRIES))
        except ValueError:
            logger.warning(
                f"Invalid YNAB_MAX_RETRIES value. Using default: {ConfigManager.DEFAULT_MAX_RETRIES}"
            )
            return ConfigManager.DEFAULT_MAX_RETRIES

    @staticmethod
    def is_dry_run() -> bool:
        """Check if running in dry-run mode."""
        return os.getenv("DRY_RUN", "false").lower() in ("true", "1", "yes")
