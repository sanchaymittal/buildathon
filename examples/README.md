# DevOps MCP Examples

This folder contains examples for testing the MCP deployment tools against public repositories.

## Quick Test - 16 Popular Frameworks

Run the test to see deployment readiness:

```bash
cd internal-server
python examples/test_repos.py
```

Results are saved to `examples/repo_test_results.md`.

## Key Finding

These popular frameworks (Express, FastAPI, Django, etc.) are **libraries**, not deployable apps. Users deploy their **OWN apps built WITH** these frameworks.

| Framework | Language | Stars | Can Deploy via MCP |
|-----------|----------|------:|-------------------:|
| FastAPI | Python | 74,000 | YES |
| Flask | Python | 71,000 | Via user app |
| Django | Python | 87,000 | Via user app |
| Express | Node.js | 69,000 | Via user app |
| Fastify | Node.js | 36,000 | Via user app |
| NestJS | Node.js | 75,000 | YES |
| Next.js | Node.js | 139,000 | YES |
| Gin | Go | 88,000 | Via user app |
| Echo | Go | 32,000 | YES |
| Fiber | Go | 39,000 | YES |
| Actix | Rust | 24,000 | YES |
| Rails | Ruby | 58,000 | YES |
| Sinatra | Ruby | 31,000 | Via user app |
| Laravel | PHP | 76,000 | Via user app |
| Spring Boot | Java | 68,000 | YES |
| ASP.NET | C# | 19,000 | YES |

## MCP Tool Usage via API

The MCP tools are exposed via `/api/mcp/*` endpoints:

### 1. List Available Tools

```bash
curl -X POST http://localhost:8000/api/mcp/tools/list
```

### 2. Deploy a Repository

```bash
curl -X POST http://localhost:8000/api/mcp/tools/call \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "deploy_quick",
    "arguments": {
      "repository": "owner/repo-name",
      "branch": "main",
      "user_id": "user123"
    }
  }'
```

### 3. Check Deployment Status

```bash
curl -X POST http://localhost:8000/api/mcp/tools/call \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "deploy_status",
    "arguments": {
      "deploy_id": "abc123",
      "user_id": "user123"
    }
  }'
```

### 4. Get Logs

```bash
curl -X POST http://localhost:8000/api/mcp/tools/call \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "deploy_logs",
    "arguments": {
      "deploy_id": "abc123",
      "user_id": "user123",
      "tail": 50
    }
  }'
```

### 5. Remove Deployment

```bash
curl -X POST http://localhost:8000/api/mcp/tools/call \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "deploy_down",
    "arguments": {
      "deploy_id": "abc123",
      "user_id": "user123"
    }
  }'
```

## Example: Full Deployment Flow (Python)

```python
import requests

BASE = "http://localhost:8000"

# 1. Deploy
resp = requests.post(f"{BASE}/api/mcp/tools/call", json={
    "name": "deploy_quick",
    "arguments": {
        "repository": "owner/my-fastapi-app",
        "branch": "main",
        "user_id": "user123"
    }
})
deployment = resp.json()["result"]
print(f"Deployed: {deployment['url']}")

# 2. Wait and check status
import time
time.sleep(5)
resp = requests.post(f"{BASE}/api/mcp/tools/call", json={
    "name": "deploy_status",
    "arguments": {"deploy_id": deployment["id"], "user_id": "user123"}
})
print(f"Status: {resp.json()['result']['status']}")

# 3. Get logs
resp = requests.post(f"{BASE}/api/mcp/tools/call", json={
    "name": "deploy_logs",
    "arguments": {"deploy_id": deployment["id"], "user_id": "user123", "tail": 20}
})
print(f"Logs: {resp.json()['result']['logs']}")

# 4. Cleanup
resp = requests.post(f"{BASE}/api/mcp/tools/call", json={
    "name": "deploy_down",
    "arguments": {"deploy_id": deployment["id"], "user_id": "user123"}
})
print(f"Removed: {resp.json()['result']}")
```

## Running the Server

```bash
# Install dependencies
cd internal-server
pip install -e .

# Start the server
python -m src.cli serve --port 8000

# Or run directly
uvicorn src.api.app:app --port 8000
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `http://localhost:8000` | Base URL for API |
| `DEPLOY_WORKSPACE` | `/tmp/devops-deploys` | Workspace for cloned repos |