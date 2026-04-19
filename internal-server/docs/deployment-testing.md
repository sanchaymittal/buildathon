# End-to-End Deployment Testing

This guide walks through a full Docker-native deployment cycle using the API and CLI.

## Prerequisites
- Python 3.9+
- Docker daemon running locally
- GitHub repository with a Dockerfile (or a buildable app)
- GitHub token exported as `GITHUB_TOKEN` or stored in `~/.devops/credentials.json`

## 1) Install and Configure
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Set a GitHub token (required for private repos or higher rate limits):
```bash
export GITHUB_TOKEN="<your_token_here>"
```

Optional: confirm Docker connectivity.
```bash
docker ps
```

## 2) Start the API Server
```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

Verify health:
```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/health/docker
```

## 3) Deploy a Repository (API)
Use a repo that builds into a container. Replace `owner/repo` and `container_port`.

```bash
curl -s -X POST http://localhost:8000/deployments \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "owner/repo",
    "branch": "main",
    "container_port": 8000,
    "env": {
      "ENVIRONMENT": "staging"
    }
  }'
```

The response returns a `Deployment` object with `id`, `container_name`, and `url`.

## 4) Check Status and Logs
```bash
curl -s http://localhost:8000/deployments
curl -s http://localhost:8000/deployments/<deploy_id>
curl -s "http://localhost:8000/deployments/<deploy_id>/logs?tail=200"
```

## 5) Hit the Deployed App
Use the `url` field from the deployment response:
```bash
curl -s http://localhost:<host_port>
```

## 6) Stop, Start, Restart
```bash
curl -s -X POST http://localhost:8000/deployments/<deploy_id>/stop
curl -s -X POST http://localhost:8000/deployments/<deploy_id>/start
curl -s -X POST http://localhost:8000/deployments/<deploy_id>/restart
```

## 7) Remove the Deployment
```bash
curl -s -X DELETE http://localhost:8000/deployments/<deploy_id>
```

## 8) Container Introspection (Optional)
```bash
curl -s http://localhost:8000/containers
curl -s http://localhost:8000/containers/<container_id>
curl -s "http://localhost:8000/containers/<container_id>/logs?tail=200"
```

## CLI Workflow (Alternative)
If you installed the project in editable mode, you can use the CLI instead:

```bash
devops-agent docker deploy --repo owner/repo --branch main --port 8000 --env ENVIRONMENT=staging
devops-agent docker list
devops-agent docker logs <deploy_id> --tail 200
devops-agent docker stop <deploy_id>
devops-agent docker start <deploy_id>
devops-agent docker rm <deploy_id>
```

## Troubleshooting
- `400 Bad Request` during deployment usually means the repo failed to clone or build. Inspect `GET /deployments/<deploy_id>/logs`.
- `503 Service Unavailable` from `/health/docker` indicates the Docker daemon is not reachable.
- If the app is not responding, confirm the repo exposes the correct `container_port`.
