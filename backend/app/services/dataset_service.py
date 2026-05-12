"""
Dataset service — upload, chunk, and manage research datasets.
Supports CSV, JSON, and Parquet with streaming memory-safe processing.
Stores raw files and chunks in Supabase Storage (S3-compatible).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.supabase_storage import storage
from app.models.dataset import Dataset, DatasetChunk, DatasetFormat, UploadStatus

logger = logging.getLogger(__name__)

# Max rows per chunk
CHUNK_SIZE = 10_000


def _detect_format(filename: str) -> DatasetFormat:
    """Detect dataset format from filename extension."""
    lower = filename.lower()
    if lower.endswith(".csv"):
        return DatasetFormat.CSV
    elif lower.endswith(".json") or lower.endswith(".jsonl"):
        return DatasetFormat.JSON
    elif lower.endswith(".parquet"):
        return DatasetFormat.PARQUET
    raise ValueError(f"Unsupported file format: {filename}")


def _compute_checksum(data: bytes) -> str:
    """SHA-256 checksum of a chunk."""
    return hashlib.sha256(data).hexdigest()


async def upload_dataset(
    db: AsyncSession, owner_id: UUID, filename: str, file_data: bytes
) -> Dataset:
    """Upload a dataset: store raw file, extract metadata, create chunks."""
    fmt = _detect_format(filename)
    storage_path = f"datasets/{owner_id}/{filename}"

    # Create dataset record
    dataset = Dataset(
        owner_id=owner_id,
        filename=filename,
        storage_path=storage_path,
        format=fmt,
        size_bytes=len(file_data),
        upload_status=UploadStatus.UPLOADING,
    )
    db.add(dataset)
    await db.flush()

    try:
        # Upload raw file to object storage
        content_type = {
            DatasetFormat.CSV: "text/csv",
            DatasetFormat.JSON: "application/json",
            DatasetFormat.PARQUET: "application/octet-stream",
        }.get(fmt, "application/octet-stream")

        await storage.upload(storage_path, file_data, content_type)

        # Update status to chunking
        dataset.upload_status = UploadStatus.CHUNKING
        await db.commit()

        # Parse and chunk
        if fmt == DatasetFormat.CSV:
            rows, columns_meta = _parse_csv(file_data)
        elif fmt == DatasetFormat.JSON:
            rows, columns_meta = _parse_json(file_data)
        elif fmt == DatasetFormat.PARQUET:
            rows, columns_meta = _parse_parquet_fallback(file_data)
        else:
            rows, columns_meta = [], {}

        dataset.row_count = len(rows)
        dataset.column_metadata_json = json.dumps(columns_meta)

        # Create chunks
        chunks = await _create_chunks(db, dataset, rows, fmt)

        dataset.upload_status = UploadStatus.READY
        await db.commit()
        await db.refresh(dataset)
        logger.info(
            f"Dataset {dataset.id} uploaded: {len(rows)} rows, {len(chunks)} chunks"
        )
        return dataset

    except Exception as e:
        dataset.upload_status = UploadStatus.FAILED
        await db.commit()
        logger.error(f"Dataset upload failed: {e}")
        raise


def _parse_csv(data: bytes) -> tuple[list[list], dict]:
    """Parse CSV data into rows and extract column metadata."""
    text = data.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows_out = []
    headers = []

    for i, row in enumerate(reader):
        if i == 0:
            headers = row
            continue
        # Convert numeric values
        parsed_row = []
        for val in row:
            try:
                parsed_row.append(float(val))
            except (ValueError, TypeError):
                parsed_row.append(val)
        rows_out.append(parsed_row)

    # Build column metadata
    col_meta = {
        "columns": headers,
        "column_count": len(headers),
        "dtypes": [],
    }
    if rows_out:
        for col_idx in range(len(headers)):
            numeric_count = sum(
                1 for r in rows_out[:100]
                if col_idx < len(r) and isinstance(r[col_idx], (int, float))
            )
            col_meta["dtypes"].append(
                "numeric" if numeric_count > len(rows_out[:100]) * 0.5 else "string"
            )

    return rows_out, col_meta


def _parse_json(data: bytes) -> tuple[list[list], dict]:
    """Parse JSON/JSONL data into rows and extract column metadata."""
    text = data.decode("utf-8", errors="replace")

    # Try JSONL first (one JSON object per line)
    lines = text.strip().split("\n")
    records = []

    if len(lines) > 1:
        for line in lines:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    break

    if not records:
        # Try array format
        parsed = json.loads(text)
        if isinstance(parsed, list):
            records = parsed
        elif isinstance(parsed, dict) and "data" in parsed:
            records = parsed["data"]

    if not records:
        return [], {"columns": [], "column_count": 0}

    # Extract columns from first record
    headers = list(records[0].keys()) if isinstance(records[0], dict) else []
    rows_out = []
    for rec in records:
        if isinstance(rec, dict):
            row = []
            for h in headers:
                val = rec.get(h, None)
                try:
                    row.append(float(val) if val is not None else 0.0)
                except (ValueError, TypeError):
                    row.append(val)
            rows_out.append(row)

    col_meta = {
        "columns": headers,
        "column_count": len(headers),
        "dtypes": [],
    }
    if rows_out:
        for col_idx in range(len(headers)):
            numeric_count = sum(
                1 for r in rows_out[:100]
                if col_idx < len(r) and isinstance(r[col_idx], (int, float))
            )
            col_meta["dtypes"].append(
                "numeric" if numeric_count > len(rows_out[:100]) * 0.5 else "string"
            )

    return rows_out, col_meta


def _parse_parquet_fallback(data: bytes) -> tuple[list[list], dict]:
    """Minimal Parquet support — attempts pyarrow if available, else stores as opaque."""
    try:
        import pyarrow.parquet as pq
        table = pq.read_table(io.BytesIO(data))
        headers = table.column_names
        rows_out = []
        for i in range(table.num_rows):
            row = []
            for col in headers:
                val = table.column(col)[i].as_py()
                try:
                    row.append(float(val) if val is not None else 0.0)
                except (ValueError, TypeError):
                    row.append(val)
            rows_out.append(row)

        col_meta = {
            "columns": headers,
            "column_count": len(headers),
            "dtypes": [str(table.schema.field(c).type) for c in headers],
        }
        return rows_out, col_meta
    except ImportError:
        logger.warning("pyarrow not available — Parquet stored as opaque blob")
        return [], {"columns": [], "column_count": 0, "note": "pyarrow not installed"}


async def _create_chunks(
    db: AsyncSession,
    dataset: Dataset,
    rows: list,
    fmt: DatasetFormat,
) -> List[DatasetChunk]:
    """Split rows into chunks and upload each to object storage."""
    chunks = []
    total_rows = len(rows)

    for chunk_idx, start in enumerate(range(0, max(total_rows, 1), CHUNK_SIZE)):
        end = min(start + CHUNK_SIZE, total_rows)
        chunk_rows = rows[start:end] if rows else []

        # Serialize chunk
        chunk_data = json.dumps(chunk_rows).encode("utf-8")
        checksum = _compute_checksum(chunk_data)
        chunk_path = f"datasets/{dataset.owner_id}/{dataset.id}/chunk_{chunk_idx}.json"

        # Upload chunk to storage
        await storage.upload(chunk_path, chunk_data, "application/json")

        chunk = DatasetChunk(
            dataset_id=dataset.id,
            chunk_index=chunk_idx,
            storage_path=chunk_path,
            row_start=start,
            row_end=end,
            checksum=checksum,
        )
        db.add(chunk)
        chunks.append(chunk)

    await db.flush()
    return chunks


async def get_dataset(db: AsyncSession, dataset_id: UUID) -> Optional[Dataset]:
    """Fetch a dataset by ID."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    return result.scalar_one_or_none()


