#!/usr/bin/env bash
# deploy.sh — trigger a Xerant deployment.
#
# Usage: deploy.sh <environment> [--force]
#   environment: production | staging | preview | development
#
# Behaviour:
#   1. Validates XERANT_API_KEY is set (does not print it).
#   2. Prefers the `xerant` CLI if it is on PATH.
#   3. Otherwise emits a structured request the agent can route to the MCP
#      tool `xerant_deploy` when it becomes available.
#
# The API key is passed via environment variable only. Never via argv.

set -u -o pipefail

ENV_ARG="${1:-}"
FORCE="${2:-}"

case "$ENV_ARG" in
  production|staging|preview|development) ;;
  "")
    echo "deploy.sh: environment required (production|staging|preview|development)"
    exit 2
    ;;
  *)
    echo "deploy.sh: unknown environment '$ENV_ARG'"
    exit 2
    ;;
esac

if [ -z "${XERANT_API_KEY:-}" ]; then
  echo "deploy.sh: XERANT_API_KEY not set. export it in your shell and retry."
  echo "          I will not read it from a file or accept it as an argument."
  exit 3
fi

COMMIT="$(git rev-parse --short HEAD 2>/dev/null | head -n1)"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null | head -n1)"
# Treat empty output, bare "HEAD" (pre-initial-commit), or detached as unknown.
if [ -z "$COMMIT" ]; then COMMIT=unknown; fi
if [ -z "$BRANCH" ] || [ "$BRANCH" = "HEAD" ]; then BRANCH=unknown; fi

echo "deploy.sh: environment=$ENV_ARG commit=$COMMIT branch=$BRANCH force=${FORCE:-false}"

# Prefer the CLI. The MCP path is handled by the agent, not this script — when
# the `xerant_deploy` MCP tool is registered, the SKILL.md workflow instructs
# the agent to call it directly instead of this script.
if command -v xerant >/dev/null 2>&1; then
  # Key stays in env; never shown in argv.
  exec xerant deploy \
    --env "$ENV_ARG" \
    --commit "$COMMIT" \
    ${FORCE:+--force}
fi

# No CLI and no MCP — emit a machine-readable request for the agent/operator.
cat <<EOF
deploy.sh: neither \`xerant\` CLI nor the \`xerant_deploy\` MCP tool is
available in this environment.

Pending deploy request:
{
  "tool": "xerant_deploy",
  "arguments": {
    "environment": "$ENV_ARG",
    "commit": "$COMMIT",
    "branch": "$BRANCH",
    "force": ${FORCE:+true}${FORCE:-false}
  }
}

To proceed:
  1. Install the CLI:  \`curl -fsSL https://xerant.internal/install.sh | sh\`
     or register the Xerant MCP server in opencode.json.
  2. Re-run the skill.
EOF
exit 4
