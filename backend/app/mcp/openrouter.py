"""
OpenRouter client — GPT-4o strategic reasoning for MCP decisions.
Only called for complex multi-job balancing, not per-event.

Implements:
- Structured JSON output enforcement
- Rate limiting and cooldowns
- Decision caching
- Retry handling
- Token-efficient compressed prompts
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Decision cache: state_hash -> (decision, timestamp)
_decision_cache: Dict[str, tuple[Dict, float]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes
MIN_CALL_INTERVAL = 120  # 2 minutes between LLM calls
_last_call_time: float = 0

SYSTEM_PROMPT = """You are the autonomous incentive orchestration engine for DeSci, a decentralized scientific compute network powered by Torque MCP.

Your role: Analyze network state and produce PRECISE JSON campaign decisions to optimize:
- Contributor retention and re-engagement
- Compute supply/demand balancing
- Dataset completion speed
- Contributor reliability and consistency
- Organic growth via referrals

Campaign types you can create:
1. supply_balancing — redirect compute to under-supplied jobs
2. retention — bring back inactive contributors
3. streak — reward daily consistency
4. new_contributor — activate onboarding
5. referral — drive organic growth
6. dataset_completion — accelerate workload finishing
7. reliability — reward trusted contributors
8. time_based — weekend/night/seasonal boosts
9. experimental — novel AI-invented campaigns

Decision rules:
1. Output ONLY valid JSON
2. Never allocate more than 15% of treasury to a single campaign
3. Max 3 campaigns per decision cycle
4. Prioritize critical supply shortages and retention emergencies
5. Avoid campaign fatigue — don't repeat same types within cooldown
6. Consider treasury sustainability — always preserve emergency reserves
7. Each campaign must have clear reasoning and measurable success metrics

Torque primitives available: leaderboard, raffle, gift, campaign

Output format:
{
  "campaigns": [
    {
      "campaign_name": "descriptive name",
      "campaign_type": "one of the 9 types",
      "reasoning": "why this campaign now",
      "target_audience": "who it targets",
      "reward_pool": 1000,
      "duration_hours": 24,
      "eligibility_rules": ["rule1"],
      "torque_primitives": ["leaderboard", "raffle"],
      "success_metrics": ["metric1"],
      "priority": "low|medium|high|critical",
      "multiplier": 2.0
    }
  ],
  "actions": [
    {"type": "boost_rewards", "job_id": "...", "multiplier": 2.0},
    {"type": "trigger_raffle", "job_id": "...", "tickets_per_task": 3},
    {"type": "send_reengagement_gifts", "target_group": "inactive_users_48h"},
    {"type": "adjust_urgency", "job_id": "...", "new_priority": 8}
  ],
  "reasoning_summary": "brief strategic rationale"
}"""



async def get_strategic_decision(
    network_state: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Call GPT-4o via OpenRouter for strategic MCP decisions.

    Only called when:
    - Multiple jobs compete for workers
    - Churn spike detected
    - Complex reward optimization needed
    - Anomaly detection triggered
    """
    global _last_call_time

    if not settings.OPENROUTER_API_KEY:
        logger.debug("OpenRouter API key not configured, skipping LLM call")
        return None

    # Rate limiting
    now = time.time()
    if now - _last_call_time < MIN_CALL_INTERVAL:
        logger.debug("OpenRouter rate limited, using cached decision")
        return _get_cached_decision(network_state)

    # Check cache
    cached = _get_cached_decision(network_state)
    if cached:
        return cached

    try:
        _last_call_time = now
        decision = await _call_openrouter(network_state)

        if decision:
            # Validate and sanitize
            decision = _validate_decision(decision, network_state)
            # Cache
            state_hash = _compute_state_hash(network_state)
            _decision_cache[state_hash] = (decision, now)
            # Cleanup old cache entries
            _cleanup_cache()
            return decision

    except Exception as e:
        logger.error(f"OpenRouter call failed: {e}")
        return None

    return None


