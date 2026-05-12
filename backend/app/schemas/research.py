"""Research output schemas for aggregated results, reports, and downloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel


class AggregatedResultResponse(BaseModel):
    job_id: UUID
    aggregation_version: int
    metrics: Dict[str, Any]
    completed_tasks: int
    total_tasks: int
    aggregation_status: str
    updated_at: datetime


class ResearchReportResponse(BaseModel):
    job_id: UUID
    job_name: str
    template_type: str
    summary: Dict[str, Any]
    report_url: Optional[str] = None
    visualization_url: Optional[str] = None
    generated_at: datetime


class DownloadResponse(BaseModel):
    download_url: str
    format: str
    size_bytes: int
    filename: str


class MCPActionResponse(BaseModel):
    id: UUID
    action_type: str
    target_job_id: Optional[UUID] = None
    target_user_id: Optional[UUID] = None
    parameters: Dict[str, Any]
    status: str
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class CampaignResponse(BaseModel):
    id: UUID
    campaign_type: str
    multiplier: float
    target_job_id: Optional[UUID] = None
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class MCPStatusResponse(BaseModel):
    active_workers: int
    under_supplied_jobs: int
    active_campaigns: int
    recent_actions: list
    avg_multiplier: float
    total_mcp_actions: int
