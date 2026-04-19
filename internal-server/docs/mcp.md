# MCP Integration (Open)

This service exposes a minimal, open MCP (Model Context Protocol) adapter for external agents.

## Base URL
`http://<host>:8000/mcp/`

## Tools
### List Tools
```bash
curl -s -X POST http://localhost:8000/mcp/tools/list
```

### Call Tool
```bash
curl -s -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "deploy_quick",
    "arguments": {
      "repository": "owner/repo",
      "user_id": "user-123"
    }
  }'
```

## Available Tools
- `deploy_quick`: Deploy a GitHub repo with a `user_id`.
- `deploy_status`: Fetch deployment details by `deploy_id` + `user_id`.
- `deploy_logs`: Fetch logs by `deploy_id` + `user_id`.
- `deploy_down`: Remove a deployment by `deploy_id` + `user_id`.

## Notes
- No auth is required. Run on trusted networks only.
- `user_id` is required for all MCP calls and is enforced for access checks.
