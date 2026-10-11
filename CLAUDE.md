<!-- PROJECT_MEMORY:START -->
# Project Memory Bootstrap

Project: Yensi Chiefops
Repo path: /Users/nrupal/dev/yensi/dev/YenSi-ChiefOps
Remote: https://github.com/yensi-aiorg/YenSi-ChiefOps.git
Summary: **AI-powered Chief Operations Officer Agent — the COO's Right Hand**
Stack: c++, docker, fastapi, mongodb, python, react, redis, vite
Local ports:
- backend: 20161 (.env)
- backend: 20161 (.env.example)
- app: 23100 (docker-compose.yml)
- frontend: 23101 (.env)
- frontend: 23101 (.env.example)
- app: 23102 (docker-compose.yml)
Deployment:
- hosts: yensi.solutions
Systems: citex, docker, fastapi, react
Secret refs: YenSi-ChiefOps/AI_ADAPTER, YenSi-ChiefOps/AI_CLI_TIMEOUT, YenSi-ChiefOps/AI_CLI_TOOL, YenSi-ChiefOps/CITEX_API_KEY, YenSi-ChiefOps/CITEX_API_URL, YenSi-ChiefOps/CITEX_PROJECT_ID
Commands:
- `project-session-start`
- `project-session-end`
- `project-help`
Last synced: 2026-04-10T21:07:26.419468+00:00
<!-- PROJECT_MEMORY:END -->

# CLAUDE.md — ChiefOps Local Development

## Architecture

- **Docker** (via `docker-compose.yml`, project name `chiefops`):
  - **Frontend** — React 19 / Vite dev server with HMR, port **23100**
    - Volumes mount `./frontend/src` and `./frontend/index.html` into the container for live editing
  - **MongoDB 8** — port **23102**, persistent named volume
  - **Redis 7** — port **23103**, persistent named volume
- **Host** (not Docker):
  - **Backend** — FastAPI / uvicorn, port **23101**
  - Runs on the host so it has access to Claude CLI and local tools
- **External** (separate docker-compose project):
  - **Citex** RAG system — port **20161**

## Bringing Up Local Dev

The backend (API) runs on the host and is started separately by the developer. Only the Docker services need to be started here.

```bash
# Start frontend + MongoDB + Redis in Docker (backend already runs on host)
make infra

# Stop Docker services
make infra-down
```

`make infra` runs `docker compose up --build -d`. This starts 3 services:
1. Frontend with Vite HMR (source-mounted for live reload)
2. MongoDB 8 (waits for healthcheck before frontend starts)
3. Redis 7

Do **NOT** start the backend from Docker — it runs on the host via `make backend` or `bash scripts/dev.sh`.

## URLs

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:23100       |
| Backend  | http://localhost:23101       |
| MongoDB  | mongodb://localhost:23102    |
| Redis    | redis://localhost:23103      |
| Citex    | http://localhost:20161       |

## Useful Commands

| Command                    | Purpose                                    |
|----------------------------|--------------------------------------------|
| `make infra`               | Start Docker services (frontend/mongo/redis) |
| `make infra-down`          | Stop Docker services                       |
| `make backend`             | Start backend on host (separate terminal)  |
| `make logs`                | Follow all Docker logs                     |
| `make logs-frontend`       | Follow frontend logs only                  |
| `make seed`                | Load sample data into MongoDB              |
| `make reset-db`            | Clear all MongoDB collections              |
| `make test-all`            | Run all tests with coverage                |
| `make lint-all`            | Run all linters (ruff, mypy, eslint)       |
| `make format-all`          | Format all code (ruff, prettier)           |
| `make clean`               | Stop services + remove volumes + caches    |

## Key Gotchas

- `redirect_slashes=False` is required in FastAPI — 307 redirects break the Vite proxy
- Do NOT set `VITE_API_URL` in docker-compose — it makes the browser bypass the proxy
- Backend endpoints return paginated wrappers (`{items: [], total, skip, limit}`), not raw arrays
- Frontend stores must unwrap these; setting the wrapper where an array is expected causes silent React crashes
