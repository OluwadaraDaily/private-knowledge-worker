#!/usr/bin/env sh

set -eu

ROOT_DIR=$(git rev-parse --show-toplevel)
cd "$ROOT_DIR"

PATTERN='-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(sk|pk|rk)-[A-Za-z0-9_-]{20,}\b|\bgh[pousr]_[A-Za-z0-9_]{20,}\b|\bAIza[A-Za-z0-9_-]{30,}\b|\bxox[baprs]-[A-Za-z0-9-]{20,}\b|\b(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*["'"'][^"'"']+["'"']'

MATCHES=$(rg -l --hidden \
	--glob '!.git/**' \
	--glob '!.env' \
	--glob '!.env.*' \
	--glob '!node_modules/**' \
	--glob '!frontend/dist/**' \
	--glob '!backend/.venv/**' \
	-e "$PATTERN" . || true)

if [ -n "$MATCHES" ]; then
	echo 'Potential secret detected in:'
	echo "$MATCHES"
	exit 1
fi
