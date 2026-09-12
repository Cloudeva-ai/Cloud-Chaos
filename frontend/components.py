"""Reusable presentation; all gameplay decisions remain in backend services."""
import base64
import html
import math
from pathlib import Path
import time
import streamlit as st
from backend.game_data import GAME_DURATION, NUM_PAINS

ROOT = Path(__file__).resolve().parents[1]


def render_html(content):
    st.html(content)


def icon(name):
    return f'<span class="material-symbols-outlined" aria-hidden="true">{name}</span>'


@st.cache_data
def logo_uri():
    return "data:image/png;base64," + base64.b64encode((ROOT / "Logo" / "CloudEva_Logo_transparent.png").read_bytes()).decode()


def brand():
    render_html(f'''<header class="brand-header"><span class="brand-logo"><img src="{logo_uri()}" alt="Cloudeva" /></span>
      <span>The event challenge</span><button class="motion-toggle" type="button" aria-label="Pause animations" title="Pause animations">{icon('pause')}</button></header>''')
    st.html((ROOT / "static" / "experience.js").read_text(), unsafe_allow_javascript=True)


def wave_video():
  return '''<img class="mascot-video mascot-animation" src="app/static/mascot-wave-static.webp?v=4"
      alt="Cloudeva cat mascot waving" />'''


def mascot(extra_class=""):
    render_html(f'''<div class="mascot-stage {extra_class}"><img class="chill-float"
      src="app/static/mascot_cool_cutout.png" alt="Cloudeva mascot relaxing in its visor and sunglasses"></div>''')


def timer(player, deadline, count):
    remaining = max(0, deadline - time.time())
    render_html(f'''<div class="game-hud"><div class="player-info"><span class="player-avatar">{html.escape(player['name'][0].upper())}</span>
      <div><strong>{html.escape(player['name'])}</strong><span>{html.escape(player['company'])}</span></div></div>
      <div class="timer-wrap"><strong id="cc-timer-num" data-remaining="{remaining*1000:.0f}" data-duration="{GAME_DURATION*1000}" data-deadline="{deadline}">{math.ceil(remaining)}</strong><span>SEC LEFT</span></div>
      <div class="game-count">{count}<small>/{NUM_PAINS}</small></div></div>
      <div class="timer-track"><div id="cc-timer-fill" style="width:{remaining/GAME_DURATION*100}%"></div></div>''')
    st.html((ROOT / "static" / "timer.js").read_text(), unsafe_allow_javascript=True)


def preview_cta(kicker, text, *, animated=False):
    character = wave_video() if animated else '<img src="app/static/mascot_cool_cutout.png" alt="Cloudeva mascot relaxing">'
    render_html(f'''<section class="preview-panel"><div class="mascot-stage preview-mascot">{character}</div>
      <div class="preview-copy"><span class="eyebrow">{kicker}</span><h2>{text}</h2></div></section>
      <a class="preview-link" href="https://app.cloudeva.ai/auth/register" target="_blank" rel="noopener noreferrer">Start Free Preview {icon('arrow_forward')}</a>''')
