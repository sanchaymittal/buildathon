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

# ---------- 5. compose-specific gates (if compose file present) -----------
COMPOSE_FILE=""
for candidate in compose.yml compose.yaml docker-compose.yml docker-compose.yaml; do
  if [ -f "$candidate" ]; then COMPOSE_FILE="$candidate"; break; fi
done

if [ -n "$COMPOSE_FILE" ]; then
  section "compose: $COMPOSE_FILE"

  # 5a. Sensitive bind-mounts
  # Grep for `host_path:container_path` patterns under volumes: that match
  # known-dangerous hosts. False positives are OK here — we'd rather warn.
  sensitive=$(grep -nE '^[[:space:]]*-[[:space:]]*["'"'"']?(/var/run/docker\.sock|/root|/etc|/var/lib|\$HOME/\.(ssh|aws|docker|gnupg)|~/\.(ssh|aws|docker|gnupg))' "$COMPOSE_FILE" 2>/dev/null || true)
  if [ -n "$sensitive" ]; then
    echo "FAIL: sensitive host path bind-mount detected in $COMPOSE_FILE:"
    printf '%s\n' "$sensitive"
    echo "  If you really need this, re-run with --force. Otherwise move the data into a named volume."
    FAIL=1
  else
    echo "OK: no sensitive bind-mounts"
  fi

  # 5b. privileged: true
  if grep -nE '^[[:space:]]*privileged:[[:space:]]*true' "$COMPOSE_FILE" >/dev/null 2>&1; then
    echo "FAIL: service marked 'privileged: true' in $COMPOSE_FILE. Drop caps explicitly instead."
    grep -nE '^[[:space:]]*privileged:[[:space:]]*true' "$COMPOSE_FILE"
    FAIL=1
  else
    echo "OK: no privileged services"
  fi

  # 5c. Low-port exposure
  # Matches `ports: - "0.0.0.0:22:22"`, `- "22:22"`, `- 80:80`. Extracts the
  # host port (the numeric group immediately before the second colon) and
  # flags it if <= 1024.
  low_ports=$(awk '
    /^[[:space:]]*-[[:space:]]*["'"'"']?([0-9.]+:)?[0-9]+:[0-9]+["'"'"']?[[:space:]]*$/ {
      line = $0
      # Strip leading list marker, quotes, whitespace.
      sub(/^[[:space:]]*-[[:space:]]*["'"'"']?/, "", line)
      sub(/["'"'"']?[[:space:]]*$/, "", line)
      n = split(line, parts, ":")
      # Host port is the second-to-last numeric field when an IP is present,
      # otherwise the first field.
      host_port = (n == 3) ? parts[2] : parts[1]
      if (host_port ~ /^[0-9]+$/ && host_port+0 > 0 && host_port+0 <= 1024) {
        printf "%d:\t%s\n", FNR, $0
      }
    }
  ' "$COMPOSE_FILE" 2>/dev/null || true)
  if [ -n "$low_ports" ]; then
    echo "WARN: port binding <= 1024 (advisory, not blocking):"
    printf '%s\n' "$low_ports"
  fi

  # 5d. env_file that isn't .env.example
  bad_env_files=$(grep -nE '^[[:space:]]*env_file:[[:space:]]*["'"'"']?[^"#]*\.env(\b|[^.])' "$COMPOSE_FILE" 2>/dev/null \
    | grep -vE '\.env\.example' || true)
  if [ -n "$bad_env_files" ]; then
    echo "WARN: env_file references a .env variant that is typically git-ignored:"
    printf '%s\n' "$bad_env_files"
    echo "  Ensure the file exists on the deploy host and isn't accidentally committed."
  fi
else
  section "compose"
  echo "SKIP: no compose file found (COMPOSE flow not in play)"
fi

# ---------- result --------------------------------------------------------
echo
if [ "$FAIL" -eq 0 ]; then
  echo "check-dockerfile: all gates passed."
  exit 0
fi
echo "check-dockerfile: one or more gates failed. Do not deploy."
exit 1