async def _call_openrouter(state: Dict[str, Any]) -> Optional[Dict]:
    """Make the actual OpenRouter API call."""
    # Compress state to minimize tokens
    compressed = _compress_state(state)

    payload = {
        "model": "openai/gpt-4o",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(compressed),
            },
        ],
        "temperature": 0.3,
        "max_tokens": 500,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://desci-compute.app",
        "X-Title": "DeSci Compute MCP",
    }

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

                content = data["choices"][0]["message"]["content"]
                return json.loads(content)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                await asyncio.sleep(5 * (attempt + 1))
                continue
            logger.error(f"OpenRouter HTTP error: {e.response.status_code}")
            break
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"OpenRouter response parse error: {e}")
            break
        except httpx.RequestError as e:
            logger.error(f"OpenRouter connection error: {e}")
            if attempt < 2:
                await asyncio.sleep(2)

    return None


def _compress_state(state: Dict) -> Dict:
    """Compress network state to minimize token usage."""
    compressed = {}

    if "under_supplied_jobs" in state:
        jobs = state["under_supplied_jobs"]
        compressed["under_supplied"] = [
            {
                "id": j.get("job_id", "")[:12],
                "workers": j.get("active_workers", 0),
                "required": j.get("required_workers", 0),
                "priority": j.get("priority", 1),
                "mult": j.get("reward_multiplier", 1.0),
            }
            for j in jobs[:10]  # Limit to top 10
        ]

    compressed["active_workers"] = state.get("active_workers", 0)
    compressed["inactive_48h"] = state.get("inactive_users_48h", 0)
    compressed["reward_pool"] = state.get("reward_pool_remaining", 0)
    compressed["lb_drop"] = state.get("leaderboard_activity_drop", 0)
    compressed["active_campaigns"] = state.get("active_campaigns", 0)

    return compressed


def _compute_state_hash(state: Dict) -> str:
    """Compute a hash of the network state for cache keying.
    Uses a coarse hash so similar states hit the same cache entry."""
    # Quantize numeric values to reduce cache misses
    key_parts = [
        str(state.get("active_workers", 0) // 10),
        str(state.get("inactive_users_48h", 0) // 5),
        str(len(state.get("under_supplied_jobs", []))),
    ]
    return hashlib.md5("|".join(key_parts).encode()).hexdigest()


def _get_cached_decision(state: Dict) -> Optional[Dict]:
    """Return cached decision if state is similar and cache is fresh."""
    state_hash = _compute_state_hash(state)
    if state_hash in _decision_cache:
        decision, ts = _decision_cache[state_hash]
        if time.time() - ts < CACHE_TTL_SECONDS:
            logger.debug("Using cached MCP decision")
            return decision
    return None


def _validate_decision(
    decision: Dict, state: Dict
) -> Dict:
    """Validate and sanitize LLM output to prevent runaway actions."""
    actions = decision.get("actions", [])
    validated = []

    for action in actions[:5]:  # Max 5 actions
        action_type = action.get("type", "")

        if action_type == "boost_rewards":
            mult = min(max(float(action.get("multiplier", 1.5)), 1.0), 10.0)
            action["multiplier"] = mult
            validated.append(action)

        elif action_type == "trigger_raffle":
            tickets = min(max(int(action.get("tickets_per_task", 1)), 1), 10)
            action["tickets_per_task"] = tickets
            validated.append(action)

        elif action_type in ("send_reengagement_gifts", "trigger_leaderboard_boost"):
            validated.append(action)

        elif action_type == "adjust_urgency":
            priority = min(max(int(action.get("new_priority", 5)), 1), 10)
            action["new_priority"] = priority
            validated.append(action)

    decision["actions"] = validated
    return decision


def _cleanup_cache():
    """Remove expired cache entries."""
    now = time.time()
    expired = [k for k, (_, ts) in _decision_cache.items() if now - ts > CACHE_TTL_SECONDS * 2]
    for k in expired:
        del _decision_cache[k]
