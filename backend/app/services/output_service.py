"""
Output service — generates research reports, CSV/JSON exports,
and downloadable archives from aggregated results.
Stores outputs in object storage and tracks via researcher_outputs table.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.supabase_storage import storage
from app.models.aggregated_result import AggregatedResult
from app.models.job import Job
from app.models.researcher_output import ResearcherOutput
from app.services.aggregation_service import aggregate_job, get_aggregation

logger = logging.getLogger(__name__)


async def generate_report(db: AsyncSession, job_id: UUID) -> Dict[str, Any]:
    """Generate a research report for a completed job."""
    job_q = await db.execute(select(Job).where(Job.id == job_id))
    job = job_q.scalar_one_or_none()
    if not job:
        return {"error": "Job not found"}

    # Get or compute aggregation
    agg_data = await get_aggregation(db, job_id)
    if not agg_data:
        agg_data = {"metrics": await aggregate_job(db, job_id)}

    metrics = agg_data.get("metrics", {})
    template = job.template_type.value

    # Generate report content
    report = {
        "job_id": str(job_id),
        "job_name": job.name,
        "template_type": template,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": job.status.value,
        "parameters": json.loads(job.parameters_json),
        "results": metrics,
    }

    # Template-specific report sections
    if template == "monte_carlo":
        report["analysis"] = _monte_carlo_analysis(metrics)
    elif template == "dataset_stats":
        report["analysis"] = _dataset_stats_analysis(metrics)
    elif template == "matrix_compute":
        report["analysis"] = _matrix_analysis(metrics)

    # Store report in object storage
    report_json = json.dumps(report, indent=2).encode("utf-8")
    report_path = f"outputs/{job.owner_id}/{job_id}/report.json"

    try:
        await storage.upload(report_path, report_json, "application/json")
    except Exception as e:
        logger.warning(f"Report upload failed: {e}")
        report_path = None

    # Upsert researcher output record
    out_q = await db.execute(
        select(ResearcherOutput).where(ResearcherOutput.job_id == job_id)
    )
    output = out_q.scalar_one_or_none()
    if output:
        output.report_path = report_path
        output.summary_json = json.dumps(report)
        output.generated_at = datetime.now(timezone.utc)
    else:
        output = ResearcherOutput(
            job_id=job_id,
            report_path=report_path,
            summary_json=json.dumps(report),
        )
        db.add(output)

    await db.commit()
    return report


async def generate_export(
    db: AsyncSession, job_id: UUID, fmt: str = "json"
) -> tuple[bytes, str, str]:
    """Generate a downloadable export in the specified format.

    Returns: (data_bytes, content_type, filename)
    """
    job_q = await db.execute(select(Job).where(Job.id == job_id))
    job = job_q.scalar_one_or_none()
    if not job:
        raise ValueError("Job not found")

    agg_data = await get_aggregation(db, job_id)
    if not agg_data:
        metrics = await aggregate_job(db, job_id)
    else:
        metrics = agg_data.get("metrics", {})

    template = job.template_type.value
    base_name = f"desci_output_{job.name.replace(' ', '_')}_{job_id}"

    if fmt == "json":
        export_data = {
            "job_id": str(job_id),
            "job_name": job.name,
            "template_type": template,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "results": metrics,
        }
        data = json.dumps(export_data, indent=2).encode("utf-8")
        return data, "application/json", f"{base_name}.json"

    elif fmt == "csv":
        data = _metrics_to_csv(metrics, template)
        return data, "text/csv", f"{base_name}.csv"

    elif fmt == "zip":
        data = await _create_zip_archive(job, metrics, template, base_name)
        return data, "application/zip", f"{base_name}.zip"

    else:
        raise ValueError(f"Unsupported export format: {fmt}")


def _metrics_to_csv(metrics: Dict, template: str) -> bytes:
    """Convert aggregated metrics to CSV bytes."""
    output = io.StringIO()
    writer = csv.writer(output)

    if template == "monte_carlo":
        writer.writerow(["metric", "value"])
        writer.writerow(["probability_estimate", metrics.get("probability_estimate", "")])
        writer.writerow(["total_samples", metrics.get("total_samples", "")])
        writer.writerow(["total_hits", metrics.get("total_hits", "")])
        writer.writerow(["standard_error", metrics.get("standard_error", "")])
        writer.writerow(["estimator_variance", metrics.get("estimator_variance", "")])
        ci95 = metrics.get("confidence_interval_95", {})
        writer.writerow(["ci_95_lower", ci95.get("lower", "")])
        writer.writerow(["ci_95_upper", ci95.get("upper", "")])

    elif template == "dataset_stats":
        col_names = metrics.get("column_names", [])
        means = metrics.get("global_means", [])
        stddevs = metrics.get("global_stddevs", [])
        mins = metrics.get("global_mins", [])
        maxs = metrics.get("global_maxs", [])
        sums = metrics.get("global_sums", [])
        variances = metrics.get("global_variances", [])

        writer.writerow(["column", "mean", "stddev", "variance", "min", "max", "sum"])
        for i, name in enumerate(col_names):
            writer.writerow([
                name,
                means[i] if i < len(means) else "",
                stddevs[i] if i < len(stddevs) else "",
                variances[i] if i < len(variances) else "",
                mins[i] if i < len(mins) else "",
                maxs[i] if i < len(maxs) else "",
                sums[i] if i < len(sums) else "",
            ])

    elif template == "matrix_compute":
        writer.writerow(["metric", "value"])
        writer.writerow(["total_rows_processed", metrics.get("total_rows_processed", "")])
        writer.writerow(["total_block_sum", metrics.get("total_block_sum", "")])
        writer.writerow(["global_mean", metrics.get("global_mean", "")])
        writer.writerow(["row_sum_variance", metrics.get("row_sum_variance", "")])
        writer.writerow(["row_sum_stddev", metrics.get("row_sum_stddev", "")])

        blocks = metrics.get("blocks", [])
        if blocks:
            writer.writerow([])
            writer.writerow(["block_range_start", "block_range_end", "block_sum", "block_mean", "rows"])
            for b in blocks:
                r = b.get("range", [0, 0])
                writer.writerow([r[0], r[1], b.get("block_sum", ""), b.get("block_mean", ""), b.get("rows", "")])

    return output.getvalue().encode("utf-8")


async def _create_zip_archive(
    job: Job, metrics: Dict, template: str, base_name: str
) -> bytes:
    """Create a ZIP archive with JSON report + CSV export."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # JSON report
        report = {
            "job_id": str(job.id),
            "job_name": job.name,
            "template_type": template,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "results": metrics,
        }
        zf.writestr(f"{base_name}/report.json", json.dumps(report, indent=2))

        # CSV data
        csv_data = _metrics_to_csv(metrics, template)
        zf.writestr(f"{base_name}/data.csv", csv_data.decode("utf-8"))

        # README
        readme = (
            f"# DeSci Compute Output\n\n"
            f"Job: {job.name}\n"
            f"Template: {template}\n"
            f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
            f"## Files\n"
            f"- report.json — Full computation report with metrics\n"
            f"- data.csv — Tabular results for analysis\n"
        )
        zf.writestr(f"{base_name}/README.md", readme)

    return buf.getvalue()


