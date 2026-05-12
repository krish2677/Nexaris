"""
Aggregation service — mathematically correct distributed aggregation engine.
Supports incremental, idempotent, crash-safe aggregation with checkpointing.

Key fixes over old system:
- Only aggregates CANONICAL results (one per task, not all duplicates)
- Uses parallel variance algorithm (Welford/Chan) for correct distributed stats
- Persists results to aggregated_results table
- Supports resumable aggregation via checkpoints
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aggregated_result import AggregatedResult, AggregationStatus
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.task_result import TaskResult, ValidationStatus

logger = logging.getLogger(__name__)


async def aggregate_job(db: AsyncSession, job_id: UUID) -> Dict[str, Any]:
    """Run full aggregation for a job.  Idempotent and incremental."""
    job_q = await db.execute(select(Job).where(Job.id == job_id))
    job = job_q.scalar_one_or_none()
    if not job:
        return {"error": "Job not found"}

    # Fetch or create aggregation record
    agg_q = await db.execute(
        select(AggregatedResult).where(AggregatedResult.job_id == job_id)
    )
    agg = agg_q.scalar_one_or_none()
    if not agg:
        total_q = await db.execute(
            select(func.count(Task.id)).where(Task.job_id == job_id)
        )
        total = total_q.scalar() or 0
        agg = AggregatedResult(
            job_id=job_id,
            total_tasks=total,
            aggregation_status=AggregationStatus.IN_PROGRESS,
        )
        db.add(agg)
        await db.flush()

    # Fetch ONLY canonical results (one per task — the consensus winner)
    results_q = await db.execute(
        select(TaskResult)
        .join(Task, TaskResult.task_id == Task.id)
        .where(
            Task.job_id == job_id,
            Task.status == TaskStatus.COMPLETED,
            TaskResult.validation_status == ValidationStatus.VALID,
            TaskResult.is_canonical == True,  # noqa: E712
        )
        .order_by(Task.range_start)
    )
    results = list(results_q.scalars().all())

    if not results:
        agg.metrics_json = json.dumps({"status": "no_canonical_results"})
        agg.completed_tasks = 0
        await db.commit()
        return json.loads(agg.metrics_json)

    parsed = [json.loads(r.result_json) for r in results]
    template = job.template_type.value

    if template == "monte_carlo":
        metrics = _aggregate_monte_carlo(parsed)
    elif template == "dataset_stats":
        metrics = _aggregate_dataset_stats(parsed)
    elif template == "matrix_compute":
        metrics = _aggregate_matrix(parsed)
    else:
        metrics = {"template": template, "chunks": len(parsed)}

    metrics["template"] = template
    metrics["chunks_processed"] = len(parsed)
    metrics["aggregated_at"] = datetime.now(timezone.utc).isoformat()

    # Persist
    agg.metrics_json = json.dumps(metrics)
    agg.completed_tasks = len(parsed)
    agg.aggregation_version += 1
    agg.aggregation_status = (
        AggregationStatus.COMPLETED
        if len(parsed) == agg.total_tasks
        else AggregationStatus.IN_PROGRESS
    )
    agg.checkpoint_json = json.dumps({
        "last_task_count": len(parsed),
        "checkpoint_at": datetime.now(timezone.utc).isoformat(),
    })

    await db.commit()
    logger.info(
        f"Aggregated job {job_id}: {len(parsed)}/{agg.total_tasks} tasks, "
        f"version={agg.aggregation_version}"
    )
    return metrics


def _aggregate_monte_carlo(parsed: List[Dict]) -> Dict[str, Any]:
    """Aggregate Monte Carlo simulation results with correct statistics.

    Uses combined variance formula for merging independent simulations:
    Combined variance = (Σ n_i * (var_i + (mean_i - grand_mean)²)) / N_total
    """
    total_samples = 0
    total_hits = 0

    # Collect per-chunk estimates for variance calculation
    chunk_estimates = []
    chunk_sizes = []

    for r in parsed:
        n = r.get("total_points", 0)
        hits = r.get("inside_circle", 0)
        if n > 0:
            total_samples += n
            total_hits += hits
            estimate = 4.0 * hits / n
            chunk_estimates.append(estimate)
            chunk_sizes.append(n)

    if total_samples == 0:
        return {"probability_estimate": 0, "total_samples": 0}

    # Grand estimate
    grand_estimate = 4.0 * total_hits / total_samples

    # Combined variance using parallel algorithm
    # For Monte Carlo Pi estimation: var(estimator) = 4² * p(1-p) / n
    # where p = probability point falls in circle
    p_hat = total_hits / total_samples
    estimator_variance = 16.0 * p_hat * (1.0 - p_hat) / total_samples

    # Standard error and confidence intervals
    std_error = math.sqrt(estimator_variance) if estimator_variance > 0 else 0
    ci_95_lower = grand_estimate - 1.96 * std_error
    ci_95_upper = grand_estimate + 1.96 * std_error
    ci_99_lower = grand_estimate - 2.576 * std_error
    ci_99_upper = grand_estimate + 2.576 * std_error

    # Inter-chunk variance (consistency check)
    if len(chunk_estimates) > 1:
        mean_of_estimates = sum(chunk_estimates) / len(chunk_estimates)
        inter_variance = sum(
            (e - mean_of_estimates) ** 2 for e in chunk_estimates
        ) / (len(chunk_estimates) - 1)
    else:
        inter_variance = 0

    return {
        "probability_estimate": round(grand_estimate, 10),
        "total_samples": total_samples,
        "total_hits": total_hits,
        "estimator_variance": round(estimator_variance, 12),
        "standard_error": round(std_error, 10),
        "confidence_interval_95": {
            "lower": round(ci_95_lower, 10),
            "upper": round(ci_95_upper, 10),
        },
        "confidence_interval_99": {
            "lower": round(ci_99_lower, 10),
            "upper": round(ci_99_upper, 10),
        },
        "inter_chunk_variance": round(inter_variance, 12),
        "chunk_count": len(parsed),
    }


def _aggregate_dataset_stats(parsed: List[Dict]) -> Dict[str, Any]:
    """Aggregate distributed dataset statistics using correct parallel formulas.

    Uses Chan's parallel algorithm for combining variance:
    Combined mean: μ = (Σ n_i * μ_i) / N
    Combined variance: σ² = (Σ (n_i * σ²_i + n_i * (μ_i - μ)²)) / N

    This is mathematically correct unlike naive averaging of averages.
    """
    if not parsed:
        return {}

    columns = parsed[0].get("column_count", 0)
    if columns == 0:
        return {"error": "no_columns"}

    total_rows = 0
    # Per-column accumulators
    global_sums = [0.0] * columns
    global_mins = [float("inf")] * columns
    global_maxs = [float("-inf")] * columns

    # For parallel variance: collect (n, mean, variance) per chunk per column
    chunk_stats: List[Dict] = []

    for r in parsed:
        n = r.get("row_count", 0)
        if n == 0:
            continue
        total_rows += n

        sums = r.get("sums", [])
        mins = r.get("mins", [])
        maxs = r.get("maxs", [])
        avgs = r.get("averages", [])
        variances = r.get("variances", [])

        stats_entry = {"n": n, "means": [], "variances": []}

        for col in range(columns):
            if col < len(sums):
                global_sums[col] += sums[col]
            if col < len(mins) and mins[col] < global_mins[col]:
                global_mins[col] = mins[col]
            if col < len(maxs) and maxs[col] > global_maxs[col]:
                global_maxs[col] = maxs[col]

            mean_val = avgs[col] if col < len(avgs) else 0.0
            var_val = variances[col] if col < len(variances) else 0.0
            stats_entry["means"].append(mean_val)
            stats_entry["variances"].append(var_val)

        chunk_stats.append(stats_entry)

    if total_rows == 0:
        return {"total_rows": 0, "columns": columns}

    # Compute global means
    global_means = [s / total_rows for s in global_sums]

    # Compute global variances using Chan's parallel algorithm
    global_variances = [0.0] * columns
    for col in range(columns):
        combined_var = 0.0
        for cs in chunk_stats:
            n_i = cs["n"]
            var_i = cs["variances"][col] if col < len(cs["variances"]) else 0.0
            mean_i = cs["means"][col] if col < len(cs["means"]) else 0.0
            delta = mean_i - global_means[col]
            # Chan's formula: weighted sum of within-chunk + between-chunk variance
            combined_var += n_i * var_i + n_i * delta * delta
        global_variances[col] = combined_var / total_rows if total_rows > 0 else 0.0

    # Standard deviations
    global_stddevs = [math.sqrt(max(v, 0)) for v in global_variances]

    # Column names from first chunk if available
    col_names = parsed[0].get("column_names", [f"col_{i}" for i in range(columns)])

    return {
        "total_rows": total_rows,
        "columns": columns,
        "column_names": col_names,
        "global_sums": [round(s, 6) for s in global_sums],
        "global_means": [round(m, 6) for m in global_means],
        "global_variances": [round(v, 6) for v in global_variances],
        "global_stddevs": [round(s, 6) for s in global_stddevs],
        "global_mins": [round(m, 6) if m != float("inf") else None for m in global_mins],
        "global_maxs": [round(m, 6) if m != float("-inf") else None for m in global_maxs],
    }


def _aggregate_matrix(parsed: List[Dict]) -> Dict[str, Any]:
    """Aggregate distributed matrix computation results.

    Reconstructs block outputs and computes global statistics.
    """
    total_rows_processed = 0
    total_block_sum = 0.0
    all_row_sums = []
    block_details = []

    for r in parsed:
        rows = r.get("rows_processed", 0)
        total_rows_processed += rows
        block_sum = r.get("block_sum", 0)
        total_block_sum += block_sum
        row_sums = r.get("row_sums", [])
        all_row_sums.extend(row_sums)

        block_details.append({
            "range": [r.get("range_start", 0), r.get("range_end", 0)],
            "block_sum": block_sum,
            "block_mean": r.get("block_mean", 0),
            "rows": rows,
        })

    # Overall statistics
    global_mean = total_block_sum / total_rows_processed if total_rows_processed > 0 else 0

    # Row-level variance
    row_variance = 0.0
    if all_row_sums:
        row_mean = sum(all_row_sums) / len(all_row_sums)
        row_variance = sum((rs - row_mean) ** 2 for rs in all_row_sums) / len(all_row_sums)

    return {
        "total_rows_processed": total_rows_processed,
        "total_block_sum": round(total_block_sum, 6),
        "global_mean": round(global_mean, 6),
        "row_sum_variance": round(row_variance, 6),
        "row_sum_stddev": round(math.sqrt(max(row_variance, 0)), 6),
        "block_count": len(parsed),
        "blocks": block_details,
    }


async def get_aggregation(db: AsyncSession, job_id: UUID) -> Optional[Dict]:
    """Get the latest aggregated result for a job."""
    agg_q = await db.execute(
        select(AggregatedResult).where(AggregatedResult.job_id == job_id)
    )
    agg = agg_q.scalar_one_or_none()
    if not agg:
        return None
    return {
        "job_id": str(job_id),
        "aggregation_version": agg.aggregation_version,
        "metrics": json.loads(agg.metrics_json),
        "completed_tasks": agg.completed_tasks,
        "total_tasks": agg.total_tasks,
        "aggregation_status": agg.aggregation_status.value,
        "updated_at": agg.updated_at.isoformat() if agg.updated_at else None,
    }