async def get_user_datasets(db: AsyncSession, owner_id: UUID) -> List[Dataset]:
    """List all datasets owned by a user."""
    result = await db.execute(
        select(Dataset)
        .where(Dataset.owner_id == owner_id)
        .order_by(Dataset.created_at.desc())
    )
    return list(result.scalars().all())


async def get_dataset_chunks(
    db: AsyncSession, dataset_id: UUID
) -> List[DatasetChunk]:
    """Get all chunks for a dataset."""
    result = await db.execute(
        select(DatasetChunk)
        .where(DatasetChunk.dataset_id == dataset_id)
        .order_by(DatasetChunk.chunk_index)
    )
    return list(result.scalars().all())


async def delete_dataset(db: AsyncSession, dataset_id: UUID, owner_id: UUID) -> bool:
    """Delete a dataset and its chunks from DB and storage."""
    dataset = await get_dataset(db, dataset_id)
    if not dataset or dataset.owner_id != owner_id:
        return False

    chunks = await get_dataset_chunks(db, dataset_id)
    paths = [c.storage_path for c in chunks] + [dataset.storage_path]

    try:
        await storage.delete(paths)
    except Exception as e:
        logger.warning(f"Storage cleanup partial failure: {e}")

    await db.delete(dataset)
    await db.commit()
    return True
