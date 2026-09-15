"""Cloud Chaos: registration, timed challenge, results and leaderboard."""
from __future__ import annotations
import html
from pathlib import Path
import time
import streamlit as st
from backend import admin_auth, attempts, database as db, game_data as gd, game_engine as ge
from backend.config import setting
from frontend.components import brand, mascot, render_html, timer, preview_cta, icon

ROOT = Path(__file__).resolve().parents[1]
st.set_page_config(page_title="Cloud Chaos - Cloudeva", page_icon=":material/bolt:", layout="wide")
st.html(ROOT / "static" / "polish.css")


@st.cache_resource
def initialize():
    db.init_db()


try:
    initialize()
except Exception:
    st.error("The event database is temporarily unavailable. Please try again shortly.")
    st.stop()


def go(screen, *, new_game=False):
    if new_game:
        for key in ("attempt_token", "submitted", "session_id", "answer_feedback"):
            st.session_state.pop(key, None)
        st.query_params.clear()
    st.session_state.screen = screen
    st.rerun()


def adopt(state):
    st.session_state.update(attempt_token=state["token"], game_cards=state["cards"],
        game_start_time=state["started_at"], deadline=state["deadline"],
        selections=state["answers"], active_pain=state["current_idx"])


def load_state():
    state = attempts.get_attempt(st.session_state.attempt_token)
    adopt(state)
    return state


def submit():
    try:
        result = attempts.finalize_attempt(st.session_state.attempt_token)
    except ValueError as exc:
        st.warning(str(exc))
        return
    except Exception:
        st.error("Your game result could not be saved right now. Please try again.")
        return
    st.session_state.update(submitted=True, score=result.score, session_id=result.id,
                            result_time=result.time_used, result_timed_out=result.timed_out)
    go("results")


def restore():
    """Reloading resumes the same attempt and its original deadline."""
    token = st.query_params.get("attempt")
    if token and st.session_state.get("attempt_token") != token:
        try:
            state = attempts.get_attempt(token)
            with db.SessionFactory() as session:
                player = session.get(db.Player, state["player_id"])
                st.session_state.player = {"id": player.id, "name": player.name, "company": player.company}
            adopt(state)
            st.session_state.screen = "results" if state["result_session_id"] else "game"
        except ValueError:
            st.query_params.clear()
            st.session_state.screen = "register"
            st.warning("This attempt could not be found. Start a new challenge.")
        except Exception:
            st.error("The event database is temporarily unavailable. Please try again shortly.")
            st.stop()


def register():
    left, right = st.columns([1.14, 1], gap="large")
    with left:
        render_html(f'''<section class="hero-copy"><p class="eyebrow">Cloud Governance Challenge</p>
          <h1 class="hero-title">CLOUD<br><span>CHAOS</span></h1>
          <p class="hero-sub">Read the signal. Beat the clock. Decide whether each cloud
          problem is paired with the right impact and owner.</p>
          <div class="challenge-facts"><div><strong>{gd.GAME_DURATION}s</strong><span>on the clock</span></div>
          <div><strong>{gd.NUM_PAINS} cards</strong><span>right or wrong</span></div>
          <div><strong>3 winners</strong><span>smartwatch prizes</span></div></div></section>''')
    with right:
        mascot("hero-mascot")
        with st.form("register_form", border=True):
            render_html('<h2 class="form-title">Ready to make the call?</h2><p class="form-description">Add your details. The timer starts when you begin.</p>')
            name = st.text_input("Your name", placeholder="Enter your name", key="reg_name", max_chars=120)
            company = st.text_input("Company", placeholder="Enter your company", key="reg_company", max_chars=120)
            start = st.form_submit_button("Start the challenge", type="primary", use_container_width=True)
        if start:
            try:
                with st.spinner("Saving your registration..."):
                    player, _ = db.upsert_player(name, company)
                    state = attempts.start_attempt(player.id)
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error("Registration could not be saved right now. Please try again.")
            else:
                st.session_state.player = {"id": player.id, "name": player.name, "company": player.company}
                st.session_state.update(submitted=False, answer_feedback=None)
                adopt(state)
                st.query_params["attempt"] = state["token"]
                go("game")
    render_html(f'''<aside class="prize-strip"><div class="prize-intro">{icon('trophy')}<strong>Up for grabs</strong></div>
      <video autoplay muted loop playsinline preload="metadata" aria-label="Smartwatch prize">
      <source src="app/static/Smartwatch%203d.mp4" type="video/mp4"></video>
      <div><strong>Smartwatch</strong><p>3 winners - announced at the event</p></div></aside>''')
    nav, admin_col = st.columns([3, 1])
    if nav.button("View Leaderboard", icon=":material/leaderboard:", key="reg_lb_btn", use_container_width=True):
        go("leaderboard")
    if admin_col.button("Admin Login", key="reg_admin_btn", use_container_width=True):
        go("admin")


