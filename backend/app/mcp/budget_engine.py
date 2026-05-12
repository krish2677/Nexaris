"""
Budget Allocation Engine — ensures the autonomous agent never overspends
treasury funds, enforces allocation percentages, and tracks ROI per campaign.

Allocation split (configurable):
- 40% retention campaigns
- 25% supply balancing
- 15% referrals
- 10% streak rewards
- 10% experimental campaigns

Reserves 10% of total balance as emergency liquidity.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import IncentiveCampaign
from app.models.treasury import TreasuryLedger, TreasuryTransaction

logger = logging.getLogger(__name__)

# Budget allocation percentages (of available balance) — keyed by plain strings
ALLOCATION_PERCENTAGES: Dict[str, float] = {
    "retention": 0.40,
    "supply_balancing": 0.25,
    "referral": 0.15,
    "streak": 0.10,
    "experimental": 0.10,
}

# Map campaign types (strings) to budget categories (strings)
CAMPAIGN_TO_CATEGORY: Dict[str, str] = {
    "retention": "retention",
    "new_contributor": "retention",
    "supply_balancing": "supply_balancing",
    "dataset_completion": "supply_balancing",
    "referral": "referral",
    "streak": "streak",
    "reliability": "streak",
    "time_based": "experimental",
    "experimental": "experimental",
}

# Max single campaign spend caps
MAX_CAMPAIGN_PERCENTAGE = 0.15  # Max 15% of available balance per campaign
MAX_CAMPAIGNS_ACTIVE = 8  # Max simultaneous active campaigns


class BudgetEngine:
    """Treasury-safe budget allocation engine."""

    async def get_or_create_treasury(self, db: AsyncSession) -> TreasuryLedger:
        """Get the treasury ledger, creating it if it doesn't exist."""
        result = await db.execute(select(TreasuryLedger).limit(1))
        treasury = result.scalar_one_or_none()
        if not treasury:
            treasury = TreasuryLedger()
            db.add(treasury)
            await db.commit()
            await db.refresh(treasury)
        return treasury

    async def can_fund_campaign(
        self,
        db: AsyncSession,
        campaign_type: str,
        requested_amount: float,
    ) -> Tuple[bool, str]:
        """Check if a campaign can be funded without violating budget rules."""
        treasury = await self.get_or_create_treasury(db)
        available = treasury.available_balance
        category = CAMPAIGN_TO_CATEGORY.get(campaign_type, "experimental")

        # Rule 1: Check total available balance
        if requested_amount > available:
            return False, f"Insufficient balance: {available:.0f} available, {requested_amount:.0f} requested"

        # Rule 2: Max single campaign cap
        max_single = available * MAX_CAMPAIGN_PERCENTAGE
        if requested_amount > max_single:
            return False, f"Exceeds max single campaign cap ({max_single:.0f})"

        # Rule 3: Check category allocation
        category_budget = available * ALLOCATION_PERCENTAGES.get(category, 0.10)
        category_spent = await self._get_category_spent(db, category)
        category_remaining = category_budget - category_spent
        if requested_amount > category_remaining:
            return False, (
                f"Category '{category}' budget exhausted: "
                f"{category_remaining:.0f} remaining of {category_budget:.0f}"
            )

        # Rule 4: Max active campaigns
        active_count = (await db.execute(
            select(func.count(IncentiveCampaign.id)).where(
                IncentiveCampaign.status == "active"
            )
        )).scalar() or 0
        if active_count >= MAX_CAMPAIGNS_ACTIVE:
            return False, f"Max active campaigns ({MAX_CAMPAIGNS_ACTIVE}) reached"

        return True, "approved"

    async def fund_campaign(
        self,
        db: AsyncSession,
        campaign: IncentiveCampaign,
    ) -> bool:
        """Allocate funds from treasury to a campaign."""
        can_fund, reason = await self.can_fund_campaign(
            db, campaign.campaign_type, campaign.reward_pool
        )
        if not can_fund:
            logger.warning(
                f"Budget rejected campaign '{campaign.name}': {reason}"
            )
            campaign.status = "failed"
            await db.commit()
            return False

        category = CAMPAIGN_TO_CATEGORY.get(
            campaign.campaign_type, "experimental"
        )

        # Record transaction
        txn = TreasuryTransaction(
            campaign_id=campaign.id,
            category=category,
            amount=campaign.reward_pool,
            description=f"Fund campaign: {campaign.name}",
        )
        db.add(txn)

        # Update treasury
        treasury = await self.get_or_create_treasury(db)
        treasury.total_spent += campaign.reward_pool

        # Update category allocation tracking
        cat_field = f"allocated_{category}"
        if hasattr(treasury, cat_field):
            setattr(treasury, cat_field, getattr(treasury, cat_field) + campaign.reward_pool)

        # Activate campaign
        campaign.status = "active"
        campaign.start_time = datetime.now(timezone.utc)

        await db.commit()
        logger.info(
            f"Budget: funded campaign '{campaign.name}' with {campaign.reward_pool:.0f} "
            f"from {category} budget"
        )
        return True

    async def get_budget_summary(self, db: AsyncSession) -> Dict[str, Any]:
        """Get a summary of budget allocations and remaining capacity."""
        treasury = await self.get_or_create_treasury(db)
        available = treasury.available_balance
        summary = {
            "total_balance": treasury.total_balance,
            "available_balance": available,
            "reserved_emergency": treasury.reserved_emergency,
            "total_spent": treasury.total_spent,
            "utilization_rate": treasury.utilization_rate,
            "categories": {},
        }

        for category, pct in ALLOCATION_PERCENTAGES.items():
            budget = available * pct
            spent = await self._get_category_spent(db, category)
            summary["categories"][category] = {
                "budget": round(budget, 2),
                "spent": round(spent, 2),
                "remaining": round(budget - spent, 2),
                "percentage": pct,
            }

        return summary

    async def _get_category_spent(
        self, db: AsyncSession, category: str
    ) -> float:
        """Get total spent for a budget category from active campaigns."""
        result = await db.execute(
            select(func.coalesce(func.sum(TreasuryTransaction.amount), 0)).where(
                TreasuryTransaction.category == category
            )
        )
        return float(result.scalar() or 0.0)

    async def calculate_campaign_roi(
        self, db: AsyncSession, campaign_id: UUID
    ) -> Dict[str, Any]:
        """Calculate ROI metrics for a completed campaign."""
        campaign_q = await db.execute(
            select(IncentiveCampaign).where(IncentiveCampaign.id == campaign_id)
        )
        campaign = campaign_q.scalar_one_or_none()
        if not campaign:
            return {}

        perf = json.loads(campaign.performance_json) if campaign.performance_json else {}
        participants = perf.get("participants", 0)
        conversions = perf.get("conversions", 0)
        cost = campaign.spent or campaign.reward_pool

        return {
            "campaign_id": str(campaign.id),
            "campaign_name": campaign.name,
            "cost": cost,
            "participants": participants,
            "conversions": conversions,
            "cost_per_participant": round(cost / max(participants, 1), 2),
            "conversion_rate": round(conversions / max(participants, 1), 4),
        }


# Singleton
budget_engine = BudgetEngine()
