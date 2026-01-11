"""
Command-line interface for YNAB CSV Parser.

Unified CLI with subcommands for all operations.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ynab_parser.core.logging_config import setup_logging
from ynab_parser import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="ynab-parser",
        description="YNAB CSV Parser - Transaction processing and YNAB API integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup YNAB integration
  ynab-parser setup

  # Process bank CSVs
  ynab-parser process

  # Upload to YNAB (dry-run first)
  ynab-parser upload --dry-run
  ynab-parser upload

  # Full workflow
  ynab-parser setup && ynab-parser process && ynab-parser upload

For more information on each command, use:
  ynab-parser <command> --help
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command
    setup_parser = subparsers.add_parser(
        "setup",
        help="Interactive setup wizard for YNAB integration",
    )
    setup_parser.set_defaults(func=handle_setup)

    # Process command
    process_parser = subparsers.add_parser(
        "process",
        help="Parse bank CSVs and normalize transactions",
    )
    process_parser.add_argument(
        "--data-dir",
        default="data",
        help="Input data directory (default: data)",
    )
    process_parser.add_argument(
        "--output-dir",
        default="results",
        help="Output directory (default: results)",
    )
    process_parser.set_defaults(func=handle_process)

    # Upload command
    upload_parser = subparsers.add_parser(
        "upload",
        help="Upload transactions to YNAB",
    )
    upload_parser.add_argument(
        "--config",
        default=".env",
        help="Configuration file (default: .env)",
    )
    upload_parser.add_argument(
        "--budget-id",
        help="YNAB budget ID (overrides config)",
    )
    upload_parser.add_argument(
        "--results-dir",
        default="results",
        help="Results directory (default: results)",
    )
    upload_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without posting to YNAB",
    )
    upload_parser.set_defaults(func=handle_upload)

    return parser


def handle_setup(args) -> int:
    """Handle setup command."""
    from ynab_parser.setup import setup_interactive

    try:
        if setup_interactive():
            return 0
        return 1
    except Exception as e:
        print(f"Setup failed: {e}", file=sys.stderr)
        return 1


def handle_process(args) -> int:
    """Handle process command."""
    from ynab_parser.process import process_transactions

    try:
        return process_transactions(
            data_dir=args.data_dir,
            output_dir=args.output_dir,
        )
    except Exception as e:
        print(f"Processing failed: {e}", file=sys.stderr)
        return 1


def handle_upload(args) -> int:
    """Handle upload command."""
    from ynab_parser.upload import main

    try:
        argv = [
            "--config", args.config,
            "--results-dir", args.results_dir,
        ]
        if args.budget_id:
            argv.extend(["--budget-id", args.budget_id])
        if args.dry_run:
            argv.append("--dry-run")
        
        return main(argv)
    except Exception as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        return 1


def main(argv: Optional[list] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Setup logging
    setup_logging(
        "ynab_parser",
        level=10 if args.verbose else 20,  # DEBUG=10, INFO=20
    )

    # No command provided
    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    # Execute command
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
