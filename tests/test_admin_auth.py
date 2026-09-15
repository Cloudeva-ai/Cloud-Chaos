from backend import database as db


def test_lockout_survives_independent_calls_and_expires(monkeypatch):
    from backend import admin_auth as auth
    db.init_db()
    clock = [1000.0]
    monkeypatch.setattr(auth, "_epoch", lambda: clock[0])
    for _ in range(5):
        assert not auth.authenticate("admin", "bad", "admin", "correct").authenticated
    result = auth.authenticate("admin", "correct", "admin", "correct")
    assert not result.authenticated and result.retry_after == 60
    clock[0] += 61
    assert auth.authenticate("admin", "correct", "admin", "correct").authenticated


def test_missing_config_fails_closed():
    from backend import admin_auth as auth
    assert not auth.authenticate("", "", "", "").authenticated
