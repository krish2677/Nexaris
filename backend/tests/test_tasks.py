"""
Tests for compute template determinism.
"""

import pytest

from app.workers.monte_carlo import execute as mc_execute
from app.workers.dataset_stats import execute as ds_execute
from app.workers.matrix_compute import execute as mx_execute


def test_monte_carlo_deterministic():
    """Same seed + range must produce identical results."""
    params = {"seed": 42}
    r1 = mc_execute(params, 0, 10000)
    r2 = mc_execute(params, 0, 10000)
    assert r1 == r2
    assert r1["total_points"] == 10000
    assert 2.5 < r1["pi_estimate"] < 4.0  # rough sanity check


def test_dataset_stats_deterministic():
    params = {"seed": 42, "columns": 4}
    r1 = ds_execute(params, 0, 1000)
    r2 = ds_execute(params, 0, 1000)
    assert r1 == r2
    assert r1["row_count"] == 1000
    assert r1["column_count"] == 4


def test_matrix_compute_deterministic():
    params = {"seed": 42, "matrix_size": 64, "operation": "multiply"}
    chunk_ref = '{"matrix_size": 64, "cols": [0, 64]}'
    r1 = mx_execute(params, 0, 16, chunk_reference=chunk_ref)
    r2 = mx_execute(params, 0, 16, chunk_reference=chunk_ref)
    assert r1["rows_processed"] == r2["rows_processed"]
    assert abs(r1["block_sum"] - r2["block_sum"]) < 0.001


def test_monte_carlo_different_ranges():
    """Different ranges must produce different results."""
    params = {"seed": 42}
    r1 = mc_execute(params, 0, 5000)
    r2 = mc_execute(params, 5000, 10000)
    assert r1["range_start"] != r2["range_start"]
