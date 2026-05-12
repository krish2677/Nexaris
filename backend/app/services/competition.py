"""
Competition Engine — manages campaign participation, live leaderboards,
winner calculation, and automatic reward distribution.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import IncentiveCampaign
from app.models.competition import CampaignParticipant, RewardDistribution, WalletDeposit
from app.models.user import User

logger = logging.getLogger(__name__)

# Reward distribution tiers (percentage of pool)
REWARD_TIERS = {
    "top1": {"max_rank": 1, "percentage": 0.40},
    "top3": {"max_rank": 3, "percentage": 0.30},
    "top10": {"max_rank": 10, "percentage": 0.20},
    "participation": {"max_rank": 9999, "percentage": 0.10},
}


class CompetitionEngine:
    """Manages the full campaign competition lifecycle."""

    async def join_campaign(
        self, db: AsyncSession, campaign_id: UUID, user_id: UUID
    ) -> Dict[str, Any]:
        """Add a user to a campaign competition."""
        # Check campaign is active
        cq = await db.execute(select(IncentiveCampaign).where(IncentiveCampaign.id == campaign_id))
        campaign = cq.scalar_one_or_none()
        if not campaign or campaign.status != "active":
            return {"success": False, "error": "Campaign not active"}

        # Check if already joined
        existing = await db.execute(
            select(CampaignParticipant).where(
                CampaignParticipant.campaign_id == campaign_id,
                CampaignParticipant.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none():
            return {"success": True, "message": "Already participating"}

        participant = CampaignParticipant(
            campaign_id=campaign_id, user_id=user_id,
        )
        db.add(participant)
        await db.commit()

        # Broadcast join event
        try:
            from app.websocket.hub import ws_manager
            count = await self._get_participant_count(db, campaign_id)
            await ws_manager.broadcast("global", {
                "type": "participant_joined",
                "campaign_id": str(campaign_id),
                "participants": count,
            })
        except Exception:
            pass

        return {"success": True, "message": "Joined campaign"}

    async def update_score(
        self, db: AsyncSession, campaign_id: UUID, user_id: UUID,
        validated_units: int = 1, device_power: float = 1.0,
        urgency_mult: float = 1.0, reliability: float = 1.0,
    ) -> float:
        """Update a participant's contribution score."""
        pq = await db.execute(
            select(CampaignParticipant).where(
                CampaignParticipant.campaign_id == campaign_id,
                CampaignParticipant.user_id == user_id,
            )
        )
        participant = pq.scalar_one_or_none()
        if not participant:
            # Auto-join
            await self.join_campaign(db, campaign_id, user_id)
            pq = await db.execute(
                select(CampaignParticipant).where(
                    CampaignParticipant.campaign_id == campaign_id,
                    CampaignParticipant.user_id == user_id,
                )
            )
            participant = pq.scalar_one_or_none()

        if not participant:
            return 0.0

        # Compute score delta
        score_delta = (
            10.0 * validated_units * device_power * urgency_mult * reliability
        )
        participant.contribution_score += score_delta
        participant.validated_units += validated_units
        participant.last_score_at = datetime.now(timezone.utc)
        await db.commit()

        # Recalculate ranks
        await self._recalculate_ranks(db, campaign_id)

        return participant.contribution_score

    async def get_campaign_leaderboard(
        self, db: AsyncSession, campaign_id: UUID, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get the leaderboard for a specific campaign."""
        stmt = (
            select(CampaignParticipant, User.email, User.wallet_address)
            .join(User, CampaignParticipant.user_id == User.id)
            .where(CampaignParticipant.campaign_id == campaign_id)
            .order_by(CampaignParticipant.contribution_score.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [
            {
                "user_id": str(row[0].user_id),
                "email": row[1],
                "wallet": row[2][:8] + "..." if row[2] else None,
                "score": round(row[0].contribution_score, 2),
                "validated_units": row[0].validated_units,
                "rank": row[0].rank,
                "reward_earned": row[0].reward_earned_sol,
                "joined_at": row[0].joined_at.isoformat() if row[0].joined_at else None,
            }
            for row in rows
        ]

    async def complete_campaign(
        self, db: AsyncSession, campaign_id: UUID
    ) -> Dict[str, Any]:
        """Complete a campaign: freeze leaderboard, calculate winners, distribute rewards."""
        cq = await db.execute(select(IncentiveCampaign).where(IncentiveCampaign.id == campaign_id))
        campaign = cq.scalar_one_or_none()
        if not campaign:
            return {"success": False, "error": "Campaign not found"}

        # Freeze: mark as completed
        campaign.status = "completed"
        campaign.end_time = datetime.now(timezone.utc)

        # Recalculate final ranks
        await self._recalculate_ranks(db, campaign_id)

        # Get all participants ranked
        pq = await db.execute(
            select(CampaignParticipant)
            .where(CampaignParticipant.campaign_id == campaign_id)
            .order_by(CampaignParticipant.contribution_score.desc())
        )
        participants = list(pq.scalars().all())

        if not participants:
            await db.commit()
            return {"success": True, "winners": [], "message": "No participants"}

        # Calculate rewards
        pool_sol = campaign.reward_pool or 0.0
        distributions = self._calculate_distributions(participants, pool_sol)

        # Save distributions and attempt payouts
        from app.solana.client import solana_client
        payout_results = []

        for dist in distributions:
            user_id = dist["user_id"]
            amount_sol = dist["amount_sol"]
            rank = dist["rank"]
            tier = dist["tier"]

            # Get wallet address
            uq = await db.execute(select(User).where(User.id == user_id))
            user = uq.scalar_one_or_none()
            wallet = user.wallet_address if user else None

            # Create distribution record
            rd = RewardDistribution(
                campaign_id=campaign_id, user_id=user_id,
                wallet_address=wallet or "unknown",
                amount_sol=amount_sol, rank=rank, tier=tier,
                status="pending",
            )
            db.add(rd)

            # Update participant reward
            await db.execute(
                update(CampaignParticipant).where(
                    CampaignParticipant.campaign_id == campaign_id,
                    CampaignParticipant.user_id == user_id,
                ).values(reward_earned_sol=amount_sol)
            )

            # Attempt SOL transfer if wallet exists
            if wallet and amount_sol > 0:
                try:
                    result = await solana_client.send_reward(wallet, amount_sol)
                    if result.get("success"):
                        rd.status = "confirmed"
                        rd.tx_signature = result.get("signature")
                        payout_results.append({
                            "user_id": str(user_id), "amount": amount_sol,
                            "signature": result.get("signature"), "tier": tier,
                        })
                    else:
                        rd.status = "failed"
                        logger.warning(f"Payout failed for {user_id}: {result.get('error')}")
                except Exception as e:
                    rd.status = "failed"
                    logger.error(f"Payout error for {user_id}: {e}")

        # Store campaign performance
        campaign.performance_json = json.dumps({
            "participants": len(participants),
            "total_distributed_sol": sum(d["amount_sol"] for d in distributions),
            "payouts_completed": len(payout_results),
        })

        await db.commit()

        # Broadcast completion
        try:
            from app.websocket.hub import ws_manager
            await ws_manager.broadcast("global", {
                "type": "campaign_completed",
                "campaign_id": str(campaign_id),
                "campaign_name": campaign.name,
                "winners": payout_results[:3],
                "participants": len(participants),
            })
        except Exception:
            pass

        return {
            "success": True,
            "campaign_id": str(campaign_id),
            "participants": len(participants),
            "distributions": distributions[:10],
            "payouts": payout_results,
        }

    def _calculate_distributions(
        self, participants: List[CampaignParticipant], pool_sol: float
    ) -> List[Dict[str, Any]]:
        """Calculate reward distributions based on rank tiers."""
        distributions = []
        total = len(participants)

        for p in participants:
            rank = p.rank
            tier = "participation"
            if rank == 1:
                tier = "top1"
            elif rank <= 3:
                tier = "top3"
            elif rank <= 10:
                tier = "top10"

            tier_info = REWARD_TIERS[tier]
            tier_pool = pool_sol * tier_info["percentage"]

            # Split tier pool among eligible users in that tier
            if tier == "top1":
                amount = tier_pool
            elif tier == "top3":
                users_in_tier = min(total, 3) - 1  # ranks 2-3
                amount = tier_pool / max(users_in_tier, 1)
            elif tier == "top10":
                users_in_tier = min(total, 10) - min(total, 3)
                amount = tier_pool / max(users_in_tier, 1)
            else:
                users_in_tier = max(total - min(total, 10), 1)
                amount = tier_pool / users_in_tier

            distributions.append({
                "user_id": p.user_id,
                "rank": rank,
                "score": p.contribution_score,
                "tier": tier,
                "amount_sol": round(amount, 6),
            })

        return distributions

    async def _recalculate_ranks(self, db: AsyncSession, campaign_id: UUID) -> None:
        """Recalculate ranks for all participants in a campaign."""
        pq = await db.execute(
            select(CampaignParticipant)
            .where(CampaignParticipant.campaign_id == campaign_id)
            .order_by(CampaignParticipant.contribution_score.desc())
        )
        participants = list(pq.scalars().all())
        for i, p in enumerate(participants, 1):
            p.rank = i
        await db.commit()

        # Broadcast leaderboard update
        try:
            from app.websocket.hub import ws_manager
            top_3 = [
                {"rank": p.rank, "score": round(p.contribution_score, 2), "user_id": str(p.user_id)}
                for p in participants[:3]
            ]
            await ws_manager.broadcast("global", {
                "type": "leaderboard_updated",
                "campaign_id": str(campaign_id),
                "top_3": top_3,
                "total_participants": len(participants),
            })
        except Exception:
            pass

    async def _get_participant_count(self, db: AsyncSession, campaign_id: UUID) -> int:
        result = await db.execute(
            select(func.count(CampaignParticipant.id)).where(
                CampaignParticipant.campaign_id == campaign_id
            )
        )
        return result.scalar() or 0


# Singleton
competition_engine = CompetitionEngine()
