#!/usr/bin/env bash
# check-dockerfile.sh — run all security gates against ./Dockerfile.
#
# Usage: check-dockerfile.sh [project_root]
# Exits:
#   0  — all checks pass (hadolint may emit warnings but no errors)
#   1  — one or more hard findings; do not deploy
#   3  — precondition error (missing Dockerfile, etc.)

set -u -o pipefail

PROJECT_ROOT="${1:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_ROOT" || { echo "cannot cd into $PROJECT_ROOT"; exit 3; }

if [ ! -f Dockerfile ]; then
  echo "check-dockerfile: Dockerfile missing at $PROJECT_ROOT"
  exit 3
fi

FAIL=0
section() { printf '\n== %s ==\n' "$1"; }

# ---------- 1. .dockerignore coverage -------------------------------------
section ".dockerignore coverage"
if [ ! -f .dockerignore ]; then
  echo "FAIL: .dockerignore missing. Copy templates/.dockerignore from the skill."
  FAIL=1
else
  required=(".env" ".git" "node_modules" "*.pem" "*.key" "id_rsa")
  missing=()
  for entry in "${required[@]}"; do
    if ! grep -qxF "$entry" .dockerignore 2>/dev/null \
       && ! grep -qE "^[[:space:]]*${entry//./\\.}[[:space:]]*$" .dockerignore 2>/dev/null; then
      missing+=("$entry")
    fi
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    echo "FAIL: .dockerignore missing required entries: ${missing[*]}"
    FAIL=1
  else
    echo "OK"
  fi
fi

# ---------- 2. ARG → ENV leaks --------------------------------------------
section "ARG → ENV leak check"
# Collect ARG names, then look for ENV X=$X or ENV X=${X} using those names.
args=$(grep -E '^[[:space:]]*ARG[[:space:]]+' Dockerfile | awk '{print $2}' | sed 's/=.*//')
leaks=""
if [ -n "$args" ]; then
  while IFS= read -r name; do
    [ -z "$name" ] && continue
    if grep -qE "^[[:space:]]*ENV[[:space:]]+${name}[[:space:]]*=[[:space:]]*\\\$\{?${name}\}?" Dockerfile; then
      leaks="${leaks}${name}\n"
    fi
  done <<< "$args"
fi
if [ -n "$leaks" ]; then
  echo "FAIL: build-time ARG values promoted to runtime ENV (leak risk):"
  printf '  - %b' "$leaks"
  echo "  Use BuildKit secrets (--mount=type=secret) for sensitive values."
  FAIL=1
else
  echo "OK"
fi

# ---------- 3. Secret scan ------------------------------------------------
section "Secret / credential scan"
if bash "$SCRIPT_DIR/scan-secrets.sh" "$PROJECT_ROOT"; then
  :
else
  rc=$?
  if [ "$rc" -eq 2 ]; then
    FAIL=1
  else
    echo "FAIL: scan-secrets.sh errored (exit $rc)"
    FAIL=1
  fi
fi

# ---------- 4. hadolint (optional) ----------------------------------------
section "hadolint"
if command -v hadolint >/dev/null 2>&1; then
  if hadolint Dockerfile; then
    echo "OK"
  else
    echo "FAIL: hadolint reported errors above."
    FAIL=1
  fi
else
  echo "SKIP: hadolint not installed (brew install hadolint). Advisory only."
fi

# ---------- result --------------------------------------------------------
echo
if [ "$FAIL" -eq 0 ]; then
  echo "check-dockerfile: all gates passed."
  exit 0
fi
echo "check-dockerfile: one or more gates failed. Do not deploy."
exit 1
