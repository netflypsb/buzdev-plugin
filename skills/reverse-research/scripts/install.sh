#!/usr/bin/env bash
# Install the `reverse` social-media research CLI for the reverse-research skill.
# Target: Nous Portal hosted Hermes agent (Python 3.13, PEP 668 — use uv/venv, no system pip).
# Installs under /opt/data (the only persistent path), idempotent, subprocess-only (no daemons).
set -euo pipefail

DEST="/opt/data/reverse"
REPO="https://github.com/ifccod/social-media-research-cli.git"
VENV="$DEST/.venv"

if [ -x "$VENV/bin/reverse" ]; then
  echo "reverse already installed at $VENV — verifying"
  "$VENV/bin/reverse" list --json >/dev/null 2>&1 && { echo "OK: install verified"; exit 0; } || {
    echo "existing install broken — reinstalling" >&2
    rm -rf "$VENV"
  }
fi

mkdir -p "$DEST"

# Clone or update source
if [ -d "$DEST/src/.git" ]; then
  git -C "$DEST/src" pull --ff-only >/dev/null 2>&1 || true
else
  git clone --depth 1 "$REPO" "$DEST/src"
fi

# venv (PEP 668 safe). Try uv first (fast), fall back to stdlib venv+pip.
if command -v uv >/dev/null 2>&1; then
  uv venv "$VENV" --python python3 >/dev/null
  uv pip install --python "$VENV/bin/python" -e "$DEST/src" >/dev/null
else
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -e "$DEST/src"
fi

# Smoke test
"$VENV/bin/reverse" list --json > "$DEST/catalog.json"
PLAT=$(python3 -c "import json;print(len(json.load(open('$DEST/catalog.json'))))" 2>/dev/null || echo '?')
echo "OK: reverse installed. Platforms in catalog: $PLAT"
echo "Entry point: $VENV/bin/reverse"