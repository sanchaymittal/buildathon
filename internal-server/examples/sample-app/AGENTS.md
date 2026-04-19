# Sample App

A tiny Python HTTP server that responds with a greeting. Used to demo the
local-compose deploy flow of the Agentic DevOps agent.

- service: web
- port: 8000
- env:
  - `PORT` — port the server binds to (default `8000`)
  - `GREETING` — message returned on `GET /`
- healthcheck: `curl http://localhost:8000/`

Bring it up with:

```bash
python -m src.cli docker compose up --path ../../examples/sample-app
```

(from the `agentic_devops/` directory)
