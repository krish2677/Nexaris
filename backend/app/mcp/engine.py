"""
MCP Engine — autonomous incentive orchestration engine.

Architecture:
  [ Event Stream ] → [ Network Health Analyzer ] → metrics snapshot
                   → [ Campaign Generator ]      → campaign proposals
                   → [ Budget Engine ]           → funding approval
                   → [ Torque Bridge ]           → Torque MCP execution
                   → [ GPT-4o Escalation ]       → complex strategic decisions

90% deterministic, 10% GPT-4o strategic reasoning.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.campaign import IncentiveCampaign, CampaignLifecycle
from app.models.event import Event
from app.models.mcp_action import MCPAction
from app.models.user import User
from app.models.user_retention import UserRetentionState
from app.mcp.budget_engine import budget_engine
from app.mcp.campaign_generator import campaign_generator
from app.mcp.network_health import network_health
from app.mcp.rule_engine import rule_engine
from app.mcp.scoring import compute_contribution_score
from app.mcp.torque_bridge import torque_bridge
from app.services.leaderboard_service import update_user_score

logger = logging.getLogger(__name__)


class MCPEngine:
    """Autonomous incentive orchestration engine.

    Loop:
    1. Collect network health metrics
    2. Run deterministic rules (local, fast, no LLM)
    3. Score completed work (idempotent)
    4. Generate campaign proposals
    5. Fund and activate approved campaigns
    6. Execute Torque primitives
    7. Expire finished campaigns
    8. LLM escalation for complex cases (every 5 cycles)
    9. Forward events to Torque
    """

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None
        self._cycle_count = 0
        self._last_metrics: dict = {}

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("MCP Engine started (autonomous orchestration mode)")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("MCP Engine stopped")

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def last_metrics(self) -> dict:
        return self._last_metrics

    async def _loop(self) -> None:
        from app.core.distributed_lock import mcp_lock

        while self._running:
            try:
                acquired = await mcp_lock.acquire()
                if acquired:
                    try:
                        async with AsyncSessionLocal() as db:
                            await self._run_cycle(db)
                    finally:
                        await mcp_lock.release()
            except Exception as e:
                logger.error(f"MCP loop error: {e}")
            await asyncio.sleep(settings.MCP_CHECK_INTERVAL_SECONDS)

    async def _run_cycle(self, db: AsyncSession) -> None:
        """Execute one full MCP orchestration cycle."""
        self._cycle_count += 1
        cycle = self._cycle_count

        # Step 1: Collect network health metrics
        metrics = await network_health.get_full_metrics(db)
        self._last_metrics = metrics

        # Step 2: Run deterministic rules (always, no LLM)
        await rule_engine.evaluate(db)

        # Step 3: Score completed work (idempotent)
        await self._score_completed_work(db)

        # Step 4: Update retention states
        await self._update_retention(db)

        # Step 5: Generate and execute campaign proposals (every 3 cycles)
        if cycle % 3 == 0:
            await self._orchestrate_campaigns(db, metrics, cycle)

        # Step 6: Expire finished campaigns
        await self._expire_campaigns(db)

        # Step 7: LLM escalation for complex cases (every 5 cycles)
        if cycle % 5 == 0:
            if rule_engine.should_escalate_to_llm(metrics):
                await self._escalate_to_llm(db, metrics)

        # Step 8: Forward events to Torque
        await self._forward_torque_events(db)

        if cycle % 10 == 0:
            logger.info(
                f"MCP cycle {cycle}: "
                f"active={metrics.get('active_contributors', 0)}, "
                f"inactive={metrics.get('inactive_contributors', 0)}, "
                f"campaigns={metrics.get('active_campaigns', 0)}, "
                f"treasury={metrics.get('treasury_balance', 0):.0f}"
            )

    async def _orchestrate_campaigns(self, db: AsyncSession, metrics: dict, cycle: int) -> None:
        """Generate, fund, and execute campaign proposals."""
        proposals = await campaign_generator.generate_campaigns(db, metrics, cycle)

        for spec in proposals:
            try:
                campaign = campaign_generator.build_entity(spec, cycle)
                db.add(campaign)
                await db.flush()

                funded = await budget_engine.fund_campaign(db, campaign)
                if funded:
                    # Execute Torque primitives
                    try:
                        await torque_bridge.execute_campaign(campaign)
                    except Exception as te:
                        logger.warning(f"Torque execution failed for {campaign.name}: {te}")

                    # Log MCP action
                    action = MCPAction(
                        action_type=f"campaign_created_{campaign.campaign_type}",
                        parameters_json=json.dumps(spec),
                        status="executed",
                        source=spec.get("source", "rule_engine"),
                    )
                    db.add(action)

                    # Broadcast via WebSocket
                    try:
                        from app.websocket.hub import ws_manager
                        await ws_manager.broadcast("global", {
                            "type": "campaign_created",
                            "campaign": {
                                "id": str(campaign.id),
                                "name": campaign.name,
                                "type": campaign.campaign_type,
                                "priority": campaign.priority,
                                "reasoning": campaign.reasoning,
                                "reward_pool": campaign.reward_pool,
                                "multiplier": campaign.multiplier,
                            },
                        })
                    except Exception:
                        pass

                    logger.info(
                        f"MCP: Created campaign '{campaign.name}' "
                        f"[{campaign.campaign_type}] "
                        f"pool={campaign.reward_pool:.0f} "
                        f"mult={campaign.multiplier}x"
                    )

            except Exception as e:
                logger.error(f"Campaign creation failed: {e}")

        if proposals:
            await db.commit()

    async def _expire_campaigns(self, db: AsyncSession) -> None:
        """Expire campaigns that have passed their duration and distribute rewards."""
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(IncentiveCampaign).where(
                IncentiveCampaign.status == "active",
                IncentiveCampaign.end_time != None,  # noqa: E711
                IncentiveCampaign.end_time < now,
            )
        )
        expired = list(result.scalars().all())
        for campaign in expired:
            try:
                # Use competition engine to calculate winners and distribute rewards
                from app.services.competition import competition_engine
                result = await competition_engine.complete_campaign(db, campaign.id)
                logger.info(
                    f"MCP: Completed campaign '{campaign.name}' — "
                    f"{result.get('participants', 0)} participants, "
                    f"{len(result.get('payouts', []))} payouts"
                )
            except Exception as e:
                logger.error(f"Campaign completion failed for '{campaign.name}': {e}")
                campaign.status = "expired"
            try:
                await torque_bridge.end_campaign(campaign)
            except Exception:
                pass
        if expired:
            await db.commit()
            logger.info(f"MCP: Processed {len(expired)} expired campaigns")

    async def _score_completed_work(self, db: AsyncSession) -> None:
        """Process unscored validated_work_unit_completed events."""
        stmt = select(Event).where(Event.event_name == "validated_work_unit_completed")
        result = await db.execute(stmt)
        events = list(result.scalars().all())

        scored_count = 0
        for event in events:
            meta = json.loads(event.metadata_json)
            if meta.get("scored"):
                continue

            user_id = event.user_id
            device_power = meta.get("device_power_factor", 1.0)
            urgency = meta.get("urgency_multiplier", 1.0)

            ret_q = await db.execute(
                select(UserRetentionState).where(UserRetentionState.user_id == user_id)
            )
            retention = ret_q.scalar_one_or_none()

            streak_mult = 1.0
            reliability_mult = 1.0
            if retention:
                streak_mult = min(1 + (retention.streak_days * 0.02), 2.0)
                reliability_mult = retention.reliability_score

            score = compute_contribution_score(
                validated_units=1, device_power_factor=device_power,
                urgency_multiplier=urgency, reliability_multiplier=reliability_mult,
                streak_multiplier=streak_mult,
            )

            await update_user_score(db, user_id, score)

            # Also update scores in any active campaign the user is participating in
            # Uses a flag to skip if competition tables don't exist yet
            if not getattr(self, '_competition_tables_missing', False):
                try:
                    from app.services.competition import competition_engine
                    from app.models.competition import CampaignParticipant  # noqa: F811
                    active_cq = await db.execute(
                        select(IncentiveCampaign.id).where(IncentiveCampaign.status == "active")
                    )
                    for (cid,) in active_cq.all():
                        await competition_engine.update_score(
                            db, cid, user_id,
                            validated_units=1, device_power=device_power,
                            urgency_mult=urgency, reliability=reliability_mult,
                        )
                except Exception as comp_err:
                    if "UndefinedTableError" in str(type(comp_err).__name__) or "campaign_participants" in str(comp_err):
                        self._competition_tables_missing = True
                        logger.info("MCP: Competition tables not yet created — skipping campaign score updates")
                    try:
                        await db.rollback()
                    except Exception:
                        pass

            if retention:
                retention.total_validated_tasks += 1
                retention.last_compute_at = datetime.now(timezone.utc)
                retention.last_reward_at = datetime.now(timezone.utc)

            meta["scored"] = True
            meta["score_awarded"] = score
            meta["scored_at"] = datetime.now(timezone.utc).isoformat()
            event.metadata_json = json.dumps(meta)
            scored_count += 1

        if scored_count > 0:
            await db.commit()
            logger.info(f"MCP: scored {scored_count} work unit events")

    async def _update_retention(self, db: AsyncSession) -> None:
        """Update user retention states — streak tracking and churn risk."""
        users_q = await db.execute(
            select(User).where(User.is_active == True)  # noqa: E712
        )
        users = list(users_q.scalars().all())
        now = datetime.now(timezone.utc)
        updated = 0

        for user in users:
            ret_q = await db.execute(
                select(UserRetentionState).where(UserRetentionState.user_id == user.id)
            )
            retention = ret_q.scalar_one_or_none()

            if not retention:
                retention = UserRetentionState(user_id=user.id)
                db.add(retention)
                continue

            if user.last_active_at:
                hours_inactive = (now - user.last_active_at).total_seconds() / 3600
                retention.inactivity_score = min(hours_inactive / 48.0, 1.0)
                retention.churn_risk_score = min(
                    retention.inactivity_score * (1.0 / max(retention.reliability_score, 0.1)), 1.0,
                )

            if retention.last_compute_at:
                days_since = (now - retention.last_compute_at).days
                if days_since <= 1:
                    pass
                elif days_since <= 2:
                    pass
                else:
                    retention.streak_days = 0

            updated += 1

        if updated > 0:
            await db.commit()

    async def _escalate_to_llm(self, db: AsyncSession, state: dict) -> None:
        """Escalate complex decision to GPT-4o via OpenRouter."""
        try:
            from app.mcp.openrouter import get_strategic_decision
            decision = await get_strategic_decision(state)
            if not decision:
                return

            actions = decision.get("actions", [])
            logger.info(f"MCP LLM: received {len(actions)} strategic actions")

            for action_data in actions:
                await self._execute_llm_action(db, action_data)

        except Exception as e:
            logger.error(f"MCP LLM escalation failed: {e}")

    async def _execute_llm_action(self, db: AsyncSession, action_data: dict) -> None:
        """Execute an action returned by GPT-4o."""
        from app.models.job import Job
        action_type = action_data.get("type", "")

        if action_type == "boost_rewards":
            job_id = action_data.get("job_id")
            multiplier = action_data.get("multiplier", 1.5)
            if job_id:
                from sqlalchemy import update
                await db.execute(
                    update(Job).where(Job.id == job_id).values(
                        reward_multiplier=min(multiplier, 10.0)
                    )
                )
        elif action_type == "trigger_raffle":
            pass  # Forward to Torque
        elif action_type == "trigger_leaderboard_boost":
            pass  # Forward to Torque

        mcp_action = MCPAction(
            action_type=action_type,
            parameters_json=json.dumps(action_data),
            status="executed",
            source="llm",
        )
        db.add(mcp_action)
        await db.commit()

    async def _forward_torque_events(self, db: AsyncSession) -> None:
        """Forward recent events to Torque as custom_events."""
        try:
            from app.torque.client import torque_client
            if not settings.TORQUE_API_KEY:
                return

            stmt = select(Event).where(
                Event.event_name.in_([
                    "validated_work_unit_completed", "job_under_supplied",
                    "user_inactive", "streak_completed",
                ])
            ).order_by(Event.created_at.desc()).limit(20)

            result = await db.execute(stmt)
            events = list(result.scalars().all())

            for event in events:
                meta = json.loads(event.metadata_json)
                if meta.get("torque_forwarded"):
                    continue
                try:
                    user_q = await db.execute(select(User).where(User.id == event.user_id))
                    user = user_q.scalar_one_or_none()
                    pubkey = user.wallet_address if user and user.wallet_address else str(event.user_id)

                    await torque_client.send_custom_event(
                        user_pubkey=pubkey, event_name=event.event_name,
                        data={
                            "job_id": str(event.job_id) if event.job_id else None,
                            "device_id": str(event.device_id) if event.device_id else None,
                            **{k: v for k, v in meta.items() if k not in ("scored", "torque_forwarded")},
                        },
                    )
                    meta["torque_forwarded"] = True
                    event.metadata_json = json.dumps(meta)
                except Exception as te:
                    logger.debug(f"Torque event forward failed: {te}")

            await db.commit()
        except Exception as e:
            logger.debug(f"Torque forwarding error: {e}")


# Singleton instance
mcp_engine = MCPEngine()
