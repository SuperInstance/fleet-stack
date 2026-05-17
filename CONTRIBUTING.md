# Contributing to Fleet Stack

> *One command to deploy the entire Cocapn fleet infrastructure.*

## Quick Start

Fleet Stack is a Docker Compose deployment of the Cocapn ecosystem.

### Prerequisites
- Docker & Docker Compose v2
- API keys for model providers (DeepInfra, Groq, z.ai/Groq)

### Launch Locally

```bash
# Clone
git clone https://github.com/SuperInstance/fleet-stack.git
cd fleet-stack

# Set API keys
export DEEPINFRA_KEY=your-key
export GROQ_KEY=your-key
export ZAI_KEY=your-key

# Launch everything
docker compose up -d
```

### Verify

```bash
# Check PLATO server
curl http://localhost:8847/status

# Check Fleet Router (OpenAI-compatible)
curl -X POST http://localhost:8100/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "ping?"}'

# Check Dashboard
open http://localhost:8080
```

## What's In Here

| Service | Port | Description |
|---------|------|-------------|
| PlatoClaw | :8847 | Core PLATO server — rooms, tiles, routing |
| Fleet Router | :8100 | OpenAI-compatible auto-routing API |
| PLATO MCP | :8300 | MCP bridge for any framework |
| Dashboard | :8080 | Web UI for fleet status |
| Conservation Monitor | — | Continuous compliance daemon |
| Event Bus Seed | — | One-shot bootstrap for pubsub |

## Making Changes

1. **Fork the repo**
2. **Create a feature branch** (`git checkout -b feature/my-feature`)
3. **Understand the services** — each service lives in its own `services/` subdirectory:
   - `services/fleet-router/` — API gateway
   - `services/dashboard/` — Web UI
   - `services/conservation-monitor/` — Compliance daemon
   - `services/seed/` — Bootstrap scripts
4. **Test with the full stack** — run `docker compose up -d` and verify your service
5. **Commit** (`git commit -m "feat: add my feature"`)
6. **Push** (`git push origin feature/my-feature`)
7. **Open a PR**

## Code Style

### Python Services
- Python 3.10+ with type hints
- Use `ruff` for linting (`ruff check .`)
- Format with `ruff format .`
- One service per `services/` subdirectory

### Docker
- Use multi-stage builds for small images
- Pin base image versions (no `:latest`)
- Document environment variables in the service README
- Ensure all ports are configurable via env vars

### Configuration
- Use `services/<name>/config.py` for service config
- Load secrets from environment variables, never hardcode
- Default values should work for local development

## Testing

### Service Tests
```bash
# Run tests for a specific service
cd services/conservation-monitor
pip install -e ".[dev]"
pytest
```

### Integration Test
```bash
# Launch full stack
docker compose up -d

# Run integration tests
./scripts/test-integration.sh
```

### CI
The repo has a GitHub Actions workflow (`.github/workflows/python-ci.yml`) that:
- Runs linting (ruff)
- Runs tests (pytest)
- Builds Docker images

## Adding a New Service

1. Create `services/<service-name>/` with:
   - `Dockerfile` (multi-stage)
   - `requirements.txt` (if Python)
   - `config.py` with env-var loading
   - Tests in a `tests/` subdirectory
2. Add to `docker-compose.yml` with healthcheck
3. Add startup to `scripts/init.sh` if needed
4. Document the new service in `README.md`

## Service Dependencies

```
PlatoClaw (:8847) ← ALL services depend on this
    ↕
Fleet Router (:8100) ← depends on PlatoClaw + model APIs
PLATO MCP (:8300)   ← depends on PlatoClaw
Dashboard (:8080)   ← depends on PlatoClaw
Conservation Monitor ← depends on PlatoClaw
Event Bus Seed      ← depends on PlatoClaw (runs once, then exits)
```

## Reporting Issues

Open an [Issue](https://github.com/SuperInstance/fleet-stack/issues) with:
- `docker compose logs` output
- Step-by-step reproduction
- Environment details (OS, Docker version)

## Questions?

- Read the main [README](README.md) for architecture overview
- Open a [Discussion](https://github.com/SuperInstance/fleet-stack/discussions)
- Check existing [Issues](https://github.com/SuperInstance/fleet-stack/issues)
