import pytest

from backend import game_data as gd
from backend import game_engine as ge


def selections_for(answers):
    return {
        index: {"answer": answer, "is_correct": None}
        for index, answer in enumerate(answers)
    }


def test_calculate_score_uses_canonical_answers():
    answers = [card["is_right"] for card in gd.CARDS]

    assert ge.calculate_score(selections_for(answers)) == gd.NUM_PAINS


def test_calculate_score_handles_missing_answers():
    answers = [card["is_right"] for card in gd.CARDS]
    answers[-1] = None

    assert ge.calculate_score(selections_for(answers)) == gd.NUM_PAINS - 1


def test_calculate_score_does_not_trust_is_correct_flag():
    selections = selections_for([False] * gd.NUM_PAINS)
    for selection in selections.values():
        selection["is_correct"] = True

    expected = sum(not card["is_right"] for card in gd.CARDS)
    assert ge.calculate_score(selections) == expected


def test_format_time():
    assert ge.format_time(0) == "0s"
    assert ge.format_time(65) == "1:05"


@pytest.mark.parametrize("score", [-1, gd.NUM_PAINS + 1])
def test_result_tier_accepts_only_domain_scores(score):
    with pytest.raises(ValueError):
        ge.get_result_tier(score)
