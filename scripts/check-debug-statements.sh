#!/usr/bin/env sh

set -eu

ROOT_DIR=$(git rev-parse --show-toplevel)
cd "$ROOT_DIR"

MATCHES=$( {
	rg -l -g '*.py' -e '\bprint\s*\(' backend || true
	rg -l -g '*.{js,jsx,ts,tsx}' -e 'console\.(log|debug|info|warn|error)\s*\(|\bdebugger\b' frontend || true
} | sort -u )

if [ -n "$MATCHES" ]; then
	echo 'Potential debug statement detected in:'
	echo "$MATCHES"
	exit 1
fi
