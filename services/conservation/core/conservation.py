"""Conservation law — core invariant of the PLATO system.
Integrated into: gates, Refiner, memory module, event bus, FleetHealthMetric.

gamma + H = 1.283 - 0.159 * log(V) ± epsilon
epsilon ~0.15 for style coupling, ~0.03 for topology coupling
"""

import math

# Constants (empirically derived, R²=0.9602)
SLOPE = -0.159
INTERCEPT = 1.283

def predicted_sum(V, coupling_type="style"):
    """Predict gamma+H for a given fleet size V."""
    if V < 2:
        return 1.5
    pred = INTERCEPT + SLOPE * math.log(V)
    if coupling_type == "topology":
        pred += 0.4  # topology has higher baseline
    elif coupling_type == "directed":
        pred += 0.2
    return pred

def deviation(gamma, H, V, coupling_type="style"):
    """Return deviation from conservation law."""
    return (gamma + H) - predicted_sum(V, coupling_type)

def is_conserved(gamma, H, V, coupling_type="style", threshold=0.3):
    """Check if gamma+H is within conservation law bounds."""
    dev = abs(deviation(gamma, H, V, coupling_type))
    return dev < threshold

def expected_range(V, coupling_type="style"):
    """Return (lower, upper) expected range for gamma+H."""
    pred = predicted_sum(V, coupling_type)
    sigma = 0.15 if coupling_type == "style" else 0.03
    return (pred - 2*sigma, pred + 2*sigma)

def V_from_sum(gh_sum, coupling_type="style"):
    """Infer fleet size V from observed gamma+H sum."""
    raw = math.exp((gh_sum - INTERCEPT) / SLOPE)
    return max(2, round(raw))

# ── Gate integration: P4 gate (quality) uses conservation law ──
def gate_check(tile, coupling_type="style"):
    """Gate check: tiles should not violate conservation law.
    Returns (pass: bool, reason: str)."""
    metadata = tile.get("_meta", {})
    gamma = metadata.get("gamma")
    H = metadata.get("H")
    V = metadata.get("V")

    if gamma is not None and H is not None and V is not None:
        if not is_conserved(gamma, H, V, coupling_type):
            pred = predicted_sum(V, coupling_type)
            actual = gamma + H
            return (False, f"conservation violation: gamma+H={actual:.2f}, expected ~{pred:.2f}")
    return (True, "")

# ── Refiner integration: detect conservation drift ──
def conservation_drift(recent_tiles, V, coupling_type="style"):
    """Check if recent tiles show conservation law drift.
    Returns drift_score (0=normal, higher = anomalous)."""
    if len(recent_tiles) < 5:
        return 0.0

    sums = []
    for t in recent_tiles[-10:]:
        m = t.get("_meta", {})
        g = m.get("gamma", 0)
        h = m.get("H", 0)
        if g > 0 and h > 0:
            sums.append(g + h)

    if not sums:
        return 0.0

    mean_sum = sum(sums) / len(sums)
    pred = predicted_sum(V, coupling_type)
    return abs(mean_sum - pred) / 0.15  # in sigma units
