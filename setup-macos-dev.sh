#!/bin/zsh
set -e
cd "${0:A:h}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This setup script must be run on macOS."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install Python 3 first, then run this script again."
  exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium

echo "Development environment ready."
echo "GUI:      ./run-macos.sh"
echo "Menu bar: ./run-menubar-macos.sh"
