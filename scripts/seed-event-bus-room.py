#!/usr/bin/env python3
"""Seed the event-bus room on first startup.

Creates the event-bus room by submitting a bootstrap tile to PLATO.
Event bus rooms enable pubsub-style communication between services:
agents emit events as tiles, officers subscribe by polling the room.

Usage:
    python3 seed-event-bus-room.py [--plato-url http://plato:8847]

This runs as a one-shot init container in docker-compose.
"""

import json, urllib.request, sys, time, os

PLATO = os.environ.get("PLATO_URL", "http://plato:8847")
MAX_RETRIES = int(os.environ.get("SEED_MAX_RETRIES", "10"))
RETRY_DELAY = int(os.environ.get("SEED_RETRY_DELAY", "3"))


def wait_for_plato(max_retries=MAX_RETRIES):
    """Wait for PLATO to be available before seeding."""
    for attempt in range(1, max_retries + 1):
        try:
            resp = json.loads(
                urllib.request.urlopen(f"{PLATO}/status", timeout=5).read()
            )
            if resp.get("status") == "active":
                print(f"[seed] PLATO is ready (attempt {attempt})")
                return True
        except Exception as e:
            print(f"[seed] waiting for PLATO (attempt {attempt}/{max_retries}): {e}")
        time.sleep(RETRY_DELAY)
    print(f"[seed] ERROR: PLATO not available after {max_retries} attempts")
    return False


def seed_event_bus_room():
    """Submit a bootstrap tile to create the event-bus room."""
    tile = {
        "room_id": "event-bus",
        "domain": "pubsub",
        "question": "event-bus/bootstrap",
        "answer": json.dumps({
            "event": "bootstrap",
            "version": 1,
            "message": "Event bus room initialized. Services can now publish/subscribe via tiles.",
            "rooms": ["research_log", "fleet_math", "event-bus"],
            "timestamp": time.time(),
        }),
        "tags": ["pubsub", "event-bus", "bootstrap"],
        "source": "fleet-stack-seed",
        "confidence": 1.0,
    }

    try:
        data = json.dumps(tile).encode()
        req = urllib.request.Request(
            f"{PLATO}/submit", data=data,
            headers={"Content-Type": "application/json"}
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        if resp.get("status") == "accepted":
            print(f"[seed] Event bus room seeded successfully (tile #{resp.get('tile_count')})")
            return True
        else:
            print(f"[seed] ERROR: tile rejected: {resp}")
            return False
    except Exception as e:
        print(f"[seed] ERROR submitting tile: {e}")
        return False


if __name__ == "__main__":
    print("[seed] Event bus room seed starting...")
    print(f"[seed] PLATO: {PLATO}")

    if not wait_for_plato():
        sys.exit(1)

    if seed_event_bus_room():
        print("[seed] Done — event bus room is ready")
        sys.exit(0)
    else:
        print("[seed] Failed to seed event bus room")
        sys.exit(1)
