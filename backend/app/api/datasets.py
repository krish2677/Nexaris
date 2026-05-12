"""
Datasets API — upload, list, inspect, and manage research datasets.
"""

from __future__ import annotations

import json
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dataset import DatasetUploadResponse, DatasetDetail, DatasetListItem
from app.services.dataset_service import (
    upload_dataset,
    get_dataset,
    get_user_datasets,
    get_dataset_chunks,
    delete_dataset,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a research dataset (CSV, JSON, or Parquet).
    The dataset is automatically chunked and stored in object storage."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    # Validate file extension
    allowed_extensions = {".csv", ".json", ".jsonl", ".parquet"}
    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Allowed: {', '.join(allowed_extensions)}",
        )

    # Read file data (with size limit)
    max_size = 100 * 1024 * 1024  # 100MB
    data = await file.read()
    if len(data) > max_size:
        raise HTTPException(status_code=413, detail="File too large (max 100MB)")

    try:
        dataset = await upload_dataset(db, user.id, file.filename, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    return dataset


@router.get("/", response_model=List[DatasetListItem])
async def list_datasets(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all datasets owned by the current user."""
    datasets = await get_user_datasets(db, user.id)
    return datasets


@router.get("/{dataset_id}")
async def dataset_detail(
    dataset_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed metadata and chunk info for a dataset."""
    did = UUID(dataset_id)
    dataset = await get_dataset(db, did)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your dataset")

    chunks = await get_dataset_chunks(db, did)
    col_meta = json.loads(dataset.column_metadata_json) if dataset.column_metadata_json else {}

    return {
        "id": str(dataset.id),
        "filename": dataset.filename,
        "format": dataset.format.value,
        "row_count": dataset.row_count,
        "size_bytes": dataset.size_bytes,
        "upload_status": dataset.upload_status.value,
        "column_metadata": col_meta,
        "chunks": [
            {
                "id": str(c.id),
                "chunk_index": c.chunk_index,
                "row_start": c.row_start,
                "row_end": c.row_end,
                "checksum": c.checksum,
            }
            for c in chunks
        ],
        "created_at": dataset.created_at.isoformat(),
    }


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_dataset(
    dataset_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a dataset and its chunks."""
    did = UUID(dataset_id)
    deleted = await delete_dataset(db, did, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found or not yours")
