"""
MCP Rule Engine — deterministic backend rules that handle 90% of decisions.
Only escalates complex cases to GPT-4o via OpenRouter.

Handles locally (no LLM):
1. User inactive > 48h → comeback gift
2. active_workers < required → increase multiplier
3. First validated task → referral reward
4. Streak milestone → gift reward
5. Leaderboard threshold → badge/reward
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.device import Device, DeviceStatus
from app.models.event import Event
from app.models.job import Job, JobStatus
from app.models.mcp_action import MCPAction, RewardCampaign, CampaignStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.user_retention import UserRetentionState

logger = logging.getLogger(__name__)

# Cooldown tracking (in-memory, resets on restart — acceptable for rule engine)
_action_cooldowns: Dict[str, float] = {}
COOLDOWN_SECONDS = 300  # 5 min cooldown per action type per target


class RuleEngine:
    """Deterministic rule engine — handles simple MCP decisions locally."""

    async def evaluate(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Run all rules and return list of actions taken."""
        actions = []

        actions.extend(await self._rule_worker_shortage(db))
        actions.extend(await self._rule_inactive_users(db))
        actions.extend(await self._rule_streak_milestones(db))
        actions.extend(await self._rule_expire_campaigns(db))

        return actions

    def should_escalate_to_llm(self, db_state: Dict) -> bool:
        """Determine if the current state is complex enough to need GPT-4o."""
        under_supplied = db_state.get("under_supplied_count", 0)
        inactive = db_state.get("inactive_users_48h", 0)
        active_campaigns = db_state.get("active_campaigns", 0)

        # Escalate when multiple competing conditions exist
        if under_supplied >= 3 and inactive >= 10:
            return True
        if under_supplied >= 5:
            return True
        if db_state.get("leaderboard_activity_drop", 0) > 0.5:
            return True

        return False

    # ── RULE 1: Worker shortage → boost reward multiplier ──
    async def _rule_worker_shortage(self, db: AsyncSession) -> List[Dict]:
        """Increase multiplier for under-supplied jobs."""
        actions = []
        stmt = select(Job).where(
            Job.status == JobStatus.ACTIVE,
            Job.active_workers < Job.required_workers,
        )
        result = await db.execute(stmt)
        under_supplied = list(result.scalars().all())

        for job in under_supplied:
            if _is_on_cooldown(f"shortage_{job.id}"):
                continue

            # Calculate boost based on supply deficit
            deficit_ratio = 1 - (job.active_workers / max(job.required_workers, 1))
            boost = 1 + (deficit_ratio * 0.5)  # 1.0 to 1.5x boost
            new_mult = min(job.reward_multiplier * boost, 10.0)

            if abs(new_mult - job.reward_multiplier) > 0.01:
                old_mult = job.reward_multiplier
                job.reward_multiplier = round(new_mult, 2)
                _set_cooldown(f"shortage_{job.id}")

                action = MCPAction(
                    action_type="boost_rewards",
                    target_job_id=job.id,
                    parameters_json=json.dumps({
                        "old_multiplier": old_mult,
                        "new_multiplier": job.reward_multiplier,
                        "deficit_ratio": round(deficit_ratio, 2),
                    }),
                    status="executed",
                    source="rule_engine",
                )
                db.add(action)
                actions.append({
                    "type": "boost_rewards",
                    "job_id": str(job.id),
                    "multiplier": job.reward_multiplier,
                })
                logger.info(
                    f"MCP Rule: boosted job {job.id} multiplier "
                    f"{old_mult} → {job.reward_multiplier}"
                )

        if actions:
            await db.commit()

        return actions

    # ── RULE 2: Inactive user → re-engagement ──
    async def _rule_inactive_users(self, db: AsyncSession) -> List[Dict]:
        """Emit re-engagement events and trigger comeback gifts."""
        actions = []
        cutoff = datetime.now(timezone.utc) - timedelta(
            hours=settings.INACTIVITY_THRESHOLD_HOURS
        )
        stmt = select(User).where(
            User.is_active == True,  # noqa: E712
            User.last_active_at < cutoff,
        )
        result = await db.execute(stmt)
        inactive = list(result.scalars().all())

        for user in inactive:
            if _is_on_cooldown(f"inactive_{user.id}"):
                continue

            # Check if we already emitted recently
            recent_q = await db.execute(
                select(Event).where(
                    Event.user_id == user.id,
                    Event.event_name == "user_inactive",
                    Event.created_at > cutoff,
                )
            )
            if recent_q.scalar_one_or_none():
                continue

            _set_cooldown(f"inactive_{user.id}")

            event = Event(
                user_id=user.id,
                event_name="user_inactive",
                metadata_json=json.dumps({
                    "last_active": user.last_active_at.isoformat(),
                    "hours_inactive": (
                        datetime.now(timezone.utc) - user.last_active_at
                    ).total_seconds() / 3600,
                }),
            )
            db.add(event)

            action = MCPAction(
                action_type="send_reengagement_gift",
                target_user_id=user.id,
                parameters_json=json.dumps({
                    "hours_inactive": round(
                        (datetime.now(timezone.utc) - user.last_active_at).total_seconds() / 3600,
                        1,
                    )
                }),
                status="executed",
                source="rule_engine",
            )
            db.add(action)
            actions.append({
                "type": "send_reengagement_gift",
                "user_id": str(user.id),
            })

        if actions:
            await db.commit()
            logger.info(f"MCP Rule: re-engaged {len(actions)} inactive users")

        return actions

    # ── RULE 3: Streak milestones ──
    async def _rule_streak_milestones(self, db: AsyncSession) -> List[Dict]:
        """Reward users who hit streak milestones."""
        actions = []
        stmt = select(UserRetentionState).where(
            UserRetentionState.streak_days.in_([7, 14, 30, 60, 90])
        )
        result = await db.execute(stmt)
        milestone_users = list(result.scalars().all())

        for state in milestone_users:
            cooldown_key = f"streak_{state.user_id}_{state.streak_days}"
            if _is_on_cooldown(cooldown_key):
                continue

            _set_cooldown(cooldown_key)

            action = MCPAction(
                action_type="streak_reward",
                target_user_id=state.user_id,
                parameters_json=json.dumps({
                    "streak_days": state.streak_days,
                    "reward_bonus": state.streak_days * 5,
                }),
                status="executed",
                source="rule_engine",
            )
            db.add(action)
            actions.append({
                "type": "streak_reward",
                "user_id": str(state.user_id),
                "streak_days": state.streak_days,
            })

        if actions:
            await db.commit()

        return actions

    # ── RULE 4: Expire old campaigns ──
    async def _rule_expire_campaigns(self, db: AsyncSession) -> List[Dict]:
        """Expire campaigns that have passed their end time."""
        actions = []
        now = datetime.now(timezone.utc)

        stmt = select(RewardCampaign).where(
            RewardCampaign.status == CampaignStatus.ACTIVE,
            RewardCampaign.end_time != None,  # noqa: E711
            RewardCampaign.end_time < now,
        )
        result = await db.execute(stmt)
        expired = list(result.scalars().all())

        for campaign in expired:
            campaign.status = CampaignStatus.EXPIRED
            actions.append({
                "type": "campaign_expired",
                "campaign_id": str(campaign.id),
            })

        if actions:
            await db.commit()
            logger.info(f"MCP Rule: expired {len(actions)} campaigns")

        return actions

    async def get_network_state(self, db: AsyncSession) -> Dict[str, Any]:
        """Collect current network state for LLM escalation decisions."""
        # Active workers
        active_q = await db.execute(
            select(func.count(Device.id)).where(
                Device.status.in_([DeviceStatus.ONLINE, DeviceStatus.COMPUTING])
            )
        )
        active_workers = active_q.scalar() or 0

        # Under-supplied jobs
        under_q = await db.execute(
            select(Job).where(
                Job.status == JobStatus.ACTIVE,
                Job.active_workers < Job.required_workers,
            )
        )
        under_supplied_jobs = list(under_q.scalars().all())

        # Inactive users
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        inactive_q = await db.execute(
            select(func.count(User.id)).where(
                User.is_active == True,  # noqa: E712
                User.last_active_at < cutoff,
            )
        )
        inactive_count = inactive_q.scalar() or 0

        # Active campaigns
        campaign_q = await db.execute(
            select(func.count(RewardCampaign.id)).where(
                RewardCampaign.status == CampaignStatus.ACTIVE
            )
        )
        active_campaigns = campaign_q.scalar() or 0

        return {
            "active_workers": active_workers,
            "under_supplied_count": len(under_supplied_jobs),
            "under_supplied_jobs": [
                {
                    "job_id": str(j.id),
                    "active_workers": j.active_workers,
                    "required_workers": j.required_workers,
                    "priority": j.priority,
                    "reward_multiplier": j.reward_multiplier,
                }
                for j in under_supplied_jobs
            ],
            "inactive_users_48h": inactive_count,
            "active_campaigns": active_campaigns,
            "reward_pool_remaining": 50000,  # Configurable
        }


# ── Cooldown helpers ──

def _is_on_cooldown(key: str) -> bool:
    """Check if an action is on cooldown."""
    import time
    if key in _action_cooldowns:
        return time.time() - _action_cooldowns[key] < COOLDOWN_SECONDS
    return False


def _set_cooldown(key: str):
    """Set cooldown for an action."""
    import time
    _action_cooldowns[key] = time.time()


# Singleton
rule_engine = RuleEngine()
