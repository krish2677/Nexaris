"""
ResearcherOutput model — generated reports, visualizations, and export archives.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ResearcherOutput(Base):
    __tablename__ = "researcher_outputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True
    )
    report_path = Column(String(1024), nullable=True)
    visualization_path = Column(String(1024), nullable=True)
    export_path = Column(String(1024), nullable=True)
    summary_json = Column(Text, default="{}")
    generated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
