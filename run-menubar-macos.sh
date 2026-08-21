#!/bin/zsh
set -e
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  echo "Local development venv not found. Run ./setup-macos-dev.sh first."
  exit 1
fi
exec .venv/bin/python menubar.py