def _monte_carlo_analysis(metrics: Dict) -> Dict:
    """Generate Monte Carlo analysis summary."""
    estimate = metrics.get("probability_estimate", 0)
    se = metrics.get("standard_error", 0)
    samples = metrics.get("total_samples", 0)

    return {
        "type": "monte_carlo_simulation",
        "conclusion": f"Pi estimated at {estimate:.8f} from {samples:,} samples",
        "precision": f"Standard error: {se:.2e}",
        "convergence": "good" if se < 0.001 else "moderate" if se < 0.01 else "needs_more_samples",
        "relative_error": abs(estimate - 3.14159265358979) / 3.14159265358979 if estimate else 0,
    }


def _dataset_stats_analysis(metrics: Dict) -> Dict:
    """Generate dataset statistics analysis summary."""
    total_rows = metrics.get("total_rows", 0)
    columns = metrics.get("columns", 0)
    col_names = metrics.get("column_names", [])
    means = metrics.get("global_means", [])
    stddevs = metrics.get("global_stddevs", [])

    column_summaries = []
    for i, name in enumerate(col_names):
        mean = means[i] if i < len(means) else 0
        std = stddevs[i] if i < len(stddevs) else 0
        cv = std / abs(mean) if mean != 0 else 0
        column_summaries.append({
            "name": name,
            "mean": round(mean, 4),
            "stddev": round(std, 4),
            "coefficient_of_variation": round(cv, 4),
        })

    return {
        "type": "dataset_statistics",
        "total_rows_analyzed": total_rows,
        "columns_analyzed": columns,
        "column_summaries": column_summaries,
    }


def _matrix_analysis(metrics: Dict) -> Dict:
    """Generate matrix computation analysis summary."""
    return {
        "type": "matrix_computation",
        "total_rows_processed": metrics.get("total_rows_processed", 0),
        "result_magnitude": abs(metrics.get("total_block_sum", 0)),
        "row_distribution_stddev": metrics.get("row_sum_stddev", 0),
    }
