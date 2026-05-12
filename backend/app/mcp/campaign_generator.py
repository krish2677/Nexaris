"""
Campaign Generator — AI brain analyzing network health to produce campaign decisions.
Two-tier: deterministic triggers + GPT-4o escalation for complex cases.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import (
    CampaignLifecycle, CampaignPriority, CampaignType, IncentiveCampaign,
)

logger = logging.getLogger(__name__)

THRESHOLDS = {
    "inactive_critical": 10, "inactive_warning": 5,
    "under_supplied_critical": 3, "stalled_critical": 2,
    "churn_spike": 0.3, "low_retention": 0.5,
    "high_validation_failure": 0.15, "low_growth": 0.01,
    "referral_drought": 2, "max_active_per_type": 2,
}

COOLDOWNS = {
    "retention": 12, "supply_balancing": 4,
    "streak": 48, "new_contributor": 24,
    "referral": 24, "dataset_completion": 6,
    "reliability": 48, "time_based": 12,
    "experimental": 24,
}


class CampaignGenerator:
    async def generate_campaigns(self, db: AsyncSession, m: Dict[str, Any], cycle: int = 0) -> List[Dict]:
        proposals = []
        for ctype, evaluator in [
            ("supply_balancing", self._eval_supply),
            ("retention", self._eval_retention),
            ("streak", self._eval_streaks),
            ("new_contributor", self._eval_activation),
            ("referral", self._eval_referrals),
            ("dataset_completion", self._eval_dataset),
            ("reliability", self._eval_reliability),
            ("time_based", self._eval_time_based),
        ]:
            if not await self._on_cooldown(db, ctype):
                proposals.extend(evaluator(m))
        prio = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        proposals.sort(key=lambda p: prio.get(p.get("priority", "low"), 3))
        return proposals[:3]

    def _eval_supply(self, m: Dict) -> List[Dict]:
        cs = []
        stalled = m.get("stalled_workloads", 0)
        under = m.get("under_supplied_jobs", [])
        bal = m.get("treasury_balance", 0)
        if stalled >= THRESHOLDS["stalled_critical"]:
            cs.append({"campaign_name": "Emergency Compute Sprint", "campaign_type": "supply_balancing",
                "reasoning": f"{stalled} stalled workloads with 0 workers. Immediate redirect needed.",
                "target_audience": "all_active_contributors", "reward_pool": min(2000, bal * 0.05),
                "duration_hours": 6, "eligibility_rules": ["device_online", "min_reliability_0.5"],
                "torque_primitives": ["leaderboard", "raffle"],
                "success_metrics": ["stalled_reduced", "workers_assigned"], "priority": "critical", "multiplier": 2.5})
        elif len(under) >= THRESHOLDS["under_supplied_critical"]:
            cs.append({"campaign_name": "Compute Rebalancing Boost", "campaign_type": "supply_balancing",
                "reasoning": f"{len(under)} under-supplied jobs. Boosting rewards.",
                "target_audience": "idle_contributors", "reward_pool": min(1500, bal * 0.04),
                "duration_hours": 12, "eligibility_rules": ["device_online"],
                "torque_primitives": ["leaderboard", "gift"],
                "success_metrics": ["supply_deficit_reduced"], "priority": "high", "multiplier": 2.0})
        if m.get("gpu_compute_shortage"):
            cs.append({"campaign_name": "GPU Power Hour", "campaign_type": "supply_balancing",
                "reasoning": "GPU compute shortage detected.", "target_audience": "gpu_device_owners",
                "reward_pool": min(1000, bal * 0.03), "duration_hours": 8,
                "eligibility_rules": ["gpu_device"], "torque_primitives": ["leaderboard", "raffle"],
                "success_metrics": ["gpu_devices_increased"], "priority": "high", "multiplier": 3.0})
        return cs

    def _eval_retention(self, m: Dict) -> List[Dict]:
        cs = []
        inactive = m.get("inactive_contributors", 0)
        deep = m.get("deeply_inactive_contributors", 0)
        churn = m.get("high_churn_users", 0)
        total = max(m.get("total_contributors", 1), 1)
        bal = m.get("treasury_balance", 0)
        ratio = churn / total
        if deep >= THRESHOLDS["inactive_critical"]:
            cs.append({"campaign_name": "Comeback Bonus Blitz", "campaign_type": "retention",
                "reasoning": f"{deep} contributors inactive >72h. Churn ratio: {ratio:.0%}.",
                "target_audience": "inactive_72h_plus", "reward_pool": min(2000, bal * 0.05),
                "duration_hours": 48, "eligibility_rules": ["inactive_72h", "has_previous_tasks"],
                "torque_primitives": ["gift", "campaign"],
                "success_metrics": ["reactivated_users"], "priority": "critical" if ratio > THRESHOLDS["churn_spike"] else "high", "multiplier": 2.0})
        elif inactive >= THRESHOLDS["inactive_warning"]:
            cs.append({"campaign_name": "Welcome Back Rewards", "campaign_type": "retention",
                "reasoning": f"{inactive} inactive >48h. Temporary multiplier.", "target_audience": "inactive_48h",
                "reward_pool": min(1000, bal * 0.03), "duration_hours": 24,
                "eligibility_rules": ["inactive_48h"], "torque_primitives": ["gift"],
                "success_metrics": ["reactivated_users"], "priority": "medium", "multiplier": 1.5})
        ret = m.get("retention_rate", 1.0)
        if ret < THRESHOLDS["low_retention"]:
            cs.append({"campaign_name": "Loyalty Acceleration", "campaign_type": "retention",
                "reasoning": f"Retention {ret:.0%} below {THRESHOLDS['low_retention']:.0%}.",
                "target_audience": "all_contributors", "reward_pool": min(3000, bal * 0.06),
                "duration_hours": 72, "eligibility_rules": ["min_1_task"],
                "torque_primitives": ["leaderboard", "raffle", "gift"],
                "success_metrics": ["retention_improved"], "priority": "high", "multiplier": 1.8})
        return cs

    def _eval_streaks(self, m: Dict) -> List[Dict]:
        if m.get("active_contributors", 0) >= 5:
            return [{"campaign_name": "7-Day Streak Challenge", "campaign_type": "streak",
                "reasoning": f"{m['active_contributors']} active — launching streak challenge.",
                "target_audience": "active_contributors", "reward_pool": min(500, m.get("treasury_balance", 0) * 0.015),
                "duration_hours": 168, "eligibility_rules": ["active_last_24h"],
                "torque_primitives": ["leaderboard"], "success_metrics": ["avg_streak_increased"],
                "priority": "low", "multiplier": 1.3}]
        return []

    def _eval_activation(self, m: Dict) -> List[Dict]:
        new = m.get("new_contributors_7d", 0)
        growth = m.get("daily_growth_rate", 0)
        if growth < THRESHOLDS["low_growth"] and new < 5:
            return [{"campaign_name": "First Task Fast Track", "campaign_type": "new_contributor",
                "reasoning": f"Only {new} new in 7d (growth: {growth:.1%}). Boosting onboarding.",
                "target_audience": "new_no_tasks", "reward_pool": min(800, m.get("treasury_balance", 0) * 0.02),
                "duration_hours": 48, "eligibility_rules": ["joined_7d", "zero_tasks"],
                "torque_primitives": ["gift", "campaign"], "success_metrics": ["first_task_rate"],
                "priority": "medium", "multiplier": 2.0}]
        return []

    def _eval_referrals(self, m: Dict) -> List[Dict]:
        if m.get("referral_count_7d", 0) < THRESHOLDS["referral_drought"]:
            return [{"campaign_name": "Bring a Friend Sprint", "campaign_type": "referral",
                "reasoning": f"Only {m.get('referral_count_7d', 0)} referrals in 7d.",
                "target_audience": "all_active", "reward_pool": min(1000, m.get("treasury_balance", 0) * 0.03),
                "duration_hours": 168, "eligibility_rules": ["has_referral_code"],
                "torque_primitives": ["raffle", "leaderboard"], "success_metrics": ["new_referrals"],
                "priority": "medium", "multiplier": 1.5}]
        return []

    def _eval_dataset(self, m: Dict) -> List[Dict]:
        if m.get("dataset_backlog", 0) > 5:
            return [{"campaign_name": "Dataset Completion Sprint", "campaign_type": "dataset_completion",
                "reasoning": f"{m['dataset_backlog']} datasets in backlog.",
                "target_audience": "active_compute", "reward_pool": min(1500, m.get("treasury_balance", 0) * 0.04),
                "duration_hours": 24, "eligibility_rules": ["min_reliability_0.7"],
                "torque_primitives": ["leaderboard", "raffle"], "success_metrics": ["datasets_completed"],
                "priority": "high", "multiplier": 2.5}]
        return []

    def _eval_reliability(self, m: Dict) -> List[Dict]:
        if m.get("validation_failure_rate", 0) > THRESHOLDS["high_validation_failure"]:
            return [{"campaign_name": "Reliability Champions", "campaign_type": "reliability",
                "reasoning": f"Validation failure {m['validation_failure_rate']:.1%} above threshold.",
                "target_audience": "high_reliability", "reward_pool": min(800, m.get("treasury_balance", 0) * 0.02),
                "duration_hours": 72, "eligibility_rules": ["reliability_above_0.9"],
                "torque_primitives": ["gift", "leaderboard"], "success_metrics": ["failure_rate_reduced"],
                "priority": "medium", "multiplier": 1.5}]
        return []

    def _eval_time_based(self, m: Dict) -> List[Dict]:
        cs = []
        now = datetime.now(timezone.utc)
        bal = m.get("treasury_balance", 0)
        if now.weekday() >= 5 and m.get("active_contributors", 0) < m.get("total_contributors", 1) * 0.3:
            cs.append({"campaign_name": "Weekend Compute Rally", "campaign_type": "time_based",
                "reasoning": "Low weekend activity.", "target_audience": "all",
                "reward_pool": min(500, bal * 0.015), "duration_hours": 48,
                "eligibility_rules": ["device_online"], "torque_primitives": ["raffle"],
                "success_metrics": ["weekend_activity"], "priority": "low", "multiplier": 1.5})
        if now.hour >= 22 or now.hour < 6:
            cs.append({"campaign_name": "Night Owl Bonus", "campaign_type": "time_based",
                "reasoning": "Off-peak hours incentive.", "target_audience": "online",
                "reward_pool": min(300, bal * 0.01), "duration_hours": 8,
                "eligibility_rules": ["device_online"], "torque_primitives": ["gift"],
                "success_metrics": ["night_compute"], "priority": "low", "multiplier": 1.3})
        return cs

    async def _on_cooldown(self, db: AsyncSession, ctype: str) -> bool:
        hours = COOLDOWNS.get(ctype, 24)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent = (await db.execute(
            select(func.count(IncentiveCampaign.id)).where(
                IncentiveCampaign.campaign_type == ctype, IncentiveCampaign.created_at > cutoff,
            )
        )).scalar() or 0
        active = (await db.execute(
            select(func.count(IncentiveCampaign.id)).where(
                IncentiveCampaign.campaign_type == ctype, IncentiveCampaign.status == "active",
            )
        )).scalar() or 0
        return recent > 0 or active >= THRESHOLDS["max_active_per_type"]

    def build_entity(self, spec: Dict, cycle: int = 0, source: str = "rule_engine") -> IncentiveCampaign:
        return IncentiveCampaign(
            name=spec.get("campaign_name", "Unnamed"),
            campaign_type=spec.get("campaign_type", "experimental"),
            priority=spec.get("priority", "medium"),
            reasoning=spec.get("reasoning", ""), target_audience=spec.get("target_audience", ""),
            reward_pool=spec.get("reward_pool", 0), duration_hours=spec.get("duration_hours", 24),
            torque_primitives_json=json.dumps(spec.get("torque_primitives", [])),
            eligibility_rules_json=json.dumps(spec.get("eligibility_rules", [])),
            success_metrics_json=json.dumps(spec.get("success_metrics", [])),
            multiplier=spec.get("multiplier", 1.0), source=source, created_by_cycle=cycle,
        )


campaign_generator = CampaignGenerator()
