"""
Dataset statistics template.
Processes REAL dataset chunks from object storage when available,
falls back to deterministic synthetic data for validation/spot-checks.

Computes per-column: sums, means, variances, mins, maxs, histograms.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import struct
from typing import List, Optional

logger = logging.getLogger(__name__)


def execute(
    params: dict,
    range_start: int,
    range_end: int,
    chunk_reference: str | None = None,
    **kwargs,
) -> dict:
    """
    Compute statistics over a dataset chunk.

    If chunk_reference points to real data (JSON array of rows),
    processes actual uploaded data. Otherwise falls back to
    deterministic synthetic data for reproducibility.
    """
    seed = params.get("seed", 42)
    columns = params.get("columns", 4)
    total_rows = range_end - range_start

    # Try to load real chunk data
    real_data = _try_load_chunk_data(chunk_reference, params)
    if real_data is not None:
        return _compute_stats_from_data(real_data, range_start, range_end)

    # Fallback: deterministic synthetic data (for spot-checks and validation)
    return _compute_stats_synthetic(seed, columns, range_start, range_end, total_rows)


def _try_load_chunk_data(
    chunk_reference: Optional[str], params: dict
) -> Optional[List[List]]:
    """Attempt to load real chunk data from the chunk reference."""
    if not chunk_reference:
        return None

    try:
        data = json.loads(chunk_reference)
        # If it's a list of lists/rows, it's inline data
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], list):
                return data
        # If it's a reference object with chunk_data key
        if isinstance(data, dict) and "chunk_data" in data:
            return data["chunk_data"]
    except (json.JSONDecodeError, TypeError):
        pass

    return None


def _compute_stats_from_data(
    rows: List[List], range_start: int, range_end: int
) -> dict:
    """Compute statistics from real dataset rows."""
    if not rows:
        return {"row_count": 0, "column_count": 0, "sums": [], "error": "empty_data"}

    # Detect columns from first row
    columns = len(rows[0]) if rows else 0
    numeric_cols = []

    # Identify numeric columns from first row
    for col in range(columns):
        try:
            float(rows[0][col])
            numeric_cols.append(col)
        except (ValueError, TypeError, IndexError):
            pass

    n_cols = len(numeric_cols)
    sums = [0.0] * n_cols
    mins = [float("inf")] * n_cols
    maxs = [float("-inf")] * n_cols
    sq_sums = [0.0] * n_cols
    valid_counts = [0] * n_cols
    column_names = []

    # Use numeric column indices
    for ci, col in enumerate(numeric_cols):
        column_names.append(f"col_{col}")

    row_count = 0
    for row in rows:
        row_count += 1
        for ci, col in enumerate(numeric_cols):
            try:
                val = float(row[col]) if col < len(row) else 0.0
            except (ValueError, TypeError):
                continue
            sums[ci] += val
            sq_sums[ci] += val * val
            valid_counts[ci] += 1
            if val < mins[ci]:
                mins[ci] = val
            if val > maxs[ci]:
                maxs[ci] = val

    averages = [
        sums[ci] / valid_counts[ci] if valid_counts[ci] > 0 else 0.0
        for ci in range(n_cols)
    ]
    variances = [
        (sq_sums[ci] / valid_counts[ci] - averages[ci] ** 2)
        if valid_counts[ci] > 0 else 0.0
        for ci in range(n_cols)
    ]

    # Build histograms (10 bins per column)
    histograms = {}
    for ci in range(n_cols):
        if mins[ci] < maxs[ci]:
            bin_width = (maxs[ci] - mins[ci]) / 10
            bins = [0] * 10
            for row in rows:
                try:
                    val = float(row[numeric_cols[ci]])
                    bin_idx = min(int((val - mins[ci]) / bin_width), 9)
                    bins[bin_idx] += 1
                except (ValueError, TypeError, IndexError):
                    pass
            histograms[column_names[ci]] = {
                "bins": bins,
                "bin_edges": [round(mins[ci] + i * bin_width, 4) for i in range(11)],
            }

    return {
        "row_count": row_count,
        "column_count": n_cols,
        "column_names": column_names,
        "sums": sums,
        "averages": averages,
        "mins": [m if m != float("inf") else 0 for m in mins],
        "maxs": [m if m != float("-inf") else 0 for m in maxs],
        "variances": variances,
        "histograms": histograms,
        "range_start": range_start,
        "range_end": range_end,
        "data_source": "real",
    }


def _compute_stats_synthetic(
    seed: int, columns: int, range_start: int, range_end: int, total_rows: int
) -> dict:
    """Compute statistics using deterministic synthetic data.
    Used for spot-check validation and when no real data is available."""
    sums = [0.0] * columns
    mins = [float("inf")] * columns
    maxs = [float("-inf")] * columns
    sq_sums = [0.0] * columns

    for i in range(range_start, range_end):
        h = hashlib.sha256(struct.pack(">QQ", seed, i)).digest()
        for col in range(columns):
            offset = (col * 8) % (len(h) - 8)
            raw = struct.unpack(">d", h[offset: offset + 8])[0]
            val = abs(raw) % 1000.0  # bound to [0, 1000)
            sums[col] += val
            sq_sums[col] += val * val
            if val < mins[col]:
                mins[col] = val
            if val > maxs[col]:
                maxs[col] = val

    averages = [s / total_rows if total_rows > 0 else 0 for s in sums]
    variances = [
        (sq_sums[c] / total_rows) - (averages[c] ** 2) if total_rows > 0 else 0
        for c in range(columns)
    ]

    return {
        "row_count": total_rows,
        "column_count": columns,
        "sums": sums,
        "averages": averages,
        "mins": mins,
        "maxs": maxs,
        "variances": variances,
        "range_start": range_start,
        "range_end": range_end,
        "data_source": "synthetic",
    }
