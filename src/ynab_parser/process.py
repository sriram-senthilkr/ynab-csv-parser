#!/usr/bin/env python3
"""
Main entry point for YNAB transaction processing pipeline.

Parses all bank transaction CSVs and saves normalized results to results/ directory.

Usage:
  python3 -m ynab_parser.cli process [--data-dir DIR] [--output-dir DIR]
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ynab_parser.core.logging_config import get_logger, setup_logging
from ynab_parser.processor import TransactionProcessor

logger = get_logger("process")


def process_transactions(
    data_dir: str = "data",
    output_dir: str = "results",
) -> int:
    """
    Process all bank transaction CSVs.

    Args:
        data_dir: Data directory containing incoming CSVs
        output_dir: Output directory for results

    Returns:
        Exit code (0=success, 1=failure)
    """
    setup_logging("ynab_parser.process")
    logger.info("="*60)
    logger.info("TRANSACTION PROCESSING PIPELINE")
    logger.info("="*60)

    try:
        # Parse all transactions
        logger.info(f"\nScanning {data_dir}/incoming/ for CSV files...")
        grouped = TransactionProcessor.parse_all_transactions(data_dir)

        if not grouped:
            logger.error("No transactions found to process")
            return 1

        total_transactions = sum(len(txs) for txs in grouped.values())
        logger.info(f"\nTotal transactions parsed: {total_transactions}")

        # Save results
        logger.info(f"\nSaving results to {output_dir}/...")
        saved_files = TransactionProcessor.save_transactions(grouped, output_dir)

        logger.info("\n" + "="*60)
        logger.info("✓ PROCESSING COMPLETE")
        logger.info("="*60)
        logger.info(f"Results saved: {len(saved_files)} file(s)")
        for file in saved_files:
            logger.info(f"  - {Path(file).name}")

        return 0

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(process_transactions())