@st.fragment(run_every="1s")
def heartbeat():
    if time.time() >= st.session_state.deadline and not st.session_state.get("submitted"):
        submit()


def game():
    try:
        state = load_state()
    except Exception:
        st.error("Your challenge could not be loaded. Refresh to reconnect.")
        return
    if state["result_session_id"] or time.time() >= state["deadline"]:
        submit()
        return
    count = state["current_idx"]
    timer(st.session_state.player, state["deadline"], count)
    phase = "Mission complete" if count == gd.NUM_PAINS else ("Final stretch" if count >= 4 else "Trust your cloud instincts")
    receipt = st.session_state.get("answer_feedback") or "Six signals. One shot at the top."
    segments = ''.join(f'<span class="segment {"done" if i < count else "active" if i == count else ""}"></span>' for i in range(gd.NUM_PAINS))
    render_html(f'''<div class="mission-header"><div><div class="eyebrow">Cloud control</div><h2>{phase}</h2>
      <p class="answer-receipt" role="status">{html.escape(receipt)}</p></div><div class="progress-block"><div class="segments">{segments}</div>
      <span>Signal {min(count + 1, gd.NUM_PAINS)} of {gd.NUM_PAINS}</span></div></div>''')
    if count < gd.NUM_PAINS:
        card = state["cards"][count]
        names = ["Cost radar", "Service watch", "Risk scanner", "Accountability", "Delivery pulse", "Hybrid watch"]
        with st.container(key=f"question_{count}"):
            render_html(f'''<article class="question-copy"><div class="question-meta"><span>Signal {count+1:02d} of {gd.NUM_PAINS:02d}</span>
              <span>Awaiting your verdict</span></div><div class="signal-category">{icon('monitoring')} {names[card['orig_idx']]}</div>
              <h1 class="question-title">{html.escape(card['pain'])}</h1><p class="question-prompt">The diagnosis is in. Does this pairing check out?</p>
              <dl class="question-pair"><div><dt>Impact</dt><dd>{html.escape(card['impact'])}</dd></div>
              <div><dt>Owner</dt><dd>{html.escape(card['owner'])}</dd></div></dl></article>''')
            right, wrong = st.columns(2)
            choice = None
            if right.button("Right", icon=":material/check:", key=f"right_{count}", use_container_width=True):
                choice = True
            if wrong.button("Wrong", icon=":material/close:", key=f"wrong_{count}", use_container_width=True):
                choice = False
            if choice is not None:
                try:
                    updated = attempts.record_answer(state["token"], count, choice)
                except ValueError:
                    if time.time() >= state["deadline"]:
                        submit()
                    else:
                        st.warning("That card has already been answered or is not active. Refresh to continue.")
                except Exception:
                    st.error("Your answer could not be saved. Please try again.")
                else:
                    adopt(updated)
                    st.session_state.answer_feedback = f"Card {count+1} saved. {'Right' if choice else 'Wrong'}"
                    st.rerun()
            st.caption("Choose an answer to advance to the next signal.")
        st.button(f"{gd.NUM_PAINS-count} signals left to decode", disabled=True, key="fab_submit_dis", use_container_width=True)
        st.caption(f"Complete {gd.NUM_PAINS-count} more card {'decision' if count == 5 else 'decisions'} to unlock submit.")
    else:
        render_html(f'<div class="mission-complete">{icon("task_alt")}<h2>All signals decoded.</h2><p>Review your calls or reveal your score.</p></div>')
        for card in state["cards"]:
            choice = state["answers"][card["orig_idx"]]["answer"]
            render_html(f'<div class="review-call"><span>{html.escape(card["pain"])}</span><strong>{"Right" if choice else "Wrong"}</strong></div>')
        if st.button("Reveal my score", key="fab_submit", type="primary", use_container_width=True):
            submit()
    heartbeat()


