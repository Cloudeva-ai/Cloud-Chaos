from pathlib import Path
from streamlit.testing.v1 import AppTest
from backend import attempts


def test_reload_resumes_saved_answers_and_deadline():
    path = Path(__file__).parents[1] / "app.py"
    first = AppTest.from_file(path, default_timeout=30).run()
    first.text_input(key="reg_name").input("Resume QA")
    first.text_input(key="reg_company").input("Isolated test")
    first.button[0].click().run()
    token = first.session_state["attempt_token"]
    deadline = first.session_state["deadline"]
    first.button(key="right_0").click().run()
    second = AppTest.from_file(path, default_timeout=30)
    second.query_params["attempt"] = token
    second.run()
    assert not second.exception
    assert second.session_state["active_pain"] == 1
    assert second.session_state["deadline"] == deadline
    assert attempts.get_attempt(token)["current_idx"] == 1
