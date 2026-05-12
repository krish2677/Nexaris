"""
Dataset and DatasetChunk models — tracks uploaded research datasets
and their partitioned chunks stored in object storage.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class DatasetFormat(str, enum.Enum):
    CSV = "csv"
    JSON = "json"
    PARQUET = "parquet"


class UploadStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    CHUNKING = "chunking"
    READY = "ready"
    FAILED = "failed"


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    filename = Column(String(512), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    format = Column(SQLEnum(DatasetFormat), nullable=False)
    row_count = Column(Integer, default=0)
    column_metadata_json = Column(Text, default="{}")
    upload_status = Column(SQLEnum(UploadStatus), default=UploadStatus.PENDING)
    size_bytes = Column(Integer, default=0)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    owner = relationship("User", back_populates="datasets")
    chunks = relationship(
        "DatasetChunk", back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetChunk(Base):
    __tablename__ = "dataset_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False
    )
    chunk_index = Column(Integer, nullable=False)
    storage_path = Column(String(1024), nullable=False)
    row_start = Column(Integer, nullable=False)
    row_end = Column(Integer, nullable=False)
    checksum = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    dataset = relationship("Dataset", back_populates="chunks")
