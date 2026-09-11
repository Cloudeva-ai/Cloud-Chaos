"""
game_engine.py - Pure business-logic helpers for Cloud Chaos.
No Streamlit dependencies; can be tested independently.
"""

from __future__ import annotations

from game_data import CARDS, NUM_PAINS


def calculate_score(selections: dict[int, dict[str, bool | None]]) -> int:
    """Return the number of correctly judged cards."""
    return sum(
        1
        for idx in range(NUM_PAINS)
        if selections.get(idx, {}).get("answer") is not None
        and selections[idx]["answer"] == CARDS[idx]["is_right"]
    )


def build_breakdown(selections: dict[int, dict[str, bool | None]]) -> list[dict]:
    """Return per-card correctness data for the results screen."""
    breakdown = []
    for idx, card in enumerate(CARDS):
        answer = selections.get(idx, {}).get("answer")
        is_correct = answer is not None and answer == card["is_right"]
        breakdown.append({
            "pain_idx": idx,
            "pain_text": card["pain"],
            "impact_text": card["impact"],
            "owner_text": card["owner"],
            "answer": answer,
            "expected": card["is_right"],
            "both_correct": is_correct,
            "owner_correct": is_correct,
            "impact_correct": is_correct,
        })
    return breakdown


def get_result_tier(score: int) -> dict:
    """Map a score to the display tier shown on the results screen."""
    missed = NUM_PAINS - score
    if score == NUM_PAINS:
        return {
            "emoji": "Trophy",
            "title": "Perfect!",
            "sub": (
                "You spotted every signal correctly. "
                "That is exactly the kind of judgment cloud leaders need daily."
            ),
            "eva": (
                f"EVA delivers <strong>{NUM_PAINS}/{NUM_PAINS} signal clarity every morning</strong> "
                "across cost, governance, and operations."
            ),
        }
    if score >= max(3, NUM_PAINS - 2):
        return {
            "emoji": "Fire",
            "title": "Strong!",
            "sub": f"{score}/{NUM_PAINS} - sharp instincts, but {missed} hidden gap(s) still slipped through.",
            "eva": (
                f"The <strong>{missed} you missed</strong> are exactly the kind of issues "
                "that keep repeating when cloud signals stay fragmented."
            ),
        }
    if score >= 1:
        return {
            "emoji": "Bolt",
            "title": "The Gap.",
            "sub": (
                f"{score}/{NUM_PAINS} - not because you're weak, "
                "but because most cloud teams still review disconnected signals manually."
            ),
            "eva": (
                "<strong>Most teams miss more than they expect.</strong> "
                "EVA turns scattered cloud events into decisions leaders can trust."
            ),
        }
    return {
        "emoji": "Storm",
        "title": "Chaos.",
        "sub": "0 - the cloud is noisy, and bad signals are easy to normalize when no one sees the full picture.",
        "eva": (
            "<strong>Your cloud deserves better.</strong> "
            "EVA cuts through noise and surfaces what actually needs action."
        ),
    }


RANK_MEDALS = {0: "🥇", 1: "🥈", 2: "🥉"}


def format_rank(idx: int) -> str:
    return RANK_MEDALS.get(idx, str(idx + 1))


def format_time(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}" if m else f"{s}s"
