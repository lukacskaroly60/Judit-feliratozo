#!/usr/bin/env bash
# Indítás macOS-en / Linuxon
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Első indítás: a program telepítése, ez pár percig tart..."
  python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install -r requirements.txt || exit 1
fi
exec .venv/bin/python -m app
