"""Dataset schemas for upload, metadata, and chunk info."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class DatasetUploadResponse(BaseModel):
    id: UUID
    filename: str
    format: str
    upload_status: str
    row_count: int
    size_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True


class DatasetChunkInfo(BaseModel):
    id: UUID
    chunk_index: int
    row_start: int
    row_end: int
    checksum: str


class DatasetDetail(BaseModel):
    id: UUID
    filename: str
    format: str
    row_count: int
    size_bytes: int
    upload_status: str
    column_metadata: dict
    chunks: List[DatasetChunkInfo]
    created_at: datetime


class DatasetListItem(BaseModel):
    id: UUID
    filename: str
    format: str
    row_count: int
    size_bytes: int
    upload_status: str
    created_at: datetime

    class Config:
        from_attributes = True
