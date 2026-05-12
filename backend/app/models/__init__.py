"""
Central model registry — import all models here so Alembic and
init_db() can discover them via Base.metadata.
"""

from app.models.user import User
from app.models.device import Device, DeviceStatus, DeviceType
from app.models.job import Job, JobStatus, TemplateType, ValidationStrategy
from app.models.task import Task, TaskStatus
from app.models.task_result import TaskResult, ValidationStatus
from app.models.event import Event
from app.models.leaderboard import LeaderboardEntry
from app.models.dataset import Dataset, DatasetChunk, DatasetFormat, UploadStatus
from app.models.aggregated_result import AggregatedResult, AggregationStatus
from app.models.researcher_output import ResearcherOutput
from app.models.mcp_action import MCPAction, RewardCampaign, ActionStatus, CampaignStatus
from app.models.user_retention import UserRetentionState
from app.models.treasury import TreasuryLedger, TreasuryTransaction, AllocationCategory
from app.models.campaign import (
    IncentiveCampaign, CampaignType, CampaignPriority, CampaignLifecycle,
)
from app.models.competition import CampaignParticipant, WalletDeposit, RewardDistribution

__all__ = [
    "User",
    "Device", "DeviceStatus", "DeviceType",
    "Job", "JobStatus", "TemplateType", "ValidationStrategy",
    "Task", "TaskStatus",
    "TaskResult", "ValidationStatus",
    "Event",
    "LeaderboardEntry",
    "Dataset", "DatasetChunk", "DatasetFormat", "UploadStatus",
    "AggregatedResult", "AggregationStatus",
    "ResearcherOutput",
    "MCPAction", "RewardCampaign", "ActionStatus", "CampaignStatus",
    "UserRetentionState",
    "TreasuryLedger", "TreasuryTransaction", "AllocationCategory",
    "IncentiveCampaign", "CampaignType", "CampaignPriority", "CampaignLifecycle",
    "CampaignParticipant", "WalletDeposit", "RewardDistribution",
]
