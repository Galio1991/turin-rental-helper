#!/usr/bin/env bash

set -euo pipefail

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Turin Rental Helper requires Python 3.10+")
print(f"Python {sys.version.split()[0]} OK")
PY

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
destination=${1:-"${HOME}/.claude/skills/turin-rental-helper"}

if [[ -e "$destination" ]]; then
    echo "Destination already exists: $destination" >&2
    echo "Move or remove it explicitly, then run this installer again." >&2
    exit 2
fi

mkdir -p "$(dirname -- "$destination")"
cp -R "$script_dir" "$destination"

echo "Installed to $destination"
echo "Run tests with: cd '$destination' && python3 -m unittest discover -s tests -v"