def results():
    try:
        state = load_state()
        if not state["result_session_id"]:
            go("game")
        with db.SessionFactory() as session:
            result = session.get(db.GameSession, state["result_session_id"])
        score, time_used = result.score, result.time_used
        st.session_state.update(score=score, submitted=True, session_id=result.id)
    except Exception:
        st.error("Your result could not be loaded. Refresh to reconnect.")
        return
    tier = ge.get_result_tier(score)
    render_html(f'''<section class="result-hero"><div class="score-ring" style="--score:{score/gd.NUM_PAINS*100}%">
       <div><strong>{score}</strong><span>/ {gd.NUM_PAINS}</span></div></div><h1>{tier['title']}</h1><p>{tier['sub']}</p></section>
       <div class="eva-note">{icon('bolt')}<div><strong>EVA gets this right every morning</strong><p>{tier['eva']}</p></div></div>''')
    cards = []
    for row in ge.build_breakdown(state["answers"]):
        correct = row["both_correct"]
        answer = "No answer" if row["answer"] is None else ("Right" if row["answer"] else "Wrong")
        cards.append(f'''<article class="result-card {'correct' if correct else 'incorrect'}"><div class="review-top"><span>Card {row['pain_idx']+1}</span>{icon('check_circle' if correct else 'cancel')}</div>
          <h3>{html.escape(row['pain_text'])}</h3><p>You said: <strong>{answer}</strong></p><p>Correct call: <strong>{'Right' if row['expected'] else 'Wrong'}</strong></p></article>''')
    render_html('<div class="result-grid">'+''.join(cards)+'</div>')
    if score == gd.NUM_PAINS:
        render_html(f'<div class="lucky-draw">{icon("redeem")}<div><strong>You\'re in the lucky draw!</strong><p>Winner announced at the event</p></div></div>')
    render_html(f'<p class="completed-time">Completed in <strong>{ge.format_time(time_used)}</strong></p>')
    if result.timed_out:
        st.info("Time's up. Your saved answers have been submitted.")
    preview_cta("Final Step", "register now<br>to complete the challenge", animated=True)
    if st.button("Leaderboard", icon=":material/leaderboard:", key="res_lb", use_container_width=True):
        go("leaderboard")


@st.fragment(run_every="5s")
def leaderboard_rows():
    try:
        entries, stats = db.get_leaderboard(limit=5), db.get_stats()
    except Exception:
        st.warning("Leaderboard data is temporarily unavailable. Pull to refresh or try again in a moment.")
        return
    if not entries:
        render_html(f'<div class="empty-state">{icon("leaderboard")}<p>No players yet - be the first!</p></div>')
    for rank, row in enumerate(entries, 1):
        render_html(f'''<div class="leader-row rank-{rank}"><span class="leader-rank">{rank}</span><div class="leader-person">
          <strong>{html.escape(str(row['name']))}</strong><span>{html.escape(str(row['company']))}</span></div>
          <div class="leader-score">{row['score']}<small>/{gd.NUM_PAINS}</small></div><div class="leader-time">{ge.format_time(row['time_used'])}</div></div>''')
    render_html('<div class="event-stats">'+''.join(f'<div><strong>{value}</strong><span>{label}</span></div>' for label,value in [
        ("Players",stats['total_players']), ("Plays",stats['total_sessions']), ("Perfect",stats['perfect_count']),
        ("Avg Score",stats['avg_score'] or '-')])+'</div>')


