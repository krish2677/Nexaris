"""
Campaign Competition API — active campaigns, leaderboards, joining, treasury deposits.
Gracefully handles missing competition tables (pre-migration).
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.campaign import IncentiveCampaign
from app.models.competition import CampaignParticipant, WalletDeposit, RewardDistribution
from app.models.treasury import TreasuryLedger
from app.models.user import User
from app.services.competition import competition_engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["campaigns"])


# ── Schemas ──

class DepositRequest(BaseModel):
    tx_signature: str
    amount_sol: float
    wallet_address: str
    campaign_id: str | None = None


class JoinCampaignRequest(BaseModel):
    campaign_id: str


async def _safe_participant_count(db: AsyncSession, campaign_id) -> int:
    """Get participant count, returning 0 if table doesn't exist yet."""
    try:
        result = await db.execute(
            select(func.count(CampaignParticipant.id)).where(
                CampaignParticipant.campaign_id == campaign_id
            )
        )
        return result.scalar() or 0
    except Exception:
        await db.rollback()
        return 0


# ── Public Campaign Endpoints ──

@router.get("/campaigns/active")
async def list_active_campaigns(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    campaigns = []
    try:
        result = await db.execute(
            select(IncentiveCampaign).where(
                IncentiveCampaign.status == "active"
            ).order_by(IncentiveCampaign.created_at.desc())
        )
        campaigns = result.scalars().all()
    except Exception:
        await db.rollback()

    out = []
    for c in campaigns:
        count = await _safe_participant_count(db, c.id)
        out.append({
            "id": str(c.id),
            "name": c.name,
            "campaign_type": c.campaign_type,
            "priority": c.priority,
            "status": c.status,
            "reasoning": c.reasoning,
            "reward_pool": c.reward_pool,
            "multiplier": c.multiplier,
            "duration_hours": c.duration_hours,
            "participants": count,
            "torque_primitives": json.loads(c.torque_primitives_json or "[]"),
            "start_time": c.start_time.isoformat() if c.start_time else None,
            "end_time": c.end_time.isoformat() if c.end_time else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    return {"campaigns": out, "total": len(out)}


@router.get("/campaigns/{campaign_id}")
async def get_campaign_detail(
    campaign_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed campaign info with leaderboard."""
    cid = UUID(campaign_id)
    cq = await db.execute(select(IncentiveCampaign).where(IncentiveCampaign.id == cid))
    campaign = cq.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    leaderboard = []
    count = 0
    my = None
    try:
        leaderboard = await competition_engine.get_campaign_leaderboard(db, cid, limit=20)
        count = await _safe_participant_count(db, cid)
        my_entry = await db.execute(
            select(CampaignParticipant).where(
                CampaignParticipant.campaign_id == cid,
                CampaignParticipant.user_id == user.id,
            )
        )
        my = my_entry.scalar_one_or_none()
    except Exception:
        await db.rollback()

    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "campaign_type": campaign.campaign_type,
        "priority": campaign.priority,
        "status": campaign.status,
        "reasoning": campaign.reasoning,
        "reward_pool": campaign.reward_pool,
        "multiplier": campaign.multiplier,
        "duration_hours": campaign.duration_hours,
        "participants": count,
        "torque_primitives": json.loads(campaign.torque_primitives_json or "[]"),
        "start_time": campaign.start_time.isoformat() if campaign.start_time else None,
        "end_time": campaign.end_time.isoformat() if campaign.end_time else None,
        "leaderboard": leaderboard,
        "my_rank": my.rank if my else None,
        "my_score": round(my.contribution_score, 2) if my else None,
        "my_reward": my.reward_earned_sol if my else None,
    }


@router.get("/campaigns/{campaign_id}/leaderboard")
async def campaign_leaderboard(
    campaign_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get live leaderboard for a campaign."""
    cid = UUID(campaign_id)
    try:
        leaderboard = await competition_engine.get_campaign_leaderboard(db, cid, limit=50)
    except Exception:
        await db.rollback()
        leaderboard = []
    return {"campaign_id": campaign_id, "leaderboard": leaderboard}


@router.post("/campaigns/{campaign_id}/join")
async def join_campaign(
    campaign_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Join a campaign competition."""
    cid = UUID(campaign_id)
    try:
        result = await competition_engine.join_campaign(db, cid, user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Competition tables not ready: {e}")
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


# ── Treasury Endpoints ──

@router.get("/treasury/balance")
async def treasury_balance(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get treasury SOL balance."""
    from app.solana.client import solana_client

    sol_balance = await solana_client.get_treasury_balance()
    treasury_pubkey = solana_client.get_treasury_pubkey()

    # DB treasury state
    treasury = None
    try:
        tq = await db.execute(select(TreasuryLedger).limit(1))
        treasury = tq.scalar_one_or_none()
    except Exception:
        await db.rollback()

    # Total deposits (safe)
    total_deposits = 0.0
    total_rewards = 0.0
    try:
        total_deposits = float((await db.execute(
            select(func.coalesce(func.sum(WalletDeposit.amount_sol), 0))
            .where(WalletDeposit.status == "confirmed")
        )).scalar() or 0.0)
        total_rewards = float((await db.execute(
            select(func.coalesce(func.sum(RewardDistribution.amount_sol), 0))
            .where(RewardDistribution.status == "confirmed")
        )).scalar() or 0.0)
    except Exception:
        await db.rollback()

    return {
        "sol_balance": sol_balance,
        "treasury_wallet": treasury_pubkey,
        "total_deposits": total_deposits,
        "total_rewards_distributed": total_rewards,
        "ledger_balance": treasury.total_balance if treasury else 0.0,
        "ledger_available": treasury.available_balance if treasury else 0.0,
        "utilization_rate": treasury.utilization_rate if treasury else 0.0,
    }


@router.post("/treasury/deposit")
async def record_deposit(
    req: DepositRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record and verify a SOL deposit transaction."""
    from app.solana.client import solana_client

    # Check for duplicate
    try:
        existing = await db.execute(
            select(WalletDeposit).where(WalletDeposit.tx_signature == req.tx_signature)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Transaction already recorded")
    except HTTPException:
        raise
    except Exception:
        await db.rollback()

    # Verify on-chain
    verification = await solana_client.verify_transaction(
        req.tx_signature, min_amount_sol=0.001
    )

    status = "confirmed" if verification.get("verified") else "pending"

    try:
        deposit = WalletDeposit(
            user_id=user.id,
            wallet_address=req.wallet_address,
            tx_signature=req.tx_signature,
            amount_sol=req.amount_sol,
            amount_lamports=req.amount_sol * 1_000_000_000,
            status=status,
            category="campaign_fund" if req.campaign_id else "deposit",
            campaign_id=UUID(req.campaign_id) if req.campaign_id else None,
        )
        db.add(deposit)

        # Update treasury ledger
        tq = await db.execute(select(TreasuryLedger).limit(1))
        treasury = tq.scalar_one_or_none()
        if treasury and status == "confirmed":
            treasury.total_balance += req.amount_sol

        # Update user wallet address if not set
        if not user.wallet_address:
            user.wallet_address = req.wallet_address

        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to record deposit: {e}")

    # Broadcast
    try:
        from app.websocket.hub import ws_manager
        await ws_manager.broadcast("global", {
            "type": "treasury_updated",
            "deposit_amount": req.amount_sol,
            "total_balance": treasury.total_balance if treasury else req.amount_sol,
        })
    except Exception:
        pass

    return {
        "success": True,
        "deposit_id": str(deposit.id),
        "status": status,
        "verified": verification.get("verified", False),
        "amount_sol": req.amount_sol,
    }


@router.get("/wallet/history")
async def wallet_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's transaction history (deposits + rewards)."""
    deposits = []
    rewards = []
    try:
        dq = await db.execute(
            select(WalletDeposit).where(WalletDeposit.user_id == user.id)
            .order_by(WalletDeposit.created_at.desc()).limit(20)
        )
        deposits = [
            {
                "type": "deposit",
                "amount_sol": d.amount_sol,
                "tx_signature": d.tx_signature,
                "status": d.status,
                "wallet": d.wallet_address,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in dq.scalars().all()
        ]

        rq = await db.execute(
            select(RewardDistribution).where(RewardDistribution.user_id == user.id)
            .order_by(RewardDistribution.created_at.desc()).limit(20)
        )
        rewards = [
            {
                "type": "reward",
                "amount_sol": r.amount_sol,
                "tx_signature": r.tx_signature,
                "campaign_id": str(r.campaign_id),
                "tier": r.tier,
                "rank": r.rank,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rq.scalars().all()
        ]
    except Exception:
        await db.rollback()

    return {"deposits": deposits, "rewards": rewards}


@router.get("/user/rankings")
async def user_rankings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's campaign participation and ranking history."""
    try:
        pq = await db.execute(
            select(CampaignParticipant, IncentiveCampaign.name, IncentiveCampaign.status)
            .join(IncentiveCampaign, CampaignParticipant.campaign_id == IncentiveCampaign.id)
            .where(CampaignParticipant.user_id == user.id)
            .order_by(CampaignParticipant.joined_at.desc())
            .limit(30)
        )
        rows = pq.all()
    except Exception:
        await db.rollback()
        rows = []

    return {
        "total_campaigns": len(rows),
        "total_rewards_sol": sum(r[0].reward_earned_sol for r in rows),
        "rankings": [
            {
                "campaign_id": str(r[0].campaign_id),
                "campaign_name": r[1],
                "campaign_status": r[2],
                "rank": r[0].rank,
                "score": round(r[0].contribution_score, 2),
                "validated_units": r[0].validated_units,
                "reward_earned_sol": r[0].reward_earned_sol,
                "joined_at": r[0].joined_at.isoformat() if r[0].joined_at else None,
            }
            for r in rows
        ],
    }
