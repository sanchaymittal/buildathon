#!/usr/bin/env bash
# scan-secrets.sh — scan Dockerfile and build context for hard-coded secrets.
#
# Usage: scan-secrets.sh [project_root]
# Exits:
#   0  — no findings
#   2  — findings (printed to stdout)
#   3  — precondition error

set -u -o pipefail

PROJECT_ROOT="${1:-$(pwd)}"
cd "$PROJECT_ROOT" || { echo "cannot cd into $PROJECT_ROOT"; exit 3; }

if [ ! -f Dockerfile ]; then
  echo "scan-secrets: Dockerfile missing at $PROJECT_ROOT"
  exit 3
fi

# Prefer ripgrep; fall back to grep -E.
if command -v rg >/dev/null 2>&1; then
  SEARCH=(rg --no-heading --color=never --line-number --hidden)
  # rg respects .gitignore + .dockerignore-style patterns via -g, we filter below.
else
  SEARCH=(grep -RInE --color=never)
fi

# Patterns: high-confidence secret shapes + assignment heuristics.
PATTERNS=(
  'AKIA[0-9A-Z]{16}'                                    # AWS access key id
  'ASIA[0-9A-Z]{16}'                                    # AWS temporary key id
  'aws(.{0,20})?(secret|access).{0,20}[=:][[:space:]]*["'"'"']?[A-Za-z0-9/+=]{40}' # AWS secret
  'ghp_[A-Za-z0-9]{36}'                                 # GitHub PAT
  'github_pat_[A-Za-z0-9_]{82}'                         # GitHub fine-grained PAT
  'gho_[A-Za-z0-9]{36}'                                 # GitHub OAuth
  'xox[baprs]-[A-Za-z0-9-]{10,}'                        # Slack token
  'sk-[A-Za-z0-9]{20,}'                                 # OpenAI-style
  'AIza[0-9A-Za-z_-]{35}'                               # Google API
  '-----BEGIN (RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----'  # private keys
  '(api[_-]?key|secret|passwd|password|token)[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'$\{]{8,}["'"'"']' # assignment with literal
)

# Files to scan: Dockerfile + anything not excluded by .dockerignore.
# We build an include list from the build context if .dockerignore exists.
TMPLIST="$(mktemp)"
trap 'rm -f "$TMPLIST"' EXIT

{
  echo Dockerfile
  # List files git knows about (covers .gitignore), then filter via .dockerignore.
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git ls-files --cached --others --exclude-standard
  else
    find . -type f \
           -not -path './.git/*' \
           -not -path './node_modules/*' \
           -not -path './.next/*' \
           -not -path './dist/*' \
           -not -path './build/*' \
      | sed 's|^\./||'
  fi
} | sort -u > "$TMPLIST"

# Portable xargs: pipe stdin (macOS BSD xargs lacks -a).
FOUND=0
for pat in "${PATTERNS[@]}"; do
  # shellcheck disable=SC2086
  hits=$(xargs "${SEARCH[@]}" -- "$pat" < "$TMPLIST" 2>/dev/null || true)
  if [ -n "$hits" ]; then
    # Filter obvious placeholders (xxx, example, changeme, your-*, EXAMPLE in uppercase).
    filtered=$(printf '%s\n' "$hits" | grep -viE '(xxx+|example|changeme|your[-_]?(key|token|secret)|<[a-z_]+>|\$\{?[A-Z_]+\}?|placeholder)')
    if [ -n "$filtered" ]; then
      FOUND=1
      echo "── pattern: $pat"
      printf '%s\n' "$filtered"
      echo
    fi
  fi
done

if [ "$FOUND" -eq 1 ]; then
  echo "scan-secrets: potential secrets detected above. Remove or move to build-time secrets (BuildKit --mount=type=secret) or runtime env."
  exit 2
fi

echo "scan-secrets: clean."
exit 0
