#!/usr/bin/env bash
# xerant skill — remote one-line installer.
#
#   curl -fsSL https://xerant.cloud/install | sh
#
# or (no vanity URL):
#
#   curl -fsSL https://raw.githubusercontent.com/sanchaymittal/buildathon/main/.agents/skills/xerant/install-remote.sh | bash
#
# What it does (in order):
#   1. Verifies curl, tar, node >= 20 are available.
#   2. Fetches the buildathon repo tarball at $XERANT_REF (default: main).
#   3. Extracts just `.agents/skills/xerant/` into $XERANT_TARGET (default:
#      ./.agents/skills/xerant/ in the cwd where the user ran the curl).
#   4. Runs the extracted install.sh, which merges the MCP registration
#      into ./opencode.json and self-tests the MCP binary.
#
# Env overrides:
#   XERANT_REPO     owner/repo to pull from       (default sanchaymittal/buildathon)
#   XERANT_REF      branch, tag, or commit SHA    (default main)
#   XERANT_TARGET   destination skill directory   (default .agents/skills/xerant)
#   XERANT_FORCE    if "1", overwrite existing    (default off)
#
# This script writes no secrets and requires no network beyond GitHub.

set -u -o pipefail

XERANT_REPO="${XERANT_REPO:-sanchaymittal/buildathon}"
XERANT_REF="${XERANT_REF:-main}"
XERANT_TARGET="${XERANT_TARGET:-.agents/skills/xerant}"
XERANT_FORCE="${XERANT_FORCE:-0}"

c_info='\033[1;36m'; c_warn='\033[1;33m'; c_err='\033[1;31m'; c_ok='\033[1;32m'; c_off='\033[0m'
say()  { printf "${c_info}[xerant]${c_off} %s\n" "$*"; }
warn() { printf "${c_warn}[xerant]${c_off} %s\n" "$*" >&2; }
die()  { printf "${c_err}[xerant]${c_off} %s\n" "$*" >&2; exit 1; }

# ---------- 0. Sanity ----------------------------------------------------

command -v curl >/dev/null 2>&1 || die "curl not found on PATH."
command -v tar  >/dev/null 2>&1 || die "tar not found on PATH."
command -v node >/dev/null 2>&1 || die "node not found on PATH. Install Node.js >= 20 from https://nodejs.org"

node_version="$(node -v | sed 's/^v//')"
node_major="${node_version%%.*}"
if [ "${node_major:-0}" -lt 20 ]; then
  die "Node $node_version is too old. Need >= 20."
fi
say "Node $node_version OK"

# Absolute target so all later operations are path-stable.
ABS_TARGET="$(pwd)/$XERANT_TARGET"
case "$XERANT_TARGET" in /*) ABS_TARGET="$XERANT_TARGET" ;; esac

if [ -e "$ABS_TARGET" ] && [ "$XERANT_FORCE" != "1" ]; then
  if [ -d "$ABS_TARGET" ] && [ -z "$(ls -A "$ABS_TARGET" 2>/dev/null)" ]; then
    : # empty dir, fine to use
  else
    die "Destination $ABS_TARGET already exists. Set XERANT_FORCE=1 to overwrite."
  fi
fi

mkdir -p "$ABS_TARGET" || die "Cannot create $ABS_TARGET"

# ---------- 1. Download ---------------------------------------------------

TARBALL_URL="https://github.com/${XERANT_REPO}/tarball/${XERANT_REF}"
say "Fetching ${XERANT_REPO}@${XERANT_REF} tarball"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT INT TERM

# GitHub redirects tarball requests to codeload.github.com; -L follows.
curl -fsSL "$TARBALL_URL" -o "$tmpdir/repo.tgz" || die "Download failed: $TARBALL_URL"

# Extract only the skill subtree. GitHub tarballs contain a single top-level
# dir like `owner-repo-<sha7>/`; we use a glob to match it.
tar -xzf "$tmpdir/repo.tgz" -C "$tmpdir" --strip-components=1 \
    "*/.agents/skills/xerant" 2>/dev/null \
  || die "Extract failed. The repo may not contain .agents/skills/xerant at ${XERANT_REF}."

src="$tmpdir/.agents/skills/xerant"
if [ ! -d "$src" ]; then
  # Fallback for tar implementations that don't honour the glob — list and copy manually.
  tar -xzf "$tmpdir/repo.tgz" -C "$tmpdir" 2>/dev/null || die "Extract fallback failed."
  src="$(find "$tmpdir" -type d -path '*/.agents/skills/xerant' -print -quit)"
  [ -n "$src" ] && [ -d "$src" ] || die "Could not locate .agents/skills/xerant in the tarball."
fi

# Copy into target, preserving modes + setting +x on scripts.
cp -R "$src"/. "$ABS_TARGET"/ || die "Copy to $ABS_TARGET failed."
find "$ABS_TARGET" -type f -name '*.sh' -exec chmod +x {} +
find "$ABS_TARGET/bin" -type f -exec chmod +x {} + 2>/dev/null || true

say "Installed skill tree to $ABS_TARGET"

# ---------- 2. Run the local installer -----------------------------------

if [ ! -x "$ABS_TARGET/install.sh" ]; then
  die "Local install.sh missing or not executable inside $ABS_TARGET"
fi

# Run from the caller's cwd so opencode.json is written there, not in tmp.
say "Running local installer"
bash "$ABS_TARGET/install.sh" || die "Local installer failed"

# ---------- 3. Done -------------------------------------------------------

printf "\n${c_ok}[xerant]${c_off} Remote install complete.\n"
printf "           skill dir:   %s\n" "$ABS_TARGET"
printf "           opencode:    %s/opencode.json\n\n" "$(pwd)"
printf "Next: restart OpenCode and run ${c_info}/xerant --prod${c_off}\n"
