"""Durable, sequential game attempts. The browser never owns answers or timing."""
from contextlib import contextmanager
from datetime import datetime, timezone
import time
from uuid import uuid4

from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, select, text
import json

from . import database as db
from .game_data import CARDS, GAME_DURATION, NUM_PAINS, get_shuffled_cards
from .game_engine import calculate_score


class Attempt(db.Base):
    __tablename__ = "attempts"
    token = Column(String(36), primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    started_at = Column(Float, nullable=False)
    deadline = Column(Float, nullable=False)
    card_order = Column(Text, nullable=False)
    answers = Column(Text, nullable=False, default="{}")
    result_session_id = Column(Integer, ForeignKey("game_sessions.id"), unique=True)


def _epoch() -> float:
    return time.time()


@contextmanager
def transaction():
    with db.SessionFactory() as session:
        try:
            if db.ENGINE.dialect.name == "sqlite":
                session.execute(text("BEGIN IMMEDIATE"))
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def _locked(session, token):
    row = session.scalar(select(Attempt).where(Attempt.token == token).with_for_update())
    if row is None:
        raise ValueError("This attempt could not be found. Start a new challenge.")
    return row


def _state(row):
    answers = {int(k): v for k, v in json.loads(row.answers).items()}
    selections = {i: {"answer": answers.get(i), "is_correct":
                  answers[i] == card["is_right"] if i in answers else None}
                  for i, card in enumerate(CARDS)}
    return {"token": row.token, "player_id": row.player_id,
            "started_at": row.started_at, "deadline": row.deadline,
            "cards": [{"orig_idx": i, **CARDS[i]} for i in json.loads(row.card_order)],
            "answers": selections, "current_idx": len(answers),
            "result_session_id": row.result_session_id}


def start_attempt(player_id: int) -> dict:
    if GAME_DURATION <= 0:
        raise ValueError("Game duration must be positive.")
    with transaction() as session:
        if session.get(db.Player, player_id) is None:
            raise ValueError("Register before starting a challenge.")
        now = _epoch()
        row = Attempt(token=str(uuid4()), player_id=player_id, started_at=now,
                      deadline=now + GAME_DURATION,
                      card_order=json.dumps([c["orig_idx"] for c in get_shuffled_cards()]),
                      answers="{}")
        session.add(row)
        session.flush()
        return _state(row)


def get_attempt(token: str) -> dict:
    with db.SessionFactory() as session:
        row = session.get(Attempt, token)
        if row is None:
            raise ValueError("This attempt could not be found. Start a new challenge.")
        return _state(row)


def record_answer(token: str, display_idx: int, answer: bool) -> dict:
    if type(answer) is not bool or type(display_idx) is not int:
        raise ValueError("Choose Right or Wrong for the active card.")
    with transaction() as session:
        row = _locked(session, token)
        if row.result_session_id is not None or _epoch() >= row.deadline:
            raise ValueError("The attempt has ended.")
        answers = json.loads(row.answers)
        if display_idx != len(answers) or not 0 <= display_idx < NUM_PAINS:
            raise ValueError("That card has already been answered or is not active.")
        original = json.loads(row.card_order)[display_idx]
        answers[str(original)] = answer
        row.answers = json.dumps(answers)
        session.flush()
        return _state(row)


def finalize_attempt(token: str) -> db.GameSession:
    with transaction() as session:
        row = _locked(session, token)
        if row.result_session_id is not None:
            return session.get(db.GameSession, row.result_session_id)
        now = _epoch()
        timed_out = now >= row.deadline
        state = _state(row)
        if state["current_idx"] != NUM_PAINS and not timed_out:
            raise ValueError("Answer every card to submit.")
        score = calculate_score(state["answers"])
        duration = max(0, min(int(now - row.started_at), int(row.deadline - row.started_at)))
        result = db.GameSession(player_id=row.player_id, score=score, time_used=duration,
                                timed_out=timed_out, is_perfect=score == NUM_PAINS)
        session.add(result)
        session.flush()
        for idx, selection in state["answers"].items():
            answer = selection["answer"]
            correct = answer is not None and answer == CARDS[idx]["is_right"]
            session.add(db.Selection(session_id=result.id, pain_idx=idx,
                        owner_orig_idx=None if answer is None else int(answer),
                        impact_orig_idx=None if answer is None else int(answer),
                        owner_correct=correct, impact_correct=correct, both_correct=correct))
        player = session.scalar(select(db.Player).where(db.Player.id == row.player_id).with_for_update())
        player.total_plays += 1
        player.last_seen = datetime.now(timezone.utc)
        if score > player.best_score or (score == player.best_score and
                (player.best_time is None or duration < player.best_time)):
            player.best_score, player.best_time = score, duration
        row.result_session_id = result.id
    db._invalidate_read_caches()
    # Optional analytics must never turn a committed score into a retryable failure.
    try:
        db.log_event(result.player_id, "game_submit", json.dumps({"session_id": result.id,
                    "score": result.score, "time_used": result.time_used, "timed_out": result.timed_out}))
    except Exception:
        pass
    return result
