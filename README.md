# fleet-stack

Docker Compose deployment for the SuperInstance fleet. Brings up PLATO server, fleet router, MCP bridge, conservation monitor, and event bus in one command.

## Quick Start

```bash
# Set at least one LLM provider key
export DEEPINFRA_KEY=sk-...
export GROQ_KEY=gsk_...
export ZAI_KEY=zai-...

# Launch all services
docker compose up -d

# Verify everything is running
docker compose ps
curl http://localhost:8847/status
```

## Services and Ports

| Service | Port | Image/Build | Runs |
|---------|------|-------------|------|
| plato | 8847 | `../platoclaw/Dockerfile` | Continuous |
| router | 8100 | `../fleet-router/Dockerfile` | Continuous |
| mcp | 8300 | `../plato-mcp/Dockerfile` | Continuous |
| web | 8080 | `nginx:alpine` | Continuous |
| conservation | — | `services/conservation/Dockerfile` | Continuous daemon |
| seed | — | `Dockerfile.seed` | One-shot, exits after init |

## docker-compose.yml Structure

The compose file defines six services with explicit dependency ordering via `depends_on` with `condition: service_healthy`. PLATO is the root dependency — router, MCP, seed, and conservation all wait for PLATO's health check before starting.

```yaml
services:
  plato:
    build:
      context: ../platoclaw
      dockerfile: Dockerfile
    ports:
      - "8847:8847"
    environment:
      - PLATO_PORT=8847
    volumes:
      - plato-data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8847/status"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped
```

### Dependency Chain

```
plato (root, health-checked)
  ├── router (waits for plato healthy)
  ├── mcp (waits for plato healthy)
  ├── seed (waits for plato healthy, runs once)
  └── conservation (waits for plato healthy, continuous daemon)
web (nginx, depends on plato + router, no health check)
```

## Environment Variables

### Required (at least one)

| Variable | Used by | Description |
|----------|---------|-------------|
| `DEEPINFRA_KEY` | router | DeepInfra API key |
| `GROQ_KEY` | router | Groq API key |
| `ZAI_KEY` | router | ZAI API key |

### Optional

| Variable | Default | Used by | Description |
|----------|---------|---------|-------------|
| `PLATO_PORT` | 8847 | plato | PLATO listen port |
| `POLL_INTERVAL` | 60 | conservation | Seconds between conservation checks |
| `MONITORED_ROOMS` | research_log,fleet_math,event-bus | conservation | Comma-separated PLATO rooms to monitor |
| `SEED_MAX_RETRIES` | 10 | seed | Retries before seed gives up |
| `SEED_RETRY_DELAY` | 3 | seed | Seconds between seed retries |

### Setting Variables

```bash
# .env file in the fleet-stack directory
DEEPINFRA_KEY=sk-...
GROQ_KEY=gsk_...
ZAI_KEY=zai-...
POLL_INTERVAL=120
MONITORED_ROOMS=research_log,fleet_math,event-bus,custom_room
```

Or inline:

```bash
POLL_INTERVAL=30 docker compose up -d
```

## Using the APIs

### PLATO Server (port 8847)

```bash
# Health check
curl http://localhost:8847/status
# {"status": "active", ...}

# Submit a tile
curl -X POST http://localhost:8847/submit \
  -H "Content-Type: application/json" \
  -d '{
    "room_id": "research_log",
    "domain": "test",
    "question": "test/ping",
    "answer": "pong",
    "tags": ["test"],
    "source": "manual",
    "confidence": 1.0
  }'

# Get room history
curl http://localhost:8847/room/research_log/history
```

### Fleet Router (port 8100)

