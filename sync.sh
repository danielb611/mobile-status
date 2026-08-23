#!/bin/bash
# Regenerates status.json and pushes it to GitHub Pages if anything changed.
set -euo pipefail
cd "$(dirname "$0")"

/usr/bin/python3 generate-status.py

if ! git diff --quiet status.json; then
  git add status.json
  git commit -m "Status sync $(date -u +%Y-%m-%dT%H:%M:%SZ)" -q
  git push origin main -q
  echo "$(date): pushed update"
else
  echo "$(date): no change"
fi
