#!/usr/bin/env bash
# Simple helper to create and activate a Python virtual environment and install deps.
# Usage: `./scripts/setup_venv.sh` then `source .venv/bin/activate`

set -euo pipefail

VENV_DIR=".venv"

echo "Creating virtual environment in ${VENV_DIR} (if missing)..."
python3 -m venv "${VENV_DIR}"

echo "Upgrading pip and installing requirements..."
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r requirements.txt

echo "Done. Activate with: source ${VENV_DIR}/bin/activate"