OpenAI-compatible endpoint. Drop-in replacement — point any OpenAI SDK at it:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8100/v1", api_key="unused")
response = client.chat.completions.create(
    model="auto",
    messages=[{"role": "user", "content": "What is 37 + 48?"}]
)
print(response.choices[0].message.content)
```

Raw curl:

```bash
curl -X POST http://localhost:8100/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 37 + 48?"}'
```

### MCP Bridge (port 8300)

```bash
# List available tools
curl http://localhost:8300/tools
```

## Conservation Monitor

Continuous daemon that polls PLATO rooms and checks tiles against the conservation law:

```
gamma + H = 1.283 - 0.159 × log(V) ± ε
```

Where `ε ≈ 0.15` for style coupling, `ε ≈ 0.03` for topology coupling.

The monitor runs from `services/conservation/conservation_monitor.py`. It:
1. Polls each room in `MONITORED_ROOMS` every `POLL_INTERVAL` seconds
2. Parses tiles for `_meta.gamma`, `_meta.H`, `_meta.V` fields
3. Also parses answer JSON when answers contain `{gamma, H, V}` dicts
4. Flags violations and submits them as tiles to `research_log`
5. Logs compliance reports each cycle

### Customizing the Monitor

The conservation law constants live in `services/conservation/core/conservation.py`:

```python
SLOPE = -0.159
INTERCEPT = 1.283

def is_conserved(gamma, H, V, coupling_type="style", threshold=0.3):
    pred = INTERCEPT + SLOPE * math.log(V)
    return abs((gamma + H) - pred) < threshold
```

To change the compliance threshold or add new coupling types, edit this file.

### Monitor Output

```
Conservation Law Monitor starting — PLATO=http://plato:8847, interval=60s
  Monitored rooms: ['research_log', 'fleet_math', 'event-bus']
  Core constants: gamma + H = 1.283 + (-0.159) * log(V)
  research_log: 42 tiles, 0 violations
  fleet_math: 18 tiles, 1 violations
  event-bus: 7 tiles, 0 violations

[check] 67 tiles, 1 violations — HEALTHY
```

Status values: `HEALTHY` (fewer than 3 violations), `DEGRADED` (3+).

## Event Bus Seed

One-shot init container (`scripts/seed-event-bus-room.py`) that:
1. Waits for PLATO to become healthy (retries up to `SEED_MAX_RETRIES` times)
2. Submits a bootstrap tile to create the `event-bus` room
3. Exits

The event-bus room enables pubsub between services — agents publish events as tiles, officers subscribe by polling.

Re-seed manually:

```bash
docker compose run --rm seed
```

## Adding a Custom Service

Add a new service block to `docker-compose.yml`:

```yaml
  my-service:
    build:
      context: ./services/my-service
      dockerfile: Dockerfile
    environment:
      - PLATO_URL=http://plato:8847
    depends_on:
      plato:
        condition: service_healthy
    restart: unless-stopped
```

Services communicate with PLATO over HTTP. The internal Docker network resolves `plato` as the hostname — use `http://plato:8847` as the PLATO URL inside containers.

## Adding a Custom Room to Monitor

```bash
# In .env or docker-compose override
MONITORED_ROOMS=research_log,fleet_math,event-bus,my_custom_room
```

Or override in a `docker-compose.override.yml`:

```yaml
services:
  conservation:
    environment:
      - MONITORED_ROOMS=research_log,fleet_math,event-bus,my_custom_room
```

## Scaling

```bash
# Multiple PLATO instances (requires a load balancer in front)
docker compose up -d --scale plato=3

# View logs per service
docker compose logs -f conservation
docker compose logs -f plato
```

## Troubleshooting

```bash
# Check which services are healthy
docker compose ps

# PLATO won't start — check logs
docker compose logs plato

# Seed keeps retrying — PLATO isn't passing health check
docker compose logs seed

# Conservation monitor not seeing tiles
# Verify the room exists and has tiles:
curl http://localhost:8847/room/research_log/history
```

## Build Contexts

The compose file references sibling directories for builds:

```
parent-dir/
├── platoclaw/       ← plato build context
├── fleet-router/    ← router build context
├── plato-mcp/       ← mcp build context
└── fleet-stack/     ← this repo
    ├── docker-compose.yml
    ├── Dockerfile.seed
    ├── scripts/
    └── services/
        └── conservation/
```

Clone the sibling repos at the same level as `fleet-stack` for builds to work.

## Related Repos

- [plato-core](https://github.com/SuperInstance/plato-core) — Base types + mesh registry
- [fleet-router](https://github.com/SuperInstance/fleet-router) — Query routing logic
- [quality-gate-stream](https://github.com/SuperInstance/quality-gate-stream) — Tile quality scoring
- [constraint-theory-core](https://github.com/SuperInstance/constraint-theory-core) — Conservation law math

## License

MIT
