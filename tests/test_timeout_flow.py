import os
import tempfile
import time
from pathlib import Path

os.environ["CLOUD_CHAOS_DATA_DIR"] = tempfile.mkdtemp(prefix="cloud-chaos-timeout-")

from streamlit.testing.v1 import AppTest

from backend import database as db
from backend import game_data as gd
from backend.attempts import Attempt


def test_expired_game_is_submitted_as_timed_out():
    app_test = AppTest.from_file(Path(__file__).parents[1] / "app.py", default_timeout=30).run()
    app_test.text_input(key="reg_name").input("Timeout QA")
    app_test.text_input(key="reg_company").input("Local Test")
    app_test.button[0].click().run()

    assert not app_test.exception
    assert app_test.session_state["screen"] == "game"

    # Expire the durable attempt; presentation state cannot set the deadline.
    with db.SessionFactory() as session:
        attempt = session.get(Attempt, app_test.session_state["attempt_token"])
        attempt.started_at = time.time() - gd.GAME_DURATION - 1
        attempt.deadline = attempt.started_at + gd.GAME_DURATION
        session.commit()
    app_test.run()

    assert not app_test.exception
    assert app_test.session_state["screen"] == "results"
    assert app_test.session_state["submitted"] is True

    with db.SessionFactory() as session:
        result = session.get(db.GameSession, app_test.session_state["session_id"])
        assert result.timed_out is True
