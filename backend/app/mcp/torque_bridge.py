"""
Torque MCP Bridge — maps campaign decisions to Torque API primitives.
Handles leaderboard creation, raffle launches, gift distribution, and campaign management.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from app.models.campaign import IncentiveCampaign, CampaignType
from app.torque.client import torque_client

logger = logging.getLogger(__name__)


class TorqueBridge:
    """Maps IncentiveCampaign entities to Torque MCP API calls."""

    async def execute_campaign(self, campaign: IncentiveCampaign) -> Dict[str, Any]:
        """Execute all Torque primitives for a campaign."""
        primitives = json.loads(campaign.torque_primitives_json or "[]")
        results = {"campaign_id": str(campaign.id), "primitives_executed": []}

        for primitive in primitives:
            try:
                result = await self._execute_primitive(primitive, campaign)
                results["primitives_executed"].append({
                    "type": primitive, "status": "success", "result": result,
                })
            except Exception as e:
                logger.warning(f"Torque primitive '{primitive}' failed for {campaign.name}: {e}")
                results["primitives_executed"].append({
                    "type": primitive, "status": "failed", "error": str(e),
                })

        return results

    async def _execute_primitive(self, primitive: str, campaign: IncentiveCampaign) -> Dict:
        """Execute a single Torque primitive."""
        if primitive == "leaderboard":
            return await self._create_leaderboard(campaign)
        elif primitive == "raffle":
            return await self._create_raffle(campaign)
        elif primitive == "gift":
            return await self._send_gifts(campaign)
        elif primitive == "campaign":
            return await self._create_torque_campaign(campaign)
        else:
            logger.debug(f"Unknown Torque primitive: {primitive}")
            return {"status": "skipped", "reason": f"unknown_primitive_{primitive}"}

    async def _create_leaderboard(self, campaign: IncentiveCampaign) -> Dict:
        """Create a Torque leaderboard for the campaign."""
        return await torque_client.send_custom_event(
            user_pubkey="system",
            event_name="leaderboard_campaign_created",
            data={
                "campaign_id": str(campaign.id),
                "campaign_name": campaign.name,
                "campaign_type": campaign.campaign_type,
                "multiplier": campaign.multiplier,
                "duration_hours": campaign.duration_hours,
            },
        )

    async def _create_raffle(self, campaign: IncentiveCampaign) -> Dict:
        """Create a Torque raffle for the campaign."""
        return await torque_client.send_custom_event(
            user_pubkey="system",
            event_name="raffle_campaign_created",
            data={
                "campaign_id": str(campaign.id),
                "campaign_name": campaign.name,
                "reward_pool": campaign.reward_pool,
                "duration_hours": campaign.duration_hours,
                "target_audience": campaign.target_audience,
            },
        )

    async def _send_gifts(self, campaign: IncentiveCampaign) -> Dict:
        """Send Torque gifts for the campaign."""
        return await torque_client.send_custom_event(
            user_pubkey="system",
            event_name="gift_campaign_created",
            data={
                "campaign_id": str(campaign.id),
                "campaign_name": campaign.name,
                "gift_type": campaign.campaign_type,
                "reward_pool": campaign.reward_pool,
            },
        )

    async def _create_torque_campaign(self, campaign: IncentiveCampaign) -> Dict:
        """Create a full Torque campaign."""
        return await torque_client.send_custom_event(
            user_pubkey="system",
            event_name="incentive_campaign_created",
            data={
                "campaign_id": str(campaign.id),
                "campaign_name": campaign.name,
                "campaign_type": campaign.campaign_type,
                "reward_pool": campaign.reward_pool,
                "duration_hours": campaign.duration_hours,
                "multiplier": campaign.multiplier,
                "reasoning": campaign.reasoning[:200] if campaign.reasoning else "",
            },
        )

    async def end_campaign(self, campaign: IncentiveCampaign) -> Dict:
        """Notify Torque that a campaign has ended."""
        return await torque_client.send_custom_event(
            user_pubkey="system",
            event_name="campaign_ended",
            data={
                "campaign_id": str(campaign.id),
                "campaign_name": campaign.name,
                "final_status": campaign.status,
            },
        )


torque_bridge = TorqueBridge()
