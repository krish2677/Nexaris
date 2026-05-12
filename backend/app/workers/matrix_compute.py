"""
Matrix computation template.
Processes a row-block of a matrix multiplication.
Uses SHA-256 hash-based deterministic generation (no numpy)
to ensure parity with Android client.
"""

from __future__ import annotations

import hashlib
import json
import struct


def execute(
    params: dict,
    range_start: int,
    range_end: int,
    chunk_reference: str | None = None,
    **kwargs,
) -> dict:
    """
    Compute a block of rows for a simplified matrix multiplication.
    Matrices are deterministically generated from a SHA-256 seed,
    identical to the Android ComputeTemplates implementation.
    """
    seed = params.get("seed", 42)
    chunk_meta = json.loads(chunk_reference) if chunk_reference else {}
    matrix_size = chunk_meta.get("matrix_size", params.get("matrix_size", 256))
    row_count = range_end - range_start

    block_sum = 0.0
    row_sums = []

    for row in range(range_start, range_end):
        row_sum = 0.0
        for col in range(matrix_size):
            # Generate A[row][col] from seed+1
            hash_a = hashlib.sha256(
                struct.pack(">QQ", seed + 1, row * matrix_size + col)
            ).digest()
            a = struct.unpack(">d", hash_a[:8])[0]

            # Generate B[col] contribution from seed
            hash_b = hashlib.sha256(
                struct.pack(">QQ", seed, col)
            ).digest()
            b = struct.unpack(">d", hash_b[:8])[0]

            row_sum += a * b
        row_sums.append(row_sum)
        block_sum += row_sum

    block_mean = block_sum / (row_count * matrix_size) if row_count > 0 else 0.0

    return {
        "block_sum": block_sum,
        "block_mean": block_mean,
        "row_sums": row_sums,
        "rows_processed": row_count,
        "range_start": range_start,
        "range_end": range_end,
    }
