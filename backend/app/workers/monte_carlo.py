"""
Monte Carlo simulation template.
Deterministic: same seed + range → same result.

Produces full statistical outputs including:
- probability estimates
- variance tracking
- confidence intervals
- sample counts
"""

from __future__ import annotations

import hashlib
import math
import struct


def execute(params: dict, range_start: int, range_end: int, **kwargs) -> dict:
    """
    Monte Carlo estimation of Pi with full statistical output.
    Each iteration generates a deterministic (x,y) from a seeded hash.
    Points inside the unit circle are counted.

    Returns probability estimates, variance, and confidence intervals.
    """
    base_seed = params.get("seed", 42)
    inside_circle = 0
    total = range_end - range_start

    if total <= 0:
        return {
            "inside_circle": 0,
            "total_points": 0,
            "pi_estimate": 0.0,
            "variance": 0.0,
            "standard_error": 0.0,
            "confidence_interval_95": {"lower": 0.0, "upper": 0.0},
            "range_start": range_start,
            "range_end": range_end,
        }

    # Track running stats for variance calculation
    # Each trial is Bernoulli: 1 if inside circle, 0 otherwise
    for i in range(range_start, range_end):
        # Deterministic pseudo-random via hash
        h = hashlib.sha256(struct.pack(">QQ", base_seed, i)).digest()
        x = struct.unpack(">d", h[:8])[0] % 1.0
        y = struct.unpack(">d", h[8:16])[0] % 1.0
        if x * x + y * y <= 1.0:
            inside_circle += 1

    # Probability estimate
    p_hat = inside_circle / total
    pi_estimate = 4.0 * p_hat

    # Variance of the Bernoulli estimator for pi:
    # Var(4 * p_hat) = 16 * p_hat * (1 - p_hat) / n
    variance = 16.0 * p_hat * (1.0 - p_hat) / total
    std_error = math.sqrt(variance) if variance > 0 else 0.0

    # 95% CI
    ci_lower = pi_estimate - 1.96 * std_error
    ci_upper = pi_estimate + 1.96 * std_error

    return {
        "inside_circle": inside_circle,
        "total_points": total,
        "pi_estimate": pi_estimate,
        "p_hat": p_hat,
        "variance": variance,
        "standard_error": std_error,
        "confidence_interval_95": {
            "lower": ci_lower,
            "upper": ci_upper,
        },
        "range_start": range_start,
        "range_end": range_end,
    }
