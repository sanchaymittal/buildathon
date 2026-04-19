#!/usr/bin/env bash
# xerant skill installer.
#
# Drops the skill into any project. Run from the target project root:
#
#   # when the skill is already at .agents/skills/xerant/
#   bash .agents/skills/xerant/install.sh
#
#   # or pipe from anywhere
#   curl -fsSL https://raw.githubusercontent.com/sanchaymittal/buildathon/main/.agents/skills/xerant/install.sh | bash
#
# What it does:
#   1. Verifies the bundled MCP server binary is present and executable.
#   2. Merges the `xerant` MCP server block into the project's opencode.json
#      (creates the file if missing, preserves existing keys).
#   3. Prints next-step instructions.
#
# It does NOT:
#   - Install or upgrade Node.js (required: Node >= 20).
#   - Start the internal server (see QUICKSTART.md or internal-server/README.md).
#   - Write any secrets. XERANT_API_KEY / XERANT_API_URL stay in the user's shell.

set -u -o pipefail

say()  { printf '\033[1;36m[xerant]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[xerant]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[xerant]\033[0m %s\n' "$*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_PATH="$SCRIPT_DIR/bin/xerant-mcp.mjs"
PROJECT_ROOT="$(pwd)"
OPENCODE_JSON="$PROJECT_ROOT/opencode.json"

# ---------- 1. Validate bundled binary ------------------------------------

if [ ! -f "$BIN_PATH" ]; then
  die "Bundled MCP binary missing at $BIN_PATH. Run 'npm run bundle' in mcp-server/ first."
fi
if [ ! -x "$BIN_PATH" ]; then
  chmod +x "$BIN_PATH" || die "Cannot chmod +x $BIN_PATH"
fi
say "MCP binary: $BIN_PATH"

# ---------- 2. Validate Node --------------------------------------------

if ! command -v node >/dev/null 2>&1; then
  die "node is not on PATH. Install Node.js >= 20 (https://nodejs.org)."
fi
node_version="$(node -v | sed 's/^v//')"
node_major="${node_version%%.*}"
if [ "${node_major:-0}" -lt 20 ]; then
  die "Node $node_version is too old. Need >= 20."
fi
say "Node $node_version OK"

# ---------- 3. Compute command path --------------------------------------

# Use a path relative to the project root so the config is portable across
# machines that clone the project at different absolute paths.
# Try to express BIN_PATH relative to PROJECT_ROOT using python (always available on macOS/Linux).
if command -v python3 >/dev/null 2>&1; then
  REL_BIN_PATH="$(python3 -c "import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))" "$BIN_PATH" "$PROJECT_ROOT")"
elif command -v realpath >/dev/null 2>&1 && realpath --help 2>&1 | grep -q '\-\-relative-to'; then
  REL_BIN_PATH="$(realpath --relative-to="$PROJECT_ROOT" "$BIN_PATH")"
else
  REL_BIN_PATH="$BIN_PATH"
  warn "Could not compute relative path; using absolute path."
fi
MCP_CMD_PATH="./$REL_BIN_PATH"
say "MCP command: node $MCP_CMD_PATH"

# ---------- 4. Merge into opencode.json ----------------------------------

# One Node script handles both the create and the merge case cleanly, with
# identical formatting.
if [ -f "$OPENCODE_JSON" ]; then
  say "Merging xerant entry into existing $OPENCODE_JSON"
  cp "$OPENCODE_JSON" "$OPENCODE_JSON.bak.$(date +%s)" || die "backup failed"
else
  say "Creating $OPENCODE_JSON"
fi

node - "$OPENCODE_JSON" "$MCP_CMD_PATH" <<'NODE'
const fs = require('node:fs');
const [, , configPath, cmdPath] = process.argv;

let config = {};
if (fs.existsSync(configPath)) {
  const raw = fs.readFileSync(configPath, 'utf8');
  try {
    config = JSON.parse(raw);
  } catch (e) {
    console.error(`[xerant] opencode.json is not valid JSON: ${e.message}`);
    process.exit(1);
  }
  if (typeof config !== 'object' || config === null) config = {};
}

if (!config.$schema) config.$schema = 'https://opencode.ai/config.json';
if (typeof config.mcp !== 'object' || config.mcp === null) config.mcp = {};

config.mcp.xerant = {
  type: 'local',
  command: ['node', cmdPath],
  environment: {
    XERANT_API_URL: '{env:XERANT_API_URL}',
    XERANT_API_KEY: '{env:XERANT_API_KEY}',
  },
  enabled: true,
  timeout: 15000,
};

fs.writeFileSync(configPath, JSON.stringify(config, null, 2) + '\n');
console.log('[xerant] wrote mcp.xerant into', configPath);
NODE

# ---------- 5. Self-test -------------------------------------------------

say "Self-test: list tools via stdio"
# Pipe a minimal MCP handshake and exit successfully if tools/list returns.
selftest=$(
  printf '%s\n' \
    '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"xerant-install","version":"0"}}}' \
    '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
    '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
    | node "$BIN_PATH" 2>/dev/null \
    | node -e 'let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{for(const l of d.split("\n")){if(!l.trim())continue;try{const o=JSON.parse(l);if(o.id===2){console.log(o.result.tools.length);process.exit(0)}}catch{}}process.exit(1)})' \
    2>/dev/null
) || true
if [ -z "$selftest" ]; then
  die "Self-test failed: MCP binary did not return tools/list."
fi
say "Self-test OK: $selftest tools exposed"

# ---------- 6. Next steps ------------------------------------------------

cat <<EOF

$(printf '\033[1;32m[xerant]\033[0m') Install complete.

Next:
  1. Start the internal server (one of):
       cd /path/to/buildathon/internal-server && python -m src.cli serve --port 8000
       docker run -p 8000:8000 -v /var/run/docker.sock:/var/run/docker.sock xerant-internal-server
  2. Optionally export:
       export XERANT_API_URL=http://localhost:8000
       export XERANT_API_KEY=<your key, if auth is enabled>
  3. Restart OpenCode so it picks up the xerant MCP server.
  4. Invoke the skill:
       /xerant --prod
       xerant --path ./my-app

EOF