def leaderboard():
    render_html(f'<div class="page-heading"><div><h1>Leaderboard</h1><p>Top scores from today\'s event</p></div>{icon("trophy")}</div>')
    leaderboard_rows()
    preview_cta("Experience EVA", "Unlock full cloud intelligence with your free preview")
    a, b = st.columns(2)
    if a.button("Back", icon=":material/arrow_back:", key="lb_back", use_container_width=True):
        go("register", new_game=True)
    if b.button("Refresh", icon=":material/refresh:", key="lb_refresh", use_container_width=True):
        db._invalidate_read_caches()
        st.rerun()


def admin():
    render_html('<div class="page-heading"><div><h1>Admin Panel</h1><p>Live registration and leaderboard account data from the event database.</p></div></div>')
    if st.session_state.get("admin_authenticated") and time.time() - st.session_state.get("admin_signed_in", 0) > 1800:
        st.session_state.admin_authenticated = False
        st.session_state.pop("admin_export", None)
    if not st.session_state.get("admin_authenticated"):
        with st.form("admin_login_form", clear_on_submit=True):
            username = st.text_input("Admin Username", key="admin_username", max_chars=120)
            password = st.text_input("Admin Password", type="password", key="admin_password", max_chars=256)
            login = st.form_submit_button("Unlock Admin", type="primary", use_container_width=True)
        if login:
            result = admin_auth.authenticate(username, password, setting("ADMIN_USERNAME"), setting("ADMIN_PASSWORD"))
            if result.authenticated:
                st.session_state.update(admin_authenticated=True, admin_signed_in=time.time())
                st.rerun()
            st.error(result.message)
    else:
        try:
            rows = db.get_admin_panel_data()
            columns = [
                ("Name", "name"), ("Company", "company"), ("Plays", "total_plays"),
                ("Best score", "best_score"), ("Best time", "best_time"),
                ("Status", "sync_status"),
            ]
            header = ''.join(f"<th>{label}</th>" for label, _ in columns)
            body = ''.join(
                '<tr>' + ''.join(
                    f"<td>{html.escape(str(row.get(key) if row.get(key) is not None else '-'))}</td>"
                    for _, key in columns
                ) + '</tr>' for row in rows
            ) or '<tr><td colspan="6">No registrations yet.</td></tr>'
            render_html(f'''<div class="admin-table-wrap"><table class="admin-table"><thead><tr>{header}</tr></thead>
              <tbody>{body}</tbody></table></div>''')
            if st.button("Prepare Admin Excel", key="prepare_export"):
                st.session_state.admin_export = db.export_admin_workbook().read_bytes()
            if st.session_state.get("admin_export"):
                st.download_button("Download Admin Excel", st.session_state.admin_export,
                                   file_name="cloud_chaos_admin_export.xlsx", key="admin_download_excel")
            if st.button("Refresh", key="admin_refresh"):
                db._invalidate_read_caches()
                st.rerun()
        except Exception:
            st.error("Admin data is temporarily unavailable. Please try again.")
        if st.button("Log out", key="admin_logout"):
            st.session_state.admin_authenticated = False
            st.session_state.pop("admin_export", None)
            st.rerun()
    if st.button("Back", key="admin_back"):
        go("register", new_game=True)


restore()
screen = st.session_state.get("screen", "register")
if screen in ("game", "results") and not st.session_state.get("attempt_token"):
    screen = "register"
st.html(f'<style>.stMainBlockContainer{{max-width:{"1240" if screen == "register" else "900"}px !important}}</style>')
brand()
with st.container(key=f"screen_{screen}"):
    {"register":register, "game":game, "results":results, "leaderboard":leaderboard, "admin":admin}.get(screen, register)()
