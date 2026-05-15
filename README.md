# Fleet Stack

> One command to deploy the entire Cocapn fleet infrastructure.

```bash
# Set API keys
export DEEPINFRA_KEY=your-key
export GROQ_KEY=your-key
export ZAI_KEY=your-key

# Launch everything
docker compose up -d
```

## What You Get

| Service | Port | What It Does |
|---------|------|-------------|
| PlatoClaw | :8847 | PLATO server + rooms + routing |
| Fleet Router | :8100 | Auto-routing API (OpenAI compatible) |
| PLATO MCP | :8300 | MCP tools for any framework |
| Dashboard | :8080 | Web UI for rooms, tiles, officers |

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
```

The math is invisible. You just complete the room task.
