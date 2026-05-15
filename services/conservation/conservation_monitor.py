#!/usr/bin/env python3
"""Conservation law monitor — continuous daemon that checks all PLATO
tiles for conservation law compliance. Flags violations, tracks drift,
and feeds back into the Refiner.

Runs as a docker service inside fleet-stack. Polls PLATO rooms
periodically and submits violation reports as tiles.
"""

import sys, os, json, urllib.request, time, math

# Add core module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.conservation import *

PLATO = os.environ.get("PLATO_URL", "http://plato:8847")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))  # seconds between polls
MONITORED_ROOMS = os.environ.get("MONITORED_ROOMS", "research_log,fleet_math,event-bus").split(",")


def submit(q, a, tags):
    """Submit a tile to PLATO reporting monitor findings."""
    tile = {
        "room_id": "research_log",
        "domain": "conservation",
        "question": q,
        "answer": str(a)[:1950],
        "tags": tags or [],
        "source": "conservation-monitor",
        "confidence": 0.99,
    }
    try:
        d = json.dumps(tile).encode()
        urllib.request.urlopen(
            urllib.request.Request(f"{PLATO}/submit", data=d,
                                   headers={"Content-Type": "application/json"}),
            timeout=10
        )
    except Exception as e:
        sys.stderr.write(f"[monitor] submit error: {e}\n")


class ConservationMonitor:
    """Continuous monitor checking all PLATO tiles for conservation law."""

    def __init__(self):
        self.violations = []
        self.checks = 0

    def check_tiles(self, tiles):
        """Check all tiles for conservation meta fields."""
        self.checks += len(tiles)
        violations_found = []

        for t in tiles:
            meta = t.get("_meta", {}) if isinstance(t, dict) else {}
            # Also check answer field for gamma/H
            ans = t.get("answer", "")
            if isinstance(ans, str) and ans.startswith("{"):
                try:
                    parsed = json.loads(ans)
                    if "gamma" in parsed and "H" in parsed and "V" in parsed:
                        g, h, v = parsed["gamma"], parsed["H"], parsed["V"]
                        if not is_conserved(g, h, v):
                            violations_found.append({
                                "question": t.get("question", "?"),
                                "gamma": g, "H": h, "V": v,
                                "deviation": round(deviation(g, h, v), 3),
                                "expected": round(predicted_sum(v), 3),
                            })
                except Exception:
                    pass

        if violations_found:
            self.violations.extend(violations_found)
            submit("conservation/violations", json.dumps({
                "count": len(violations_found),
                "violations": violations_found[:5],
                "total_checks": self.checks,
            }), ["conservation", "violation", "monitor"])

        return violations_found

    def report(self):
        """Conservation law compliance report."""
        if self.checks == 0:
            return {"status": "no_data"}

        return {
            "checks": self.checks,
            "violations": len(self.violations),
            "compliance_rate": f"{100 * (1 - len(self.violations) / max(1, self.checks)):.1f}%",
            "status": "HEALTHY" if len(self.violations) < 3 else "DEGRADED",
        }

    def poll_room(self, room):
        """Poll a single PLATO room for tiles to check."""
        try:
            url = f"{PLATO}/room/{room}/history"
            resp = json.loads(urllib.request.urlopen(url, timeout=10).read())
            tiles = resp.get("tiles", []) if isinstance(resp, dict) else resp
            v = self.check_tiles(tiles)
            return len(tiles), len(v)
        except Exception as e:
            sys.stderr.write(f"[monitor] room {room}: error ({e})\n")
            return 0, 0

    def run_forever(self):
        """Main loop — poll monitored rooms forever."""
        print(f"Conservation Law Monitor starting — PLATO={PLATO}, interval={POLL_INTERVAL}s")
        print(f"  Monitored rooms: {MONITORED_ROOMS}")
        print(f"  Core constants: gamma + H = {INTERCEPT} + ({SLOPE}) * log(V)")
        sys.stdout.flush()

        while True:
            total_tiles = 0
            total_violations = 0
            for room in MONITORED_ROOMS:
                room = room.strip()
                if not room:
                    continue
                tiles, viols = self.poll_room(room)
                total_tiles += tiles
                total_violations += viols
                print(f"  {room}: {tiles} tiles, {viols} violations")
                sys.stdout.flush()

            report = self.report()
            print(f"\n[check] {total_tiles} tiles, {total_violations} violations — {report['status']}")
            sys.stdout.flush()

            # Submit periodic report as tile
            submit("conservation/report", json.dumps(report),
                   ["conservation", "report", report["status"]])

            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    monitor = ConservationMonitor()
    monitor.run_forever()
