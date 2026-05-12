"""Platform statistics schema."""

from pydantic import BaseModel


class PlatformStats(BaseModel):
    total_users: int
    active_devices: int
    total_jobs: int
    active_jobs: int
    completed_tasks: int
    pending_tasks: int
    total_compute_hours: float
    avg_reward_multiplier: float
