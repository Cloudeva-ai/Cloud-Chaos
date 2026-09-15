import tempfile
import os

os.environ["CLOUD_CHAOS_DATA_DIR"] = tempfile.mkdtemp(prefix="cloud-chaos-tests-")
os.environ["CLOUD_CHAOS_DATABASE_URL"] = ""

import pytest

from backend import database as db
from backend import game_data as gd


def setup_module():
    db.init_db()


def valid_selections():
    return {
        index: {"answer": card["is_right"], "is_correct": True}
        for index, card in enumerate(gd.CARDS)
    }


def test_save_game_session_rejects_forged_score():
    player, _ = db.upsert_player("Validation User", "Validation Company")

    with pytest.raises(ValueError, match="does not match"):
        db.save_game_session(
            player_id=player.id,
            score=0,
            time_used=10,
            timed_out=False,
            selections=valid_selections(),
        )


def test_save_game_session_rejects_out_of_range_index():
    player, _ = db.upsert_player("Index User", "Validation Company")
    selections = valid_selections()
    selections[gd.NUM_PAINS] = {"answer": True, "is_correct": True}

    with pytest.raises(ValueError, match="outside the game"):
        db.save_game_session(
            player_id=player.id,
            score=gd.NUM_PAINS,
            time_used=10,
            timed_out=False,
            selections=selections,
        )


def test_spreadsheet_values_are_neutralized():
    import pandas as pd

    sanitized = db._sanitize_spreadsheet_values(pd.DataFrame({"name": ["=SUM(A1:A2)", "Normal"]}))

    assert sanitized.loc[0, "name"] == "'=SUM(A1:A2)"
    assert sanitized.loc[1, "name"] == "Normal"


def test_correctness_flags_cannot_be_forged():
    player, _ = db.upsert_player("Flags User", "Validation Company")
    selections = valid_selections()
    for selection in selections.values():
        selection["is_correct"] = False
    result = db.save_game_session(player.id, gd.NUM_PAINS, 10, False, selections)
    assert all(row["both_correct"] for row in db.get_session_breakdown(result.id))


def test_hosted_export_does_not_substitute_local_data(monkeypatch):
    monkeypatch.setattr(db, "HOSTED", True)
    monkeypatch.setattr(db, "get_admin_panel_data", lambda: [])
    def unavailable(**kwargs):
        raise RuntimeError("database unavailable")
    monkeypatch.setattr(db, "get_full_leaderboard", unavailable)
    with pytest.raises(RuntimeError, match="database unavailable"):
        db.export_admin_workbook()


def test_admin_export_supports_postgres_timezone_dates(monkeypatch, tmp_path):
    from datetime import datetime, timezone, timedelta
    import openpyxl
    when = datetime(2026, 9, 12, 14, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    monkeypatch.setattr(db, "get_admin_panel_data", lambda: [{"name": "=unsafe", "registered_at": when}])
    monkeypatch.setattr(db, "get_full_leaderboard", lambda **kw: [{"created_at": when}])
    monkeypatch.setattr(db, "get_stats", lambda: {})
    monkeypatch.setattr(db, "ADMIN_EXPORT_PATH", tmp_path / "admin.xlsx")
    workbook = openpyxl.load_workbook(db.export_admin_workbook())
    assert workbook["registrations"]["A2"].value == "'=unsafe"
    assert workbook["registrations"]["B2"].value == datetime(2026, 9, 12, 9, 0)
    assert workbook["sessions"]["A2"].value == datetime(2026, 9, 12, 9, 0)
