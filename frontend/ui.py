"""Shared Streamlit presentation utilities."""

from __future__ import annotations

import base64
import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from backend import game_data as gd

PRIZE_CARD_STYLE = (
    "flex:1;background:rgba(255,255,255,0.92);border:1px solid rgba(15,23,42,.08);"
    "border-radius:12px;overflow:hidden;display:flex;flex-direction:column;align-items:center;"
)


def init_state() -> None:
    defaults = {
        "screen": "register",
        "player": None,
        "game_cards": [],
        "selections": {i: {"answer": None, "is_correct": None} for i in range(gd.NUM_PAINS)},
        "active_pain": 0,
        "game_start_time": None,
        "time_left": gd.GAME_DURATION,
        "submitted": False,
        "score": 0,
        "session_id": None,
        "last_session_id": None,
        "answer_feedback": None,
        "admin_panel_visible": False,
        "admin_login_visible": False,
        "admin_authenticated": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def admin_credentials() -> tuple[str | None, str | None]:
    try:
        username = st.secrets.get("ADMIN_USERNAME")
        password = st.secrets.get("ADMIN_PASSWORD")
    except Exception:
        username = None
        password = None
    return username or os.getenv("ADMIN_USERNAME"), password or os.getenv("ADMIN_PASSWORD")


def go(screen: str) -> None:
    st.query_params.clear()
    st.session_state.screen = screen
    st.rerun()


def toast(message: str, icon: str | None = None) -> None:
    if hasattr(st, "toast"):
        try:
            if icon:
                st.toast(message, icon=icon)
            else:
                st.toast(message)
        except Exception:
            st.toast(message)
    else:
        st.info(message)


def mobile_haptic(duration_ms: int = 18) -> None:
    components.html(
        f"""
        <script>
                if (navigator.userActivation?.hasBeenActive && navigator.vibrate) {{
          navigator.vibrate({duration_ms});
        }}
        </script>
        """,
        height=0,
        width=0,
    )


@st.cache_data
def image_data_uri(path: str) -> str:
    image_path = Path(path)
    suffix = image_path.suffix.lower().lstrip(".") or "png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/{suffix};base64,{encoded}"


@st.cache_data
def video_data_uri(path: str) -> str:
    video_path = Path(path)
    suffix = video_path.suffix.lower()
    mime = "video/quicktime" if suffix == ".mov" else f"video/{suffix.lstrip('.') or 'mp4'}"
    encoded = base64.b64encode(video_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def image_markup(path: Path, alt: str, *, height_px: int = 140) -> str:
    if not path.exists():
        fallback = alt.replace(" prize", "")
        return (
            f"<div style='height:{height_px}px;display:flex;align-items:center;"
            f"justify-content:center;color:var(--muted)'>{fallback}</div>"
        )
    image_src = image_data_uri(str(path))
    return (
        f'<img src="{image_src}" alt="{alt}" '
        f'style="width:100%;height:{height_px}px;object-fit:cover;display:block;background:#fff;">'
    )


def video_markup(path: Path, *, height_px: int = 140) -> str:
    if not path.exists():
        return (
            f"<div style='height:{height_px}px;display:flex;align-items:center;"
            f"justify-content:center;color:var(--muted)'>Smartwatch</div>"
        )
    video_src = video_data_uri(str(path))
    video_type = "video/quicktime" if path.suffix.lower() == ".mov" else "video/mp4"
    return (
        f'<video autoplay muted loop playsinline preload="auto" '
        f'disablepictureinpicture controlslist="nodownload nofullscreen noremoteplayback" '
        f'style="width:100%;height:{height_px}px;object-fit:cover;display:block;background:radial-gradient(circle at 50% 30%, #ffffff, #dbeafe 40%, #0f172a 100%);">'
        f'<source src="{video_src}" type="{video_type}">'
        f"</video>"
    )


def prize_card_html(media_html: str, label: str, winners_text: str) -> str:
    return f"""
    <div class="prize-card" style="{PRIZE_CARD_STYLE}">
      <div class="prize-media" style="width:100%">{media_html}</div>
      <div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#335369;padding:10px 0 4px;text-align:center">{label}</div>
      <div style="font-size:12px;font-weight:700;color:#00111f;padding-bottom:10px">{winners_text}</div>
    </div>
    """
