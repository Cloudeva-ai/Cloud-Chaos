"""
game_data.py - Static game content for Cloud Chaos.
Each card presents a pain point plus an owner/impact combination.
The player judges whether the combination is right or wrong.
"""

from __future__ import annotations

import random

CARDS = [
    {
        "pain": "Unexplained cost spikes",
        "impact": "Budget overruns",
        "owner": "CFO",
        "is_right": True,
    },
    {
        "pain": "No unified MSP view",
        "impact": "SLA breaches",
        "owner": "MSP delivery head",
        "is_right": True,
    },
    {
        "pain": "Cost & risk in silos",
        "impact": "Blind leadership decisions",
        "owner": "CTO",
        "is_right": True,
    },
    {
        "pain": "Same issues every quarter",
        "impact": "Zero accountability",
        "owner": "FinOps + Eng manager",
        "is_right": True,
    },
    {
        "pain": "Slow deployments",
        "impact": "Need better CI/CD",
        "owner": "DevOps",
        "is_right": False,
    },
    {
        "pain": "Poor on-prem visibility",
        "impact": "Hybrid infra gaps",
        "owner": "IT infra head",
        "is_right": False,
    },
]

PAIN_COLORS = ["#FF6B6B", "#023C57", "#06C2AC", "#0EA5E9", "#14B8A6", "#38BDF8"]
PAIN_LABELS = [f"CARD #{idx + 1}" for idx in range(len(CARDS))]
NUM_PAINS = len(CARDS)
GAME_DURATION = 90


def get_shuffled_cards() -> list[dict[str, object]]:
    """Return a shuffled copy of the card set with stable original indices."""
    cards = [{"orig_idx": idx, **card} for idx, card in enumerate(CARDS)]
    random.shuffle(cards)
    return cards
