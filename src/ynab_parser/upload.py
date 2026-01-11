#!/usr/bin/env python3
"""
YNAB transaction uploader.

Converts parsed transaction CSVs to YNAB format and posts to YNAB API.

Usage:
  python3 -m ynab_parser.cli upload [--config .env] [--budget-id ID] [--dry-run]
"""

import sys
import argparse
from typing import List, Optional
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ynab_parser.core.config import ConfigManager
from ynab_parser.core.api import YNABClient
from ynab_parser.core.logging_config import setup_logging
from ynab_parser.core.exceptions import ConfigurationError, APIError
from ynab_parser.uploader import TransactionUploader

logger = setup_logging("ynab_parser.upload")


def print_summary(all_stats: dict) -> int:
    """Print upload summary and return exit code."""
    logger.info("\n" + "="*60)
    logger.info("UPLOAD SUMMARY")
    logger.info("="*60)

    total_uploaded = 0
    total_errors = 0
    file_count = 0

    for file_name, stats in all_stats.items():
        file_count += 1
        if "error" in stats:
            logger.error(f"✗ {file_name}: {stats['error']}")
            total_errors += 1
        else:
            uploaded = stats.get("uploaded", 0)
            total = stats.get("total", 0)
            status = "✓" if uploaded == total else "⚠"
            logger.info(f"{status} {file_name}: {uploaded}/{total} uploaded")
            total_uploaded += uploaded

    logger.info("="*60)
    logger.info(f"Files processed: {file_count}")
    logger.info(f"Total uploaded: {total_uploaded}")

    return 0 if total_errors == 0 else 1


def _parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Upload parsed transactions to YNAB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m ynab_parser.upload --config .env --budget-id my_budget_id
  python3 -m ynab_parser.upload --dry-run
        """,
    )
    parser.add_argument(
        "--config",
        default=".env",
        help="Configuration file (default: .env)"
    )
    parser.add_argument(
        "--budget-id",
        help="YNAB budget ID (overrides .env)"
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Directory containing result CSVs (default: results)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview upload without posting to YNAB"
    )

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    args = _parse_args(argv or sys.argv[1:])

    logger.info("="*60)
    logger.info("YNAB TRANSACTION UPLOADER")
    logger.info("="*60)

    try:
        # Load configuration
        logger.info("\nLoading configuration...")
        config = ConfigManager(args.config)

        api_token = config.get_api_token()
        budget_id = config.get_budget_id(args.budget_id)
        account_mapping = config.get_account_mapping()

        if not account_mapping:
            logger.error("No account mappings configured. Please check .env file.")
            return 1

        logger.info(f"Budget ID: {budget_id}")
        logger.info(f"Mapped accounts: {len(account_mapping)}")

        # Create API client and uploader
        logger.info("\nConnecting to YNAB API...")
        with YNABClient(api_token) as client:
            uploader = TransactionUploader(
                client=client,
                budget_id=budget_id,
                dry_run=args.dry_run,
            )

            # Upload all transactions
            logger.info(f"\nProcessing CSV files from {args.results_dir}/...")
            all_stats = uploader.upload_all(args.results_dir, account_mapping)

            # Print summary
            return print_summary(all_stats)

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except APIError as e:
        logger.error(f"API error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
