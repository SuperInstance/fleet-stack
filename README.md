# Fleet Stack

> One command to deploy the entire Cocapn fleet infrastructure.

```bash
# Set API keys
export DEEPINFRA_KEY=your-key
export GROQ_KEY=your-key
export ZAI_KEY=your-key

# Launch everything (seed runs once, then exits)
docker compose up -d
```

## What You Get

| Service | Port | What It Does |
|---------|------|-------------|
| PlatoClaw | :8847 | PLATO server + rooms + routing |
| Fleet Router | :8100 | Auto-routing API (OpenAI compatible) |
| PLATO MCP | :8300 | MCP tools for any framework |
| Dashboard | :8080 | Web UI for rooms, tiles, officers |
| Conservation Monitor | — | Daemon checking conservation law compliance across all rooms |
| Event Bus Seed | — | One-shot init that creates the event-bus pubsub room |

## Services Explained

### PlatoClaw (`:8847`)
The core PLATO server. Manages rooms, tiles, and routing. All services depend on it.

### Fleet Router (`:8100`)
OpenAI-compatible auto-routing API. Routes prompts to the cheapest safe model based on domain detection.

### PLATO MCP (`:8300`)
MCP (Model Context Protocol) bridge. Exposes PLATO rooms and tiles as MCP tools for any framework.

### Dashboard (`:8080`)
Web UI served via nginx. Browse rooms, tiles, and fleet status.

### Conservation Monitor (new)
A continuous Python daemon that polls all PLATO rooms and checks tiles for **conservation law compliance**.

The conservation law is a core invariant of the PLATO system:

> **gamma + H = 1.283 - 0.159 × log(V) ± ε**

- **gamma**: gate coefficient (agent skill coupling)
- **H**: Helmholtz free energy of the tile/room system
- **V**: fleet size (number of agents/tiles)
- **ε**: ~0.15 for style coupling, ~0.03 for topology coupling

Violations are flagged and submitted as tiles to `research_log`. Compliance reports are generated every poll cycle.

**Configurable via environment:**
- `POLL_INTERVAL`: seconds between polls (default 60)
- `MONITORED_ROOMS`: comma-separated room list (default: research_log,fleet_math,event-bus)

### Event Bus Seed
Runs once on first startup (then exits). Submits a bootstrap tile that creates the **event-bus** room.

The event-bus room enables pubsub-style communication between agents and officers:
- Agents emit events as tiles in the event-bus room
- Officers subscribe by polling the room
- Services can react to events without direct coupling

**To re-seed manually:**
```bash
docker compose run --rm seed
```

## Endpoints

```bash
# PLATO
curl http://localhost:8847/status

# Route a query (auto-picks cheapest safe model)
curl -X POST http://localhost:8100/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 37 + 48?"}'

# OpenAI-compatible (drop-in migration)
# Just change: openai.base_url = "http://localhost:8100/v1"

# MCP tools
curl http://localhost:8300/tools

# Auto-route + complete through PLATO
curl -X POST http://localhost:8847/complete \
  -d '{"prompt": "compute the Eisenstein norm of 3+2ω"}'
```

## Architecture

```
Any Client → Fleet Router (:8100) → Cheapest Safe Model
           ↕
         PLATO (:8847) ← Officers maintain rooms
           ↕
         MCP (:8300) ← Any framework reads/writes tiles
           ↕

    Conservation Monitor ← continuous compliance checks
           ↕
       Event Bus Room ← pubsub events between services
```

The math is invisible. You just complete the room task.

**New:** The conservation monitor runs alongside the fleet, ensuring all tiles respect the gamma+H invariant. The event bus room decouples services — any agent can publish, any officer can subscribe.
