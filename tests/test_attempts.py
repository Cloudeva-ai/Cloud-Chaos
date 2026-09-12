"""Durable attempts enforce timing and exactly-once session creation."""
import importlib
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

os.environ["CLOUD_CHAOS_DATABASE_URL"] = ""
from backend import database as db
from backend.game_data import GAME_DURATION, NUM_PAINS


@pytest.fixture
def attempts():
    try:
        module = importlib.import_module("backend.attempts")
    except ModuleNotFoundError:
        pytest.fail("Durable attempts API is missing")
    db.init_db()
    return module


def start(attempts):
    player, _ = db.upsert_player("QA Attempt " + uuid4().hex, "Isolated Tests")
    return player, attempts.start_attempt(player.id)


def test_answers_are_sequential_boolean_and_immutable(attempts):
    _, state = start(attempts)
    with pytest.raises(ValueError):
        attempts.record_answer(state["token"], 1, True)
    with pytest.raises(ValueError):
        attempts.record_answer(state["token"], 0, 1)
    attempts.record_answer(state["token"], 0, True)
    with pytest.raises(ValueError):
        attempts.record_answer(state["token"], 0, False)
    assert attempts.get_attempt(state["token"])["current_idx"] == 1


def test_deadline_rejects_answer_and_timeout_is_server_derived(attempts, monkeypatch):
    player, state = start(attempts)
    with pytest.raises(ValueError):
        attempts.finalize_attempt(state["token"])
    monkeypatch.setattr(attempts, "_epoch", lambda: state["deadline"])
    with pytest.raises(ValueError):
        attempts.record_answer(state["token"], 0, True)
    result = attempts.finalize_attempt(state["token"])
    assert (result.score, result.time_used, result.timed_out) == (0, GAME_DURATION, True)
    assert attempts.finalize_attempt(state["token"]).id == result.id
    with db.SessionFactory() as session:
        assert session.get(db.Player, player.id).total_plays == 1


def test_concurrent_finalization_creates_one_result_despite_audit_failure(attempts, monkeypatch):
    player, state = start(attempts)
    for idx, card in enumerate(state["cards"]):
        attempts.record_answer(state["token"], idx, card["is_right"])
    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")
    monkeypatch.setattr(db, "log_event", fail_audit)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(attempts.finalize_attempt, [state["token"]] * 4))
    assert len({result.id for result in results}) == 1
    assert results[0].score == NUM_PAINS
    with db.SessionFactory() as session:
        assert session.get(db.Player, player.id).total_plays == 1
    assert attempts.start_attempt(player.id)["token"] != state["token"]
