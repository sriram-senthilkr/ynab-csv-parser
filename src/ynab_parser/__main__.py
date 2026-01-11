"""
Allow module to be executed as: python -m ynab_parser
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ynab_parser.cli import main

if __name__ == "__main__":
    sys.exit(main())
