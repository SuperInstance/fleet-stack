# CONTRIBUTING.md Added — Fleet Stack

**Date:** 2026-05-17
**Action:** Created `CONTRIBUTING.md`

## Why This Repo Needed It

Fleet Stack is the deployment hub for the entire Cocapn fleet infrastructure. It orchestrates 6+ services (PlatoClaw, Fleet Router, PLATO MCP, Dashboard, Conservation Monitor, Event Bus Seed). Despite having a good README with deployment instructions, it had:

- No guidance on how to develop services locally
- No service-by-service code style conventions
- No instructions for adding new services to the stack
- No testing guidance (unit tests per service, integration tests)

A multi-service Docker Compose project without contribution guidance is a barrier for anyone wanting to add a new service or fix an existing one.

## What the Contribution Workflow Looks Like

1. Fork and create a feature branch
2. Work on the relevant `services/<name>/` subdirectory
3. Test the service: `cd services/<name> && pytest`
4. Integration test: `docker compose up -d && ./scripts/test-integration.sh`
5. Ensure service has a Dockerfile, healthcheck, and documented env vars
6. Open PR

## Special Notes

- **Service Dependencies**: All services depend on PlatoClaw (:8847). New services must follow this pattern and include healthchecks that verify PlatoClaw is reachable.
- **Multi-Service Testing**: Contributors need Docker + Docker Compose to run integration tests. Unit tests can run standalone in each `services/<name>/`.
- **CI Pipeline**: GitHub Actions runs linting, tests, and Docker builds. Make sure your service passes all three.
