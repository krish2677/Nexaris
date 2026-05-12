"""
Compute engine — dispatches work to the correct template.
Used by both workers and the validation spot-checker.
"""

from __future__ import annotations

from app.workers import monte_carlo, dataset_stats, matrix_compute

_TEMPLATES = {
    "monte_carlo": monte_carlo.execute,
    "dataset_stats": dataset_stats.execute,
    "matrix_compute": matrix_compute.execute,
}


def execute_template(
    template_type: str,
    params: dict,
    range_start: int | None = None,
    range_end: int | None = None,
    chunk_reference: str | None = None,
) -> dict:
    """Execute a compute template and return the result dict."""
    fn = _TEMPLATES.get(template_type)
    if fn is None:
        raise ValueError(f"Unknown template type: {template_type}")

    return fn(
        params=params,
        range_start=range_start or 0,
        range_end=range_end or 0,
        chunk_reference=chunk_reference,
    )
