"""
Contribution scoring formula.

score = validated_work_units × device_power_factor × urgency_multiplier
        × reliability_multiplier × streak_multiplier

Extended with:
- Referral bonus calculation
- Campaign participation scoring  
- Reliability tier classification
"""

from __future__ import annotations


def compute_contribution_score(
    validated_units: int = 1,
    device_power_factor: float = 1.0,
    urgency_multiplier: float = 1.0,
    reliability_multiplier: float = 1.0,
    streak_multiplier: float = 1.0,
) -> float:
    """Calculate the contribution score for a work unit completion.

    Formula:
        base_score × validated_units × device_power × urgency × reliability × streak
    """
    base_score = 10.0  # base points per validated unit
    return round(
        base_score
        * validated_units
        * device_power_factor
        * urgency_multiplier
        * reliability_multiplier
        * streak_multiplier,
        4,
    )


def compute_referral_bonus(
    referrer_score: float,
    referred_first_task: bool = False,
) -> float:
    """Dual-sided referral bonus.
    Referrer gets 5% of their total score as bonus.
    Extra bonus if referred user completes first task.
    """
    base_bonus = referrer_score * 0.05
    if referred_first_task:
        base_bonus *= 2.0
    return round(min(base_bonus, 500.0), 4)


def get_reliability_tier(score: float) -> str:
    """Classify contributor reliability into tiers."""
    if score >= 0.95:
        return "platinum"
    elif score >= 0.85:
        return "gold"
    elif score >= 0.70:
        return "silver"
    elif score >= 0.50:
        return "bronze"
    return "unranked"


def compute_campaign_eligibility_score(
    reliability: float,
    streak_days: int,
    total_tasks: int,
) -> float:
    """Score used to determine campaign raffle/leaderboard eligibility."""
    return round(
        (reliability * 0.4)
        + (min(streak_days / 30, 1.0) * 0.3)
        + (min(total_tasks / 100, 1.0) * 0.3),
        4,
    )
