"""
app.py — Cloud Chaos: Streamlit Edition  (mobile-first)
========================================================
Single-file Streamlit app with 4 screens:
  register → game → results → leaderboard

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


try:
    secret_data_dir = st.secrets.get("CLOUD_CHAOS_DATA_DIR")
except Exception:
    secret_data_dir = None

if secret_data_dir and not os.getenv("CLOUD_CHAOS_DATA_DIR"):
    os.environ["CLOUD_CHAOS_DATA_DIR"] = str(secret_data_dir)

import database as db
import game_data as gd
import game_engine as ge

APP_DIR = Path(__file__).parent
LOGO_PATH = APP_DIR / "Logo" / "CloudEva_Logo_transparent.png"
PRIZE_CARD_STYLE = (
    "flex:1;background:rgba(255,255,255,0.92);border:1px solid rgba(15,23,42,.08);"
    "border-radius:12px;overflow:hidden;display:flex;flex-direction:column;align-items:center;"
)

# ─────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Cloud Chaos — Cloudeva",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
#  INIT DB
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def _init_database() -> None:
    db.init_db()


_init_database()

# ─────────────────────────────────────────────────────────────
#  GLOBAL CSS  (mobile-first)
# ─────────────────────────────────────────────────────────────
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#00111f">

<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');

/* ── Design tokens ── */
:root {
  --bg:      #0470a2;
  --surface: rgba(255,255,255,0.16);
  --surface-dark: rgba(2,60,87,0.30);
  --light-wash: rgba(236,250,247,0.22);
  --s2:      rgba(119,196,165,0.14);
  --border:  rgba(255,255,255,0.22);
  --accent:  #023c57;
  --accent2: #06c2ac;
  --green:   #77c4a5;
  --text:    #f7fffe;
  --muted:   #d5ecef;
  --shadow:  0 16px 34px rgba(0,0,0,0.18);
  --shadow2: 0 24px 48px rgba(0,0,0,0.24);
  --radius:  22px;
  --tap:     52px;
  --safe-b:  env(safe-area-inset-bottom, 0px);
  --safe-t:  env(safe-area-inset-top, 0px);
}

/* ── Global reset ── */
*, *::before, *::after {
  box-sizing: border-box;
  -webkit-tap-highlight-color: transparent;
  -webkit-text-size-adjust: 100%;
  text-size-adjust: 100%;
}

html { -webkit-overflow-scrolling: touch; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Manrope', sans-serif !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* ── Strip Chrome UI ── */
[data-testid="stSidebar"]          { display: none !important; }
[data-testid="stHeader"]           { display: none !important; }
[data-testid="stDecoration"]       { display: none !important; }
[data-testid="stStatusWidget"]     { display: none !important; }
[data-testid="stToolbar"]          { display: none !important; }
footer, #MainMenu, .viewerBadge_container__r5tak { display: none !important; }

/* ── Container: no top gap, mobile-width, room for sticky bottom bar ── */
[data-testid="stAppViewContainer"] > .main > .block-container {
  padding: 0 0.95rem calc(2px + var(--safe-b)) !important;
  max-width: 480px !important;
  margin: 0 auto !important;
  width: 100% !important;
  min-height: auto !important;
}
[data-testid="stAppViewContainer"] > .main {
  padding-top: 0 !important;
}
[data-testid="stAppViewContainer"] section.main {
  padding-top: 0 !important;
}
[data-testid="stAppViewContainer"] section.main > div {
  padding-top: 0 !important;
}
[data-testid="stAppViewContainer"] .stMainBlockContainer {
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
[data-testid="stAppViewContainer"] > .main > .block-container > div {
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
[data-testid="stAppViewContainer"] .block-container > div > div:first-child {
  margin-top: 0 !important;
  padding-top: 0 !important;
}
[data-testid="stAppViewContainer"] .block-container > div > div:last-child {
  margin-bottom: 0 !important;
  padding-bottom: 0 !important;
}

/* ── Sticky bottom CTA bar ── */
/* ── Dreamy pastel gradient background ── */
[data-testid="stAppViewContainer"]::before {
  content: '';
  position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background:
    radial-gradient(circle at 12% 10%, rgba(236,250,247,0.34), transparent 24%),
    radial-gradient(circle at 84% 8%, rgba(6,194,172,0.20), transparent 18%),
    radial-gradient(circle at 16% 76%, rgba(119,196,165,0.18), transparent 20%),
    radial-gradient(circle at 88% 86%, rgba(29,248,222,0.12), transparent 20%),
    linear-gradient(135deg, #eef8f6 0%, #8cd6cf 18%, #0470a2 46%, #023c57 74%, #001f39 100%);
  background-size: 120% 120%;
  animation: bgShift 16s ease-in-out infinite alternate;
}

/* Soft floating orb */
[data-testid="stAppViewContainer"]::after {
  content: '';
  position: fixed; z-index: 0; pointer-events: none;
  inset: 0;
  background:
    radial-gradient(circle at 24% 32%, rgba(255,255,255,0.22), transparent 18%),
    radial-gradient(circle at 78% 70%, rgba(255,255,255,0.12), transparent 16%),
    linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.00));
  animation: bgFloat 18s ease-in-out infinite alternate;
}

/* ── Typography ── */
.hero-panel,
.section-panel,
.form-shell {
  position: relative;
  overflow: hidden;
  border-radius: calc(var(--radius) + 6px);
  background:
    linear-gradient(180deg, rgba(255,255,255,0.18), rgba(4,112,162,0.24)),
    radial-gradient(circle at 18% 28%, rgba(236,250,247,0.22), transparent 28%),
    radial-gradient(circle at 76% 22%, rgba(6,194,172,0.20), transparent 26%),
    radial-gradient(circle at 66% 78%, rgba(172,219,200,0.14), transparent 24%);
  border: 1px solid rgba(255,255,255,0.24);
  box-shadow: var(--shadow2), inset 0 1px 0 rgba(255,255,255,0.24);
  backdrop-filter: blur(20px) saturate(145%);
  -webkit-backdrop-filter: blur(20px) saturate(145%);
}
.hero-panel { padding: 18px 18px 14px; margin: 0 0 14px; }
.section-panel { padding: 16px; margin: 0 0 14px; }
.form-shell { padding: 16px; margin: 0 0 14px; }
.hero-panel::before,
.section-panel::before,
.form-shell::before {
  content: '';
  position: absolute;
  left: 0;
  bottom: 0;
  width: 120px;
  height: 120px;
  background: radial-gradient(circle, rgba(172,219,200,0.30), transparent 68%);
  pointer-events: none;
}
.hero-panel .glass-sheen,
.section-panel .glass-sheen,
.form-shell .glass-sheen {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(135deg, rgba(255,255,255,0.24) 0%, rgba(255,255,255,0.08) 22%, rgba(255,255,255,0.00) 48%),
    linear-gradient(180deg, rgba(255,255,255,0.10), transparent 34%);
  mix-blend-mode: screen;
  opacity: 0.95;
}
.hero-panel::after,
.section-panel::after,
.form-shell::after {
  content: '';
  position: absolute;
  top: 14px;
  right: 18px;
  width: 74px;
  height: 74px;
  background: radial-gradient(circle, rgba(29,248,222,0.22), transparent 66%);
  filter: blur(2px);
  pointer-events: none;
}
.hero-kicker,
.section-kicker,
.form-kicker {
  font-size: 10px;
  letter-spacing: 2.8px;
  text-transform: uppercase;
  text-align: center;
  color: #ffffff;
  font-weight: 800;
  margin-bottom: 10px;
  text-shadow: 0 1px 10px rgba(2,60,87,0.24);
}
.form-shell,
div[data-testid="stForm"] {
  color: #00111f !important;
}
.form-shell .muted,
.form-shell .form-kicker {
  color: #ffffff !important;
  font-weight: 800 !important;
  text-shadow: 0 1px 10px rgba(2,60,87,0.20);
}
.hero-title {
  font-size: clamp(34px, 9vw, 54px);
  font-weight: 800;
  line-height: 0.96;
  text-align: center;
  margin: 0 0 10px;
  color: #f4fffe;
  letter-spacing: -1.3px;
  white-space: nowrap;
  position: relative;
  animation: chaosTilt 4.8s ease-in-out infinite;
}
.hero-title .chaos-word {
  display: inline-block;
  position: relative;
  padding: 0 0.08em;
}
.hero-title .chaos-word:first-child {
  animation: cloudDrift 3.2s ease-in-out infinite;
}
.hero-title .chaos-word:last-child {
  margin-left: 0.12em;
  animation: chaosJolt 2.4s steps(2, end) infinite;
  text-shadow:
    0 0 0 rgba(0,0,0,0),
    2px 0 0 rgba(6,194,172,0.30),
    -2px 0 0 rgba(119,196,165,0.24);
}
.hero-title .chaos-word:last-child::before,
.hero-title .chaos-word:last-child::after {
  content: attr(data-text);
  position: absolute;
  left: 0;
  top: 0;
  pointer-events: none;
  opacity: 0.55;
}
.hero-title .chaos-word:last-child::before {
  color: #1df8de;
  transform: translate(-2px, 1px);
  clip-path: polygon(0 0, 100% 0, 100% 42%, 0 54%);
  animation: chaosSliceA 1.6s steps(2, end) infinite;
}
.hero-title .chaos-word:last-child::after {
  color: #77c4a5;
  transform: translate(2px, -1px);
  clip-path: polygon(0 52%, 100% 42%, 100% 100%, 0 100%);
  animation: chaosSliceB 1.9s steps(2, end) infinite;
}
.hero-accent-line {
  width: 128px;
  height: 8px;
  border-radius: 999px;
  margin: 0 auto 14px;
  background: linear-gradient(90deg, rgba(119,196,165,0.1), var(--accent2), var(--green), rgba(119,196,165,0.1));
  box-shadow: 0 0 24px rgba(6,194,172,0.22);
}
.hero-sub {
  font-size: 14px; color: #ffffff;
  text-align: center; line-height: 1.7; margin: 0;
  font-weight: 800;
  text-shadow: 0 1px 10px rgba(2,60,87,0.20);
}
.mono { font-family: 'JetBrains Mono', monospace !important; }
.muted { color: var(--muted); font-size: 13px; }

/* ── Logo bar ── */
.logo-bar {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 8px; padding-top: 0;
}
.register-shell {
  margin: 0 !important;
  padding: 0 !important;
}
.logo-chip {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: #fff; font-family: 'JetBrains Mono', monospace;
  font-size: 11px; font-weight: 700; letter-spacing: 2px;
  padding: 6px 14px; border-radius: 999px;
  box-shadow: 0 8px 18px rgba(2,60,87,0.24);
}
.logo-text { font-size: 11px; color: var(--muted); letter-spacing: 3px; text-transform: uppercase; font-weight: 600; }

/* ── Cards ── */
.cc-card {
  background: linear-gradient(180deg, rgba(255,255,255,0.14), rgba(4,112,162,0.18));
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px 16px;
  position: relative; overflow: hidden;
  margin-bottom: 14px;
  box-shadow: var(--shadow), inset 0 1px 0 rgba(255,255,255,0.18);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
}
.cc-card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--green), var(--accent2), var(--accent));
  border-radius: var(--radius) var(--radius) 0 0;
}
.cc-card::after,
.prize-banner::before,
.question-shell::before,
.eva-box::before,
.lb-item::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(140deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.06) 22%, rgba(255,255,255,0.00) 44%),
    linear-gradient(180deg, rgba(255,255,255,0.08), transparent 38%);
  opacity: 0.9;
}

/* ── Stats row ── */
.stats-row { display: flex; margin-bottom: 0; gap: 8px; }
.stat {
  flex: 1; text-align: center;
  padding: 13px 6px;
  background: linear-gradient(180deg, rgba(255,255,255,0.18), rgba(8,243,216,0.10)); border: 1px solid rgba(255,255,255,0.20);
  box-shadow: 0 12px 24px rgba(0,17,31,0.08), inset 0 1px 0 rgba(255,255,255,0.16);
  border-radius: 16px;
  backdrop-filter: blur(16px) saturate(140%);
  -webkit-backdrop-filter: blur(16px) saturate(140%);
}
.stat-num {
  font-size: 18px; font-weight: 800;
  background: linear-gradient(90deg, var(--accent), var(--accent2), var(--green), var(--accent));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.stat-label { font-size: 8px; color: var(--muted); letter-spacing: 1.5px; text-transform: uppercase; margin-top: 4px; font-weight: 700; }

/* ── Prize banner ── */
.prize-banner {
  border-radius: var(--radius); padding: 18px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.16), rgba(3,94,137,0.22)),
    radial-gradient(circle at 12% 18%, rgba(236,250,247,0.18), transparent 22%),
    radial-gradient(circle at 86% 26%, rgba(6,194,172,0.18), transparent 24%);
  border: 1px solid rgba(255,255,255,0.22);
  position: relative; overflow: hidden; margin-bottom: 16px;
  text-align: center; box-shadow: var(--shadow2), inset 0 1px 0 rgba(255,255,255,0.22);
  backdrop-filter: blur(20px) saturate(145%);
  -webkit-backdrop-filter: blur(20px) saturate(145%);
}
.prize-top-label { font-size: 11px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; color: #77c4a5; margin-bottom: 12px; }
.prize-card {
  box-shadow: 0 10px 24px rgba(2,60,87,0.10);
}
.prize-media {
  position: relative;
  overflow: hidden;
  border-radius: 12px 12px 0 0;
  background:
    radial-gradient(circle at 50% 24%, rgba(255,255,255,0.92), rgba(186,230,253,0.92) 34%, rgba(8,47,73,0.96) 100%);
}
.prize-media::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.24), transparent 26%),
    radial-gradient(circle at 50% 108%, rgba(6,194,172,0.20), transparent 34%);
  pointer-events: none;
}
.prize-media img {
  display: block;
}
.prize-media video {
  display: block;
}

@media (max-width: 640px) {
  details [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    gap: 0.55rem !important;
  }
  details [data-testid="column"] {
    min-width: 0 !important;
    flex: 1 1 0 !important;
  }
}

/* ── Game topbar ── */
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  background: linear-gradient(180deg, rgba(255,255,255,0.16), rgba(8,243,216,0.10)); border: 1px solid rgba(255,255,255,0.20);
  border-radius: var(--radius); padding: 10px 14px; margin-bottom: 12px; gap: 10px;
  box-shadow: var(--shadow), inset 0 1px 0 rgba(255,255,255,0.16);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
}
.p-avatar {
  width: 38px; height: 38px; min-width: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 16px; color: #fff;
  box-shadow: 0 4px 12px rgba(2,60,87,0.20);
}
.player-meta { flex: 1; min-width: 0; }
.p-name { font-size: 13px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text); }
.p-co   { font-size: 10px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.timer-wrap  { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; }
.timer-lbl   { font-size: 8px; letter-spacing: 2px; text-transform: uppercase; color: var(--muted); font-weight: 600; }
.timer-num   { font-family: 'JetBrains Mono', monospace; font-size: 32px; font-weight: 700; color: var(--accent); line-height: 1; }
.timer-num.danger { color: #DC2626; animation: pulse 0.5s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.35} }
.score-chip {
  background: linear-gradient(135deg, rgba(119,196,165,0.18), rgba(6,194,172,0.12)); border: 1px solid var(--border); border-radius: 999px;
  padding: 7px 14px; font-family: 'JetBrains Mono', monospace;
  font-size: 15px; font-weight: 700; color: var(--accent); flex-shrink: 0;
}

/* ── Instructions ── */
.instructions {
  background: linear-gradient(180deg, rgba(255,255,255,0.14), rgba(8,243,216,0.08)); border: 1px solid rgba(255,255,255,0.18);
  border-radius: 16px; padding: 10px 12px; font-size: 12px; color: var(--muted);
  line-height: 1.6; text-align: center; margin-bottom: 14px;
  box-shadow: 0 12px 24px rgba(0,17,31,0.06), inset 0 1px 0 rgba(255,255,255,0.16);
}
.instructions strong { color: var(--accent); }

/* ── Progress dots ── */
.dots-row { display: flex; gap: 7px; justify-content: center; margin-bottom: 14px; }
.p-dot { width: 34px; height: 5px; border-radius: 3px; background: rgba(2,60,87,0.14); display: inline-block; transition: background .3s; }
.p-dot.done { background: linear-gradient(90deg, var(--accent), var(--accent2)); }

/* ── Pain cards ── */
.pain-card {
  background: var(--surface); border-radius: var(--radius);
  margin-bottom: 12px; overflow: hidden;
  box-shadow: var(--shadow);
}
.question-shell {
  position: relative;
  overflow: hidden;
  border-radius: 20px;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.14), rgba(3,94,137,0.18)),
    radial-gradient(circle at 12% 18%, rgba(236,250,247,0.14), transparent 26%),
    radial-gradient(circle at 88% 14%, rgba(6,194,172,0.16), transparent 22%);
  border: 1px solid rgba(255,255,255,0.18);
  padding: 14px;
  margin: 4px 0 2px;
  box-shadow: 0 18px 36px rgba(0,17,31,0.08), inset 0 1px 0 rgba(255,255,255,0.16);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
}
.question-kicker {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}
.question-index {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: var(--accent);
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(2,60,87,0.06);
}
.question-state {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  padding: 6px 10px;
  border-radius: 999px;
  color: var(--accent);
  background: rgba(119,196,165,0.20);
}
.question-state.done {
  color: #fff;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
}
.question-title {
  font-size: 16px;
  line-height: 1.52;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 12px;
}
.question-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}
.answer-panel {
  border-radius: 18px;
  padding: 12px;
  background: rgba(255,255,255,0.14);
  border: 1px solid rgba(255,255,255,0.16);
  box-shadow: 0 12px 24px rgba(0,17,31,0.06), inset 0 1px 0 rgba(255,255,255,0.14);
  backdrop-filter: blur(14px) saturate(135%);
  -webkit-backdrop-filter: blur(14px) saturate(135%);
}
.decision-strip {
  margin-top: 12px;
  padding: 0;
  border-radius: 0;
  background: transparent;
  border: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.decision-strip .stButton > button {
  min-height: 48px !important;
  padding: 0 !important;
  border-radius: 12px !important;
  font-size: 24px !important;
  font-weight: 800 !important;
  letter-spacing: 0 !important;
  width: 100% !important;
}
.answer-hint {
  font-size: 11px;
  color: var(--muted);
  line-height: 1.5;
  margin: 4px 0 8px;
}
.pain-header { padding: 13px 14px; display: flex; align-items: flex-start; gap: 9px; }
.pain-badge {
  font-family: 'JetBrains Mono', monospace; font-size: 9px; font-weight: 700;
  padding: 4px 8px; border-radius: 6px; flex-shrink: 0; margin-top: 2px;
  letter-spacing: 1px; white-space: nowrap;
}
.pain-text   { font-size: 13px; line-height: 1.5; flex: 1; color: var(--text); }
.pain-status { font-size: 16px; flex-shrink: 0; margin-top: 1px; }

/* ── Slot boxes ── */
.slot-label  { font-size: 9px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 5px; font-weight: 700; }
.slot-empty  {
  border: 1.5px dashed rgba(6,194,172,0.30); border-radius: 10px;
  padding: 12px 14px; font-size: 12px; color: var(--muted);
  text-align: center; min-height: 50px; margin-bottom: 4px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(172,219,200,0.14);
}
.slot-filled {
  border-radius: 10px; padding: 12px 14px; margin-bottom: 4px;
  font-size: 12px; line-height: 1.4;
  border-left-width: 3px !important; border-left-style: solid !important;
  color: var(--text);
}
.slot-filled strong {
  display: block;
  font-size: 10px;
  letter-spacing: 1.1px;
  text-transform: uppercase;
  margin-bottom: 4px;
  color: var(--muted);
}

/* ── EVA box (results) ── */
.eva-box {
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.14), rgba(3,94,137,0.18)),
    radial-gradient(circle at 16% 18%, rgba(236,250,247,0.14), transparent 26%),
    radial-gradient(circle at 82% 26%, rgba(6,194,172,0.14), transparent 24%);
  border: 1px solid rgba(255,255,255,0.20);
  border-left: 4px solid var(--green); border-radius: var(--radius);
  padding: 14px 16px; margin: 12px 0;
  box-shadow: 0 14px 32px rgba(0,17,31,0.08), inset 0 1px 0 rgba(255,255,255,0.16);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
}
.eva-lbl { font-size: 9px; letter-spacing: 3px; text-transform: uppercase; color: #77c4a5; margin-bottom: 6px; font-weight: 800; }
.eva-txt { font-size: 13px; line-height: 1.7; color: #d6f3ef; }
.final-step-card {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 12px 0 14px;
  padding: 14px;
  border-radius: calc(var(--radius) - 2px);
  background:
    linear-gradient(180deg, rgba(255,255,255,0.16), rgba(4,112,162,0.22)),
    radial-gradient(circle at 18% 20%, rgba(236,250,247,0.16), transparent 26%);
  border: 1px solid rgba(255,255,255,0.22);
  box-shadow: var(--shadow), inset 0 1px 0 rgba(255,255,255,0.18);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
}
.final-step-mascot {
  width: 78px;
  height: 78px;
  min-width: 78px;
  border-radius: 18px;
  object-fit: contain;
  filter: drop-shadow(0 10px 18px rgba(0,0,0,0.18));
}
.final-step-copy {
  min-width: 0;
  text-align: left;
}
.final-step-kicker {
  font-size: 10px;
  letter-spacing: 1.8px;
  text-transform: uppercase;
  color: #77c4a5;
  font-weight: 800;
  margin-bottom: 5px;
}
.final-step-text {
  font-size: 17px;
  line-height: 1.5;
  color: var(--text);
  font-weight: 700;
}
.final-step-text.highlight {
  display: inline-block;
  padding: 8px 12px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(6,194,172,0.28), rgba(255,255,255,0.18));
  border: 1px solid rgba(255,255,255,0.24);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.22);
  font-weight: 800;
}

/* ── Result title / sub ── */
.result-title { font-size: clamp(28px, 8vw, 44px); font-weight: 800; text-align: center; color: var(--text); letter-spacing: -0.8px; }
.result-sub   { font-size: 13px; color: var(--muted); text-align: center; line-height: 1.6; }
.results-shell {
  margin-top: 0 !important;
  padding-top: 0 !important;
}
.results-panel {
  position: relative;
  overflow: hidden;
  margin: 12px 0;
  padding: 16px;
  border-radius: calc(var(--radius) + 4px);
  background:
    linear-gradient(180deg, rgba(255,255,255,0.16), rgba(4,112,162,0.24)),
    radial-gradient(circle at 18% 28%, rgba(236,250,247,0.18), transparent 28%),
    radial-gradient(circle at 76% 22%, rgba(6,194,172,0.16), transparent 26%),
    radial-gradient(circle at 66% 78%, rgba(172,219,200,0.12), transparent 24%);
  border: 1px solid rgba(255,255,255,0.22);
  box-shadow: var(--shadow2), inset 0 1px 0 rgba(255,255,255,0.22);
  backdrop-filter: blur(20px) saturate(145%);
  -webkit-backdrop-filter: blur(20px) saturate(145%);
}
.results-panel::before {
  content: '';
  position: absolute;
  left: -10px;
  bottom: -16px;
  width: 120px;
  height: 120px;
  background: radial-gradient(circle, rgba(172,219,200,0.20), transparent 68%);
  pointer-events: none;
}
.result-breakdown-row {
  display:flex;
  gap:8px;
  margin-bottom:8px;
}
.result-breakdown-card {
  flex:1;
  position:relative;
  overflow:hidden;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.16), rgba(3,94,137,0.20)),
    radial-gradient(circle at 18% 18%, rgba(236,250,247,0.12), transparent 24%);
  border:1px solid rgba(255,255,255,0.18);
  border-top-width:3px;
  border-radius:16px;
  padding:12px 10px;
  box-shadow: 0 14px 28px rgba(0,17,31,0.08), inset 0 1px 0 rgba(255,255,255,0.16);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
}
.lucky-draw-card {
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(255,255,255,0.18), rgba(6,194,172,0.18)),
    radial-gradient(circle at 18% 20%, rgba(236,250,247,0.18), transparent 24%),
    radial-gradient(circle at 84% 24%, rgba(29,248,222,0.16), transparent 20%);
  border: 1px solid rgba(255,255,255,0.24);
  border-radius: calc(var(--radius) - 4px);
  padding: 14px;
  text-align: center;
  margin: 10px 0;
  box-shadow: 0 14px 32px rgba(0,17,31,0.10), inset 0 1px 0 rgba(255,255,255,0.18);
  backdrop-filter: blur(18px) saturate(145%);
  -webkit-backdrop-filter: blur(18px) saturate(145%);
}

/* ── Breakdown cells ── */
.bd-row   { display: flex; gap: 6px; width: 100%; margin-bottom: 12px; }
.bd-cell  {
  flex: 1; background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 10px 4px; text-align: center;
  box-shadow: var(--shadow);
}
.bd-cell .ic  { font-size: 20px; }
.bd-cell .lbl { font-size: 8px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; margin-top: 2px; font-weight: 600; }

/* ── Leaderboard ── */
.lb-title {
  font-size: clamp(28px, 9vw, 44px); font-weight: 800;
  color: var(--text);
  text-align: center; margin: 0 0 2px;
  letter-spacing: -1px;
}
.lb-sub  { font-size: 12px; color: var(--muted); text-align: center; margin: 0 0 16px; }
.lb-item {
  position: relative;
  overflow: hidden;
  background: linear-gradient(180deg, rgba(255,255,255,0.14), rgba(3,94,137,0.18)); border: 1px solid rgba(255,255,255,0.18);
  border-radius: 18px; padding: 12px 14px;
  display: flex; align-items: center; gap: 10px; margin-bottom: 7px;
  box-shadow: 0 14px 28px rgba(0,17,31,0.08), inset 0 1px 0 rgba(255,255,255,0.16);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
}
.lb-rank { font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 700; width: 30px; text-align: center; flex-shrink: 0; }
.lb-info { flex: 1; min-width: 0; }
.lb-pn   { font-weight: 700; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text); }
.lb-co   { font-size: 10px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.lb-sc   { font-family: 'JetBrains Mono', monospace; font-size: 17px; font-weight: 700; color: #ffffff; text-align: right; }
.lb-time { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); text-align: right; }
.r1 { color: #035e89; } .r2 { color: #06c2ac; } .r3 { color: #77c4a5; }
.stButton > button[kind="secondary"] {
  background: linear-gradient(180deg, rgba(255,255,255,0.18), rgba(3,94,137,0.28)) !important;
  border: 1px solid rgba(255,255,255,0.24) !important;
  color: #ffffff !important;
  box-shadow: 0 14px 28px rgba(0,17,31,0.12), inset 0 1px 0 rgba(255,255,255,0.16) !important;
  backdrop-filter: blur(18px) saturate(140%) !important;
  -webkit-backdrop-filter: blur(18px) saturate(140%) !important;
}
.stButton > button[kind="secondary"]:hover {
  border-color: rgba(255,255,255,0.34) !important;
  box-shadow: 0 18px 34px rgba(0,17,31,0.16), inset 0 1px 0 rgba(255,255,255,0.18) !important;
}

/* ── Streamlit form / input overrides ── */
div[data-testid="stForm"] {
  border: 1px solid rgba(255,255,255,0.18) !important;
  padding: 16px !important;
  margin: 0 0 14px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.82), rgba(236,250,247,0.74)),
    radial-gradient(circle at 18% 28%, rgba(119,196,165,0.18), transparent 28%),
    radial-gradient(circle at 78% 22%, rgba(6,194,172,0.16), transparent 26%),
    radial-gradient(circle at 68% 82%, rgba(172,219,200,0.12), transparent 24%) !important;
  border-radius: calc(var(--radius) + 6px) !important;
  box-shadow: var(--shadow2), inset 0 1px 0 rgba(255,255,255,0.20) !important;
  backdrop-filter: blur(20px) saturate(145%) !important;
  -webkit-backdrop-filter: blur(20px) saturate(145%) !important;
}
.stForm { margin: 0 !important; }
.stButton { margin: 0 !important; }

/* Inputs — 16 px REQUIRED to prevent iOS auto-zoom */
.stTextInput > div > div > input {
  background: rgba(255,255,255,0.78) !important; color: #00111f !important;
  border: 1.5px solid rgba(2,60,87,0.12) !important; border-radius: 16px !important;
  font-family: 'Manrope', sans-serif !important; font-size: 16px !important;
  height: var(--tap) !important; padding: 0 16px !important;
  -webkit-appearance: none !important; appearance: none !important;
  box-shadow: 0 10px 24px rgba(0,17,31,0.06), inset 0 1px 0 rgba(255,255,255,0.20) !important;
  backdrop-filter: blur(14px) saturate(135%) !important;
  -webkit-backdrop-filter: blur(14px) saturate(135%) !important;
}
.stTextInput > div > div > input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(6,194,172,0.14) !important;
  outline: none !important;
}
.stTextInput > div > div > input::placeholder { color: rgba(51,83,105,0.48) !important; }
.stTextInput label { color: #00111f !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 700 !important; }

/* Selectboxes — large touch targets */
.stSelectbox > div > div {
  background: rgba(255,255,255,0.78) !important; color: #00111f !important;
  border: 1.5px solid rgba(2,60,87,0.12) !important; border-radius: 16px !important;
  font-size: 14px !important; min-height: var(--tap) !important;
  -webkit-appearance: none !important; appearance: none !important;
  box-shadow: 0 10px 24px rgba(0,17,31,0.06), inset 0 1px 0 rgba(255,255,255,0.18) !important;
  backdrop-filter: blur(14px) saturate(135%) !important;
  -webkit-backdrop-filter: blur(14px) saturate(135%) !important;
}
.stSelectbox > div > div > div { padding: 10px 14px !important; color: #00111f !important; }

/* Buttons — big touch targets with active feedback */
.stButton > button {
  font-family: 'Manrope', sans-serif !important;
  font-weight: 700 !important; font-size: 16px !important;
  border-radius: 999px !important; min-height: var(--tap) !important;
  height: auto !important; line-height: 1.2 !important; width: 100% !important;
  touch-action: manipulation !important;
  -webkit-user-select: none !important; user-select: none !important;
  transition: transform 0.1s, box-shadow 0.15s !important;
}
.stButton > button:active { transform: scale(0.96) !important; }

/* Primary CTA */
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #00111f, var(--accent), var(--accent2)) !important;
  border: none !important; color: #fff !important;
  box-shadow: 0 14px 28px rgba(0,17,31,0.22) !important;
  font-size: 17px !important; min-height: 56px !important;
}
.stButton > button[kind="primary"]:active {
  box-shadow: 0 2px 8px rgba(2,60,87,0.18) !important;
}
.cta-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 64px;
  padding: 16px 20px;
  border-radius: 999px;
  background: linear-gradient(120deg, #0cc7b0 0%, #11dbc4 20%, #0470a2 54%, #023c57 100%);
  border: 1px solid rgba(255,255,255,0.24);
  color: #ffffff !important;
  text-decoration: none !important;
  font-family: 'Manrope', sans-serif;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0.35px;
  line-height: 1.2;
  box-shadow: 
    0 14px 30px rgba(0,17,31,0.22),
    0 0 0 0 rgba(29,248,222,0.22),
    inset 0 1px 0 rgba(255,255,255,0.24);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  margin: 0 0 12px;
  position: relative;
  overflow: hidden;
  isolation: isolate;
  animation: ctaPulse 2.8s ease-in-out infinite, ctaFloat 4.4s ease-in-out infinite;
  transition: transform 0.24s ease, box-shadow 0.24s ease, filter 0.24s ease;
}
.cta-link::before {
  content: '';
  position: absolute;
  inset: -28%;
  background:
    radial-gradient(circle at 18% 52%, rgba(255,255,255,0.34), transparent 14%),
    radial-gradient(circle at 78% 40%, rgba(29,248,222,0.34), transparent 16%),
    radial-gradient(circle at 50% 112%, rgba(255,255,255,0.16), transparent 22%);
  pointer-events: none;
  mix-blend-mode: screen;
  animation: ctaOrbital 5.8s linear infinite;
  z-index: 0;
}
.cta-link::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 999px;
  background: linear-gradient(
    100deg,
    transparent 0%,
    transparent 28%,
    rgba(255,255,255,0.18) 40%,
    rgba(255,255,255,0.80) 50%,
    rgba(255,255,255,0.20) 60%,
    transparent 72%,
    transparent 100%
  );
  pointer-events: none;
  opacity: 0.95;
  transform: translateX(-130%) skewX(-20deg);
  animation: ctaSweep 2.5s cubic-bezier(.22,.61,.36,1) infinite;
  z-index: 1;
}
.cta-link > * {
  position: relative;
  z-index: 2;
}
.cta-copy {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 240px;
  min-height: 1.4em;
  text-shadow: 0 1px 14px rgba(0,17,31,0.34);
}
.cta-text {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 100%;
  text-align: center;
  transform: translate(-50%, -50%);
  opacity: 0;
  white-space: nowrap;
}
.cta-text.primary {
  animation: ctaPrimarySwap 5s infinite;
}
.cta-text.alt {
  animation: ctaAltSwap 5s infinite;
}
.cta-link:hover {
  filter: saturate(1.12) brightness(1.05);
  box-shadow: 
    0 20px 38px rgba(0,17,31,0.24),
    0 0 0 10px rgba(29,248,222,0.10),
    0 0 36px rgba(29,248,222,0.24),
    inset 0 1px 0 rgba(255,255,255,0.26);
  transform: translateY(-3px) scale(1.015);
  animation-play-state: paused;
}
@keyframes ctaPulse {
  0%, 100% { 
    box-shadow: 
      0 14px 30px rgba(0,17,31,0.22),
      0 0 0 0 rgba(29,248,222,0.18),
      inset 0 1px 0 rgba(255,255,255,0.24);
  }
  50% { 
    box-shadow: 
      0 18px 36px rgba(0,17,31,0.24),
      0 0 0 8px rgba(29,248,222,0.10),
      0 0 34px rgba(29,248,222,0.22),
      inset 0 1px 0 rgba(255,255,255,0.24);
  }
}
@keyframes ctaFloat {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-4px) scale(1.012); }
}
@keyframes ctaOrbital {
  0% { transform: rotate(0deg) scale(1); }
  50% { transform: rotate(180deg) scale(1.05); }
  100% { transform: rotate(360deg) scale(1); }
}
@keyframes ctaSweep {
  0%, 18% { transform: translateX(-130%) skewX(-20deg); }
  46%, 100% { transform: translateX(130%) skewX(-20deg); }
}
@keyframes ctaPrimarySwap {
  0%, 56% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
  60%, 100% {
    opacity: 0;
    transform: translate(-50%, calc(-50% - 8px)) scale(0.96);
  }
}
@keyframes ctaAltSwap {
  0%, 58% {
    opacity: 0;
    transform: translate(-50%, calc(-50% + 8px)) scale(0.96);
  }
  64%, 96% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
  100% {
    opacity: 0;
    transform: translate(-50%, calc(-50% - 8px)) scale(0.96);
  }
}
/* Secondary */
.stButton > button[kind="secondary"] {
  background: rgba(255,255,255,0.10) !important;
  border: 1.5px solid rgba(119,196,165,0.12) !important;
  color: var(--text) !important;
  box-shadow: 0 10px 24px rgba(0,17,31,0.08) !important;
}

/* Expander — bigger tap area */
details > summary {
  min-height: var(--tap) !important;
  display: flex !important;
  align-items: center !important;
  padding: 10px 14px !important;
  font-size: 14px !important;
  font-family: 'Manrope', sans-serif !important;
  cursor: pointer !important;
  touch-action: manipulation !important;
  color: var(--text) !important;
  font-weight: 600 !important;
}
[data-testid="stExpander"] {
  background: rgba(3,77,112,0.82) !important;
  border: 1.5px solid rgba(119,196,165,0.12) !important;
  border-radius: var(--radius) !important;
  margin-bottom: 10px !important;
  box-shadow: 0 16px 32px rgba(0,17,31,0.08), inset 0 1px 0 rgba(255,255,255,0.16) !important;
  backdrop-filter: blur(18px) saturate(140%) !important;
  -webkit-backdrop-filter: blur(18px) saturate(140%) !important;
}
[data-testid="stExpander"] > div[role="button"] {
  padding: 14px 15px !important;
  min-height: var(--tap) !important;
  background: linear-gradient(180deg, rgba(4,112,162,0.24), rgba(2,60,87,0.54)) !important;
}
[data-testid="stExpander"] > div[role="button"] p {
  font-size: 13px !important;
  line-height: 1.45 !important;
  font-weight: 700 !important;
}

/* Plotly chart — transparent / light themed */
.js-plotly-plot { background: transparent !important; }

/* Alert / Success messages */
[data-testid="stAlert"] { border-radius: 12px !important; font-size: 14px !important; }

/* Remove extra Streamlit whitespace */
.element-container { margin-bottom: 0 !important; }
.element-container:first-child { margin-top: 0 !important; padding-top: 0 !important; }
.element-container:last-child { margin-bottom: 0 !important; padding-bottom: 0 !important; }
.stMarkdown { line-height: 1 !important; }
.block-container > div > div > div { gap: 4px !important; }

/* Spinner */
[data-testid="stSpinner"] { color: var(--accent) !important; }

/* Dropdown menu light override */
[data-baseweb="popover"] {
  background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(236,250,247,0.88)) !important;
  border: 1px solid rgba(2,60,87,0.14) !important;
  border-radius: 16px !important;
  box-shadow: var(--shadow2) !important;
  backdrop-filter: blur(18px) saturate(145%) !important;
  -webkit-backdrop-filter: blur(18px) saturate(145%) !important;
}
[data-baseweb="menu"] {
  background: transparent !important;
  color: #00111f !important;
}
[data-baseweb="menu"] li {
  color: #00111f !important;
  font-family: 'Manrope', sans-serif !important;
  background: transparent !important;
  border-radius: 12px !important;
}
[data-baseweb="menu"] li:hover {
  background: linear-gradient(135deg, rgba(6,194,172,0.14), rgba(119,196,165,0.18)) !important;
}
[data-baseweb="menu"] li[aria-selected="true"] {
  background: linear-gradient(135deg, rgba(2,60,87,0.12), rgba(6,194,172,0.18)) !important;
  color: #00111f !important;
}

/* ── Animations ── */
@keyframes slideUp   { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }
@keyframes float     { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-9px)} }
@keyframes popIn     { 0%{opacity:0;transform:scale(.7)} 70%{transform:scale(1.08)} 100%{opacity:1;transform:scale(1)} }
@keyframes fadeScale { 0%{opacity:0;transform:scale(.95)} 100%{opacity:1;transform:scale(1)} }
@keyframes scorePop  { 0%{opacity:0;transform:scale(0.5) rotate(-10deg)} 70%{transform:scale(1.15)} 100%{opacity:1;transform:scale(1)} }
@keyframes bgShift   { 0%{background-position:0% 0%} 50%{background-position:100% 40%} 100%{background-position:20% 100%} }
@keyframes bgFloat   { 0%{transform:translate3d(0,0,0) scale(1)} 50%{transform:translate3d(-1.5%,1.2%,0) scale(1.03)} 100%{transform:translate3d(1.5%,-1%,0) scale(1.01)} }
@keyframes prizeDrift { 0%,100%{transform:translate3d(0,0,0) rotate(0deg)} 25%{transform:translate3d(0,-4px,0) rotate(-.6deg)} 50%{transform:translate3d(0,-7px,0) rotate(.4deg)} 75%{transform:translate3d(0,-3px,0) rotate(-.35deg)} }
@keyframes prizeZoom { 0%,100%{transform:scale(1)} 50%{transform:scale(1.035)} }
@keyframes chaosTilt { 0%,100%{transform:rotate(0deg) scale(1)} 18%{transform:rotate(-1deg) scale(1.01)} 42%{transform:rotate(1deg) scale(1.015)} 64%{transform:rotate(-0.8deg) scale(0.995)} }
@keyframes cloudDrift { 0%,100%{transform:translateX(0)} 30%{transform:translateX(-2px)} 60%{transform:translateX(2px)} }
@keyframes chaosJolt { 0%,100%{transform:translate(0,0)} 18%{transform:translate(-1px,1px)} 22%{transform:translate(2px,-1px)} 48%{transform:translate(-2px,0)} 52%{transform:translate(1px,1px)} 74%{transform:translate(0,-1px)} }
@keyframes chaosSliceA { 0%,100%{transform:translate(-2px,1px)} 30%{transform:translate(-4px,1px)} 60%{transform:translate(-1px,-1px)} }
@keyframes chaosSliceB { 0%,100%{transform:translate(2px,-1px)} 28%{transform:translate(4px,-2px)} 64%{transform:translate(1px,1px)} }
/* Card entrance */
.element-container { animation: slideUp .38s cubic-bezier(.22,1,.36,1) both; }
.element-container:nth-child(1){animation-delay:.04s}
.element-container:nth-child(2){animation-delay:.09s}
.element-container:nth-child(3){animation-delay:.13s}
.element-container:nth-child(4){animation-delay:.17s}
.element-container:nth-child(5){animation-delay:.21s}
.element-container:nth-child(6){animation-delay:.24s}
.element-container:nth-child(7){animation-delay:.27s}
.element-container:nth-child(8){animation-delay:.30s}

/* Expander open state glow */
[data-testid="stExpander"][open] {
  border-color: rgba(6,194,172,0.35) !important;
  box-shadow: 0 6px 28px rgba(2,60,87,0.12) !important;
}
/* Expander header hover */
details > summary:hover {
  background: var(--s2) !important;
  border-radius: var(--radius) !important;
}

/* Floating emojis */
.float-em { display:inline-block; animation: float 3s ease-in-out infinite; }
.float-em:nth-child(2) { animation-delay:.4s; }
.float-em:nth-child(3) { animation-delay:.8s; }
.float-em:nth-child(4) { animation-delay:1.2s; }

/* Per-pain color borders on expanders */
.pain-wrap-0 [data-testid="stExpander"] { border-left: 3px solid #FF6B6B !important; }
.pain-wrap-1 [data-testid="stExpander"] { border-left: 3px solid #023c57 !important; }
.pain-wrap-2 [data-testid="stExpander"] { border-left: 3px solid #06c2ac !important; }
.pain-wrap-3 [data-testid="stExpander"] { border-left: 3px solid #1df8de !important; }
.pain-wrap-4 [data-testid="stExpander"] { border-left: 3px solid #77c4a5 !important; }
.pain-wrap-0 [data-testid="stExpander"][open] { box-shadow: 0 6px 28px rgba(2,60,87,0.14) !important; }
.pain-wrap-1 [data-testid="stExpander"][open] { box-shadow: 0 6px 28px #023c5722 !important; }
.pain-wrap-2 [data-testid="stExpander"][open] { box-shadow: 0 6px 28px #06c2ac22 !important; }
.pain-wrap-3 [data-testid="stExpander"][open] { box-shadow: 0 6px 28px rgba(29,248,222,0.14) !important; }
.pain-wrap-4 [data-testid="stExpander"][open] { box-shadow: 0 6px 28px rgba(119,196,165,0.14) !important; }

/* CSS Score Ring */
.score-ring-wrap { display:flex; flex-direction:column; align-items:center; margin:4px 0 12px; animation: popIn .5s cubic-bezier(.22,1,.36,1) both .1s; }
.score-ring {
  width:140px; height:140px; border-radius:50%; position:relative;
  display:flex; align-items:center; justify-content:center;
  background: conic-gradient(var(--accent2) var(--pct), rgba(2,60,87,0.10) var(--pct));
  box-shadow: 0 20px 36px rgba(0,17,31,0.14);
}
.score-hole {
  width:106px; height:106px; border-radius:50%;
  background:
    linear-gradient(180deg, rgba(2,60,87,0.82), rgba(0,17,31,0.90)),
    radial-gradient(circle at 30% 22%, rgba(29,248,222,0.12), transparent 28%);
  border: 1px solid rgba(255,255,255,0.18);
  position:absolute;
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.14), 0 12px 24px rgba(0,17,31,0.18);
  backdrop-filter: blur(14px) saturate(140%);
  -webkit-backdrop-filter: blur(14px) saturate(140%);
}
.score-num  { font-size:38px; font-weight:800; color:#ffffff !important; line-height:1; text-shadow: 0 6px 18px rgba(0,0,0,0.24); }
.score-denom{ font-size:13px; color:rgba(255,255,255,0.82); font-weight:700; }

/* Result title pop */
.result-title { animation: scorePop .5s cubic-bezier(.22,1,.36,1) both .3s; }

/* Stat number shimmer on leaderboard */
.stat-num {
  background: linear-gradient(90deg, var(--accent), var(--accent2), var(--green), var(--accent));
  background-size: 200% auto;
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  animation: shimmer 3s linear infinite;
}
@media (max-width: 520px) {
  .stats-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .hero-title {
    white-space: normal;
  }
}

</style>
""", unsafe_allow_html=True)

st.markdown(f"<style>{(APP_DIR / 'static' / 'polish.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
#  SESSION STATE INITIALISATION
# ─────────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "screen":           "register",
        "player":           None,
        "game_cards":       [],
        "selections":       {i: {"answer": None, "is_correct": None} for i in range(gd.NUM_PAINS)},
        "active_pain":      0,
        "game_start_time":  None,
        "time_left":        gd.GAME_DURATION,
        "submitted":        False,
        "score":            0,
        "session_id":       None,
        "last_session_id":  None,
        "answer_feedback": None,
        "admin_panel_visible": False,
        "admin_login_visible": False,
        "admin_authenticated": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()


def _admin_credentials() -> tuple[str | None, str | None]:
    try:
        username = st.secrets.get("ADMIN_USERNAME")
        password = st.secrets.get("ADMIN_PASSWORD")
    except Exception:
        username = None
        password = None
    return (
        username or os.getenv("ADMIN_USERNAME") or "sneha",
        password or os.getenv("ADMIN_PASSWORD") or "@Rapyder123",
    )


def _handle_admin_access_signal() -> None:
    access_signal = st.query_params.get("admin_access")
    if not access_signal:
        return
    st.session_state.admin_login_visible = True
    st.query_params.clear()


_handle_admin_access_signal()


# ─────────────────────────────────────────────────────────────
#  NAV
# ─────────────────────────────────────────────────────────────
def go(screen: str):
    st.query_params.clear()
    st.session_state.screen = screen
    st.rerun()


def _toast(message: str, icon: str | None = None) -> None:
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
    return None


def _mobile_haptic(duration_ms: int = 18) -> None:
    components.html(
        f"""
        <script>
        if (navigator.vibrate) {{
          navigator.vibrate({duration_ms});
        }}
        </script>
        """,
        height=0,
        width=0,
    )


@st.cache_data
def _image_data_uri(path: str) -> str:
    image_path = Path(path)
    suffix = image_path.suffix.lower().lstrip(".") or "png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/{suffix};base64,{encoded}"


@st.cache_data
def _video_data_uri(path: str) -> str:
    video_path = Path(path)
    suffix = video_path.suffix.lower()
    mime = "video/quicktime" if suffix == ".mov" else f"video/{suffix.lstrip('.') or 'mp4'}"
    encoded = base64.b64encode(video_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _image_markup(path: Path, alt: str, *, height_px: int = 140) -> str:
    if not path.exists():
        fallback = alt.replace(" prize", "")
        return (
            f"<div style='height:{height_px}px;display:flex;align-items:center;"
            f"justify-content:center;color:var(--muted)'>{fallback}</div>"
        )
    image_src = _image_data_uri(str(path))
    return (
        f'<img src="{image_src}" alt="{alt}" '
        f'style="width:100%;height:{height_px}px;object-fit:cover;display:block;background:#fff;">'
    )


def _video_markup(path: Path, *, height_px: int = 140) -> str:
    if not path.exists():
        return (
            f"<div style='height:{height_px}px;display:flex;align-items:center;"
            f"justify-content:center;color:var(--muted)'>Smartwatch</div>"
        )
    video_src = _video_data_uri(str(path))
    video_type = "video/quicktime" if path.suffix.lower() == ".mov" else "video/mp4"
    return (
        f'<video autoplay muted loop playsinline preload="auto" '
        f'disablepictureinpicture controlslist="nodownload nofullscreen noremoteplayback" '
        f'style="width:100%;height:{height_px}px;object-fit:cover;display:block;background:radial-gradient(circle at 50% 30%, #ffffff, #dbeafe 40%, #0f172a 100%);">'
        f'<source src="{video_src}" type="{video_type}">'
        f"</video>"
    )


def _prize_card_html(media_html: str, label: str, winners_text: str) -> str:
    return f"""
    <div class="prize-card" style="{PRIZE_CARD_STYLE}">
      <div class="prize-media" style="width:100%">{media_html}</div>
      <div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#335369;padding:10px 0 4px;text-align:center">{label}</div>
      <div style="font-size:12px;font-weight:700;color:#00111f;padding-bottom:10px">{winners_text}</div>
    </div>
    """


def _render_admin_access() -> None:
    if st.session_state.admin_login_visible and not st.session_state.admin_authenticated:
        configured_username, configured_password = _admin_credentials()
        with st.form("admin_login_form", clear_on_submit=True):
            username = st.text_input("Admin Username", key="admin_username")
            password = st.text_input("Admin Password", type="password", key="admin_password")
            submitted = st.form_submit_button("Unlock Admin", use_container_width=True, type="primary")

        if submitted:
            if not configured_password:
                st.error("Admin credentials are not configured. Set `ADMIN_PASSWORD` in Streamlit secrets or environment.")
            elif username == configured_username and password == configured_password:
                st.session_state.admin_authenticated = True
                st.session_state.admin_panel_visible = True
                st.session_state.admin_login_visible = False
                st.rerun()
            else:
                st.error("Invalid admin credentials.")

    if st.session_state.admin_authenticated and st.session_state.admin_panel_visible:
        _render_admin_panel_live()


@st.fragment(run_every="5s")
def _render_admin_panel_live() -> None:
    admin_rows = db.get_admin_panel_data()
    admin_df = pd.DataFrame(admin_rows, columns=[
        "player_id",
        "name",
        "company",
        "created_at",
        "last_seen",
        "total_plays",
        "best_score",
        "best_time",
        "leaderboard_session_id",
        "leaderboard_score",
        "leaderboard_time_used",
        "leaderboard_is_perfect",
        "leaderboard_timed_out",
        "leaderboard_completed_at",
        "data_source",
        "sync_status",
        "last_error",
    ])

    st.markdown(
        """
        <div class="section-panel" style="margin-top:14px">
          <div class="section-kicker">Admin Panel</div>
          <div class="muted" style="text-align:center;line-height:1.6">
            Live registration and leaderboard account data from the event database.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    export_path = db.export_admin_workbook()
    st.download_button(
        "Download Admin Excel",
        data=export_path.read_bytes(),
        file_name=export_path.name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="admin_download_excel",
    )

    st.dataframe(
        admin_df,
        use_container_width=True,
        hide_index=True,
    )


@st.fragment(run_every="5s")
def _render_leaderboard_live() -> None:
    try:
        entries = db.get_leaderboard(limit=5)
        stats = db.get_stats()
    except Exception:
        entries = []
        stats = {
            "total_players": 0,
            "total_sessions": 0,
            "perfect_count": 0,
            "avg_score": 0.0,
            "pain_accuracy": [],
        }
        st.warning("Leaderboard data is temporarily unavailable. Pull to refresh or try again in a moment.")

    if not entries:
        st.markdown(
            '<div style="text-align:center;padding:40px;color:var(--muted)">No players yet — be the first!</div>',
            unsafe_allow_html=True,
        )
    else:
        for idx, row in enumerate(entries):
            rank_cls   = ["r1", "r2", "r3"][idx] if idx < 3 else ""
            rank_emoji = ge.format_rank(idx)
            perf_badge = " 🌟" if row["is_perfect"] else ""
            time_str   = ge.format_time(row["time_used"])
            st.markdown(f"""
            <div class="lb-item">
              <div class="lb-rank {rank_cls}">{rank_emoji}</div>
              <div class="lb-info">
                <div class="lb-pn" title="{row['name']}">{row['name']}{perf_badge}</div>
                <div class="lb-co" title="{row['company']}">{row['company']}</div>
              </div>
              <div>
                <div class="lb-sc">{row['score']}/{gd.NUM_PAINS}</div>
                <div class="lb-time">{time_str}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="cc-card" style="text-align:center">
      <div style="display:flex;justify-content:space-around;flex-wrap:wrap;gap:10px">
        <div><div class="stat-num" style="font-size:20px">{stats['total_players']}</div><div class="stat-label">Players</div></div>
        <div><div class="stat-num" style="font-size:20px">{stats['total_sessions']}</div><div class="stat-label">Plays</div></div>
        <div><div class="stat-num" style="font-size:20px">{stats['perfect_count']}</div><div class="stat-label">Perfect</div></div>
        <div><div class="stat-num" style="font-size:20px">{stats['avg_score'] or '—'}</div><div class="stat-label">Avg Score</div></div>
      </div>
    </div>
    """, unsafe_allow_html=True)





# ─────────────────────────────────────────────────────────────
#  ██  SCREEN: REGISTER
# ─────────────────────────────────────────────────────────────
def screen_register():
    try:
        stats = db.get_stats()
    except Exception:
        stats = {"total_players": 0, "total_sessions": 0}

    if LOGO_PATH.exists():
        logo_src = _image_data_uri(str(LOGO_PATH))
        st.markdown(
            f"""
            <div class="brand-header">
              <img src="{logo_src}" alt="Cloudeva logo">
              <span class="event-label">The event challenge</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown("""
        <div class="logo-bar" style="justify-content:center;">
          <div class="logo-chip">CE</div>
          <div class="logo-text">Cloudeva</div>
        </div>
        """, unsafe_allow_html=True)

    watch_media_html = (
        '<video autoplay muted loop playsinline preload="metadata" aria-label="Animated golden trophy with money and coins" '
        'style="width:100%;height:150px;object-fit:contain;display:block;">'
        '<source src="app/static/trophy-prize.mp4" type="video/mp4">'
        '</video>'
    )

    st.markdown(f"""
    <div class="hero-layout">
    <div class="hero-panel">
      <div class="hero-kicker">Cloud Governance Challenge</div>
      <h1 class="hero-title"><span class="chaos-word">CLOUD</span> <span class="chaos-word">CHAOS</span></h1>
      <p class="hero-sub">
        Read the signal. Beat the clock. Decide whether each cloud
        problem is paired with the right impact and owner.
      </p>
      <div class="challenge-facts">
        <span><strong>{gd.GAME_DURATION}s</strong>on the clock</span>
        <span><strong>{gd.NUM_PAINS} cards</strong>right or wrong</span>
        <span><strong>3 winners</strong>smartwatch prizes</span>
      </div>
    </div>
    <aside class="prize-banner hero-prize" aria-label="Event prize">
      <div class="prize-top-label">Up for grabs</div>
      {_prize_card_html(watch_media_html, "Smartwatch", "3 winners · announced at the event")}
    </aside>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="form-shell">
      <div class="form-kicker">Ready to make the call?</div>
      <div class="muted" style="text-align:center;line-height:1.6">
        Add your details. The timer starts when you begin.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Registration Form
    with st.form("register_form", clear_on_submit=False):
        name    = st.text_input("Your name", placeholder="Enter your name", key="reg_name")
        company = st.text_input("Company", placeholder="Enter your company", key="reg_company")
        submitted = st.form_submit_button(
            "Start the challenge →",
            use_container_width=True,
            type="primary",
        )


    if submitted:
        if not name.strip() or not company.strip():
            _toast("Please fill in both fields.", None)
            st.error("Please fill in both fields.")
        else:
            try:
                with st.spinner("Saving your registration..."):
                    player, _ = db.upsert_player(name, company)
                    cards = gd.get_shuffled_cards()
            except ValueError as e:
                _toast(str(e), None)
                st.error(str(e))
            except Exception as e:
                _toast("Registration could not be saved right now.", None)
                st.error(f"Registration could not be saved right now: {e}")
            else:
                try:
                    db.log_event(player.id, "game_start", json.dumps({"company": company}))
                except Exception:
                    pass
                st.session_state.update({
                    "player":           {"id": player.id, "name": player.name,
                                         "company": player.company},
                    "game_cards":       cards,
                    "selections":       {i: {"answer": None, "is_correct": None} for i in range(gd.NUM_PAINS)},
                    "active_pain":      0,
                    "game_start_time":  time.time(),
                    "time_left":        gd.GAME_DURATION,
                    "submitted":        False,
                    "score":            0,
                    "session_id":       None,
                    "answer_feedback": None,
                })
                _mobile_haptic()
                go("game")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("🏆  View Leaderboard", use_container_width=True, key="reg_lb_btn"):
        go("leaderboard")
    admin_label = "Hide Admin Panel" if (
        st.session_state.admin_authenticated and
        (st.session_state.admin_panel_visible or st.session_state.admin_login_visible)
    ) else "Admin Login"
    if st.button(admin_label, use_container_width=True, key="reg_admin_btn"):
        if st.session_state.admin_authenticated and (
            st.session_state.admin_panel_visible or st.session_state.admin_login_visible
        ):
            st.session_state.admin_panel_visible = False
            st.session_state.admin_login_visible = False
        elif st.session_state.admin_login_visible:
            st.session_state.admin_login_visible = False
        elif st.session_state.admin_authenticated:
            st.session_state.admin_panel_visible = True
        else:
            st.session_state.admin_login_visible = True
        st.rerun()
    _render_admin_access()
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
#  ██  SCREEN: GAME
# ─────────────────────────────────────────────────────────────
def screen_game():
    if not st.session_state.player or st.session_state.submitted:
        go("register")
        return

    timeout_flag = st.query_params.get("timeout")
    if timeout_flag == "1" and not st.session_state.submitted:
        st.query_params.clear()
        _do_submit(timed_out=True)
        return

    player = st.session_state.player
    sels = st.session_state.selections
    cards = st.session_state.game_cards or gd.get_shuffled_cards()
    st.session_state.game_cards = cards
    start_time = st.session_state.game_start_time or time.time()

    def _next_incomplete_card() -> int:
        for display_idx, card in enumerate(cards):
            if st.session_state.selections[card["orig_idx"]]["answer"] is None:
                return display_idx
        return gd.NUM_PAINS - 1

    def _update_answer(card_idx: int, answer: bool) -> None:
        card = cards[card_idx]
        is_correct = answer == card["is_right"]
        st.session_state.selections[card["orig_idx"]] = {
            "answer": answer,
            "is_correct": is_correct,
        }
        st.session_state.active_pain = _next_incomplete_card()
        st.session_state.answer_feedback = f"Card {card_idx + 1} saved · {'Right' if answer else 'Wrong'}"
        _mobile_haptic()
        st.rerun()

    active_pain = st.session_state.get("active_pain", 0)
    if active_pain < 0 or active_pain >= gd.NUM_PAINS:
        active_pain = _next_incomplete_card()
        st.session_state.active_pain = active_pain

    elapsed = time.time() - start_time
    time_left = max(0, int(gd.GAME_DURATION - elapsed))
    st.session_state.time_left = time_left

    filled = sum(1 for s in sels.values() if s["answer"] is not None)
    initial = player["name"][0].upper()
    danger_cls = "danger" if time_left <= 15 else ""
    timer_pct = time_left / gd.GAME_DURATION
    bar_color = "#DC2626" if time_left <= 15 else ("#0891B2" if time_left <= 30 else "#06c2ac")

    st.markdown(f"""
    <div class="topbar">
      <div style="display:flex;align-items:center;gap:10px;flex:1;min-width:0">
        <div class="p-avatar">{initial}</div>
        <div class="player-meta">
          <div class="p-name">{player['name']}</div>
          <div class="p-co">{player['company']}</div>
        </div>
      </div>
      <div class="timer-wrap">
        <div class="timer-lbl">SEC LEFT</div>
        <div id="cc-timer-num" class="timer-num {danger_cls}">{time_left}</div>
      </div>
      <div class="score-chip">{filled}<span style="font-size:11px;opacity:.6">/{gd.NUM_PAINS}</span></div>
    </div>
    <div style="height:5px;border-radius:3px;background:rgba(2,60,87,0.10);overflow:hidden;margin-bottom:12px">
      <div id="cc-timer-fill" style="height:100%;width:{int(timer_pct*100)}%;background:{bar_color};
           border-radius:3px;transition:width .3s linear,background .3s"></div>
    </div>
    """, unsafe_allow_html=True)

    deadline_ms = int((start_time + gd.GAME_DURATION) * 1000)
    components.html(
        f"""
        <script>
        const deadline = {deadline_ms};
        const totalSeconds = {gd.GAME_DURATION};
        const hostWindow = window.parent;
        const timerEl = hostWindow.document.getElementById("cc-timer-num");
        const fillEl = hostWindow.document.getElementById("cc-timer-fill");
        let redirected = false;

        function paintTimer() {{
          const msLeft = deadline - Date.now();
          const secsLeft = Math.max(0, Math.ceil(msLeft / 1000));
          const pct = Math.max(0, Math.min(100, (msLeft / (totalSeconds * 1000)) * 100));

          if (timerEl) {{
            timerEl.textContent = String(secsLeft);
            timerEl.classList.toggle("danger", secsLeft <= 15);
          }}

          if (fillEl) {{
            fillEl.style.width = pct + "%";
            fillEl.style.background = secsLeft <= 15 ? "#DC2626" : (secsLeft <= 30 ? "#0891B2" : "#06c2ac");
          }}

          if (msLeft <= 0 && !redirected) {{
            redirected = true;
            const nextUrl = new URL(hostWindow.location.href);
            nextUrl.searchParams.set("timeout", "1");
            hostWindow.location.replace(nextUrl.toString());
          }}
        }}

        paintTimer();
        const intervalId = hostWindow.setInterval(() => {{
          paintTimer();
          if (redirected) {{
            hostWindow.clearInterval(intervalId);
          }}
        }}, 250);
        </script>
        """,
        height=0,
        width=0,
    )

    phase = "Mission complete" if filled == gd.NUM_PAINS else ("Final stretch" if filled >= gd.NUM_PAINS - 2 else "Trust your cloud instincts")
    receipt = st.session_state.answer_feedback or "Six signals. One shot at the top."
    st.markdown(f"""
    <div class="mission-hud">
      <div><div class="mission-label"><span class="live-dot"></span> CLOUD CONTROL</div><div class="mission-phase">{phase}</div><div class="answer-receipt" role="status">{receipt}</div></div>
      <div class="mission-meter" style="--progress:{int(filled / gd.NUM_PAINS * 100)}%"><span>{filled}<small>/{gd.NUM_PAINS}</small></span></div>
    </div>
    """, unsafe_allow_html=True)
    with st.container(key="question_navigation"):
        nav = st.columns(gd.NUM_PAINS)
        for i, item in enumerate(cards):
            done = sels[item["orig_idx"]]["answer"] is not None
            if nav[i].button(
                f"{i + 1}{' ✓' if done else ''}", key=f"question_nav_{i}",
                type="primary" if i == active_pain else "secondary",
                use_container_width=True, help=f"Review card {i + 1}" if done else f"Go to card {i + 1}",
            ):
                st.session_state.active_pain = i
                st.session_state.answer_feedback = None
                st.rerun()

    display_idx = active_pain
    card = cards[display_idx]
    sel_i = sels[card["orig_idx"]]
    answered = sel_i["answer"] is not None
    signal_names = ["Cost radar", "Service watch", "Risk scanner", "Accountability", "Delivery pulse", "Hybrid watch"]
    signal_icons = ["↗", "◈", "⌁", "◎", "ϟ", "⬡"]
    signal_name = signal_names[card["orig_idx"] % len(signal_names)]
    signal_icon = signal_icons[card["orig_idx"] % len(signal_icons)]
    with st.container(key="active_question"):
        st.markdown(f"""
        <article class="qa-card">
          <div class="qa-eyebrow"><span>SIGNAL {display_idx + 1:02d} / {gd.NUM_PAINS:02d}</span><span>{'✓ Answer saved' if answered else 'Awaiting your verdict'}</span></div>
          <div class="signal-category"><span class="signal-icon" aria-hidden="true">{signal_icon}</span><span>{signal_name}</span></div>
          <h2 class="qa-title">{card['pain']}</h2>
          <p class="qa-prompt">The diagnosis is in. Does this pairing check out?</p>
          <dl class="qa-pair">
            <div><dt><span aria-hidden="true">↗</span> Impact</dt><dd>{card['impact']}</dd></div>
            <div><dt><span aria-hidden="true">◎</span> Owner</dt><dd>{card['owner']}</dd></div>
          </dl>
        </article>
        """, unsafe_allow_html=True)
        right_col, wrong_col = st.columns(2)
        if right_col.button("✓  Right", key=f"right_{display_idx}", use_container_width=True,
                            type="primary" if sel_i["answer"] is True else "secondary"):
            _update_answer(display_idx, True)
        if wrong_col.button("✕  Wrong", key=f"wrong_{display_idx}", use_container_width=True,
                            type="primary" if sel_i["answer"] is False else "secondary"):
            _update_answer(display_idx, False)
        if answered:
            choice = "Right" if sel_i["answer"] else "Wrong"
            st.caption(f"Saved: {choice}. Tap either answer to change your call.")
        else:
            st.caption("Choose an answer to move to the next card.")

    filled = sum(1 for s in sels.values() if s["answer"] is not None)
    remaining = gd.NUM_PAINS - filled
    if remaining == 0:
        st.markdown('<div class="mission-ready"><span aria-hidden="true">✦</span><div><strong>All signals decoded.</strong><br>Review your calls or reveal your score.</div></div>', unsafe_allow_html=True)
    btn_label = "Reveal my score →" if remaining == 0 else f"{remaining} signals left to decode"
    st.markdown("""
    <div style="margin-top:10px;padding-top:12px;
         border-top:1px solid var(--border)">
    """, unsafe_allow_html=True)
    if remaining == 0:
        if st.button(btn_label, use_container_width=True, type="primary", key="fab_submit", help="Submit once you are happy with your matches."):
            _do_submit(timed_out=False)
    else:
        st.button(btn_label, use_container_width=True, type="primary", key="fab_submit_dis", disabled=True, help="Answer every card to submit.")
        st.caption(f"Complete {remaining} more card {'decision' if remaining == 1 else 'decisions'} to unlock submit.")
    st.markdown("</div>", unsafe_allow_html=True)


# --------------------------
#  SUBMIT
# ─────────────────────────────────────────────────────────────
def _do_submit(timed_out: bool = False):
    start_time = st.session_state.game_start_time or time.time()
    elapsed   = time.time() - start_time
    time_used = min(int(elapsed), gd.GAME_DURATION)
    sels      = st.session_state.selections
    score     = ge.calculate_score(sels)
    player    = st.session_state.player

    try:
        with st.spinner("Saving your result..."):
            session = db.save_game_session(
                player_id  = player["id"],
                score      = score,
                time_used  = time_used,
                timed_out  = timed_out,
                selections = sels,
            )
            db.log_event(player["id"], "game_submit",
                         json.dumps({"score": score, "time_used": time_used, "timed_out": timed_out}))
    except Exception as e:
        try:
            db.record_game_session_failover(
                player_id=player["id"],
                name=player["name"],
                company=player["company"],
                score=score,
                time_used=time_used,
                timed_out=timed_out,
                selections=sels,
                error=str(e),
            )
        except Exception:
            pass
        _toast("Your game result could not be saved right now.", None)
        st.error("Your game result could not be saved right now. Please try again.")
        return

    st.session_state.update({
        "submitted":       True,
        "score":           score,
        "session_id":      session.id,
        "last_session_id": session.id,
    })
    go("results")


# ─────────────────────────────────────────────────────────────
#  ██  SCREEN: RESULTS
# ─────────────────────────────────────────────────────────────
def screen_results():
    score     = st.session_state.score
    sels      = st.session_state.selections
    tier      = ge.get_result_tier(score)
    breakdown = ge.build_breakdown(sels)
    start_time = st.session_state.game_start_time or time.time()
    elapsed   = time.time() - start_time
    time_used = min(int(elapsed), gd.GAME_DURATION)

    st.markdown('<div class="results-shell">', unsafe_allow_html=True)
    # Pure-CSS score ring (no Plotly, instant on mobile)
    pct_css = f"{int((score / gd.NUM_PAINS) * 100)}%"
    st.markdown(f"""
    <div class="results-panel">
      <div class="score-ring-wrap">
        <div class="score-ring" style="--pct:{pct_css}">
          <div class="score-hole">
            <div class="score-num">{score}</div>
            <div class="score-denom">/ {gd.NUM_PAINS}</div>
          </div>
        </div>
      </div>
      <div class="result-title">{tier["emoji"]} {tier["title"]}</div>
      <p class="result-sub">{tier["sub"]}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="eva-box">
      <div class="eva-lbl">⚡ EVA gets this right every morning</div>
      <div class="eva-txt">{tier['eva']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Richer 2-per-row breakdown
    colors  = gd.PAIN_COLORS
    labels  = gd.PAIN_LABELS
    rows_html = ""
    for row_start in range(0, gd.NUM_PAINS, 2):
        cells = ""
        for i in range(row_start, min(row_start + 2, gd.NUM_PAINS)):
            bd = breakdown[i]
            col = colors[i]
            ic = "✅" if bd["both_correct"] else "❌"
            answer_label = "Right" if bd["answer"] is True else ("Wrong" if bd["answer"] is False else "No answer")
            expected_label = "Right" if bd["expected"] else "Wrong"
            cells += f"""
            <div class="result-breakdown-card" style="border-top-color:{col};">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                <span style="font-size:9px;font-weight:700;letter-spacing:1px;
                     text-transform:uppercase;color:{col}">{labels[i]}</span>
                <span style="font-size:18px">{ic}</span>
              </div>
              <div style="font-size:11px;color:var(--text);font-weight:600;margin-bottom:6px;
                   line-height:1.3">{bd['pain_text']}</div>
              <div style="font-size:10px;color:var(--muted);line-height:1.45">
                You said: <span style="color:{'#059669' if bd['both_correct'] else '#DC2626'}">{answer_label}</span><br>
                Correct call: <span style="color:#77c4a5">{expected_label}</span>
              </div>
            </div>"""
        rows_html += f'<div class="result-breakdown-row">{cells}</div>'
    # If odd number, last card is full-width
    st.markdown(f'<div class="results-panel">{rows_html}</div>', unsafe_allow_html=True)

    if score == gd.NUM_PAINS:
        st.markdown("""
        <div class="lucky-draw-card">
          <div style="font-size:22px;margin-bottom:4px">🎰</div>
          <div style="font-weight:800;color:#ffffff">You're in the lucky draw!</div>
          <div style="font-size:11px;color:var(--muted);margin-top:3px">Winner announced at the event</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        f'<p class="muted" style="text-align:center;margin:10px 0">Completed in '
        f'<span class="mono" style="color:var(--accent);font-weight:700">{ge.format_time(time_used)}</span></p>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    mascot_path = APP_DIR / "static" / "mascot_cool_cutout.png"
    mascot_src = _image_data_uri(str(mascot_path)) if mascot_path.exists() else ""
    if mascot_src:
        st.markdown(
            f"""
            <div class="final-step-card">
              <img class="final-step-mascot" src="{mascot_src}" alt="Cloudeva mascot">
              <div class="final-step-copy">
                <div class="final-step-kicker">Final Step</div>
                <div class="final-step-text highlight"><strong>register now<br>to complete the challenge</strong></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <a class="cta-link" href="https://app.cloudeva.ai/auth/register" target="_blank" rel="noopener noreferrer">
          <span class="cta-copy">
            <span class="cta-text primary">Start Free Preview →</span>
            <span class="cta-text alt">Win Smartwatch →</span>
          </span>
        </a>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🏆  Leaderboard", use_container_width=True, key="res_lb"):
        go("leaderboard")


# ─────────────────────────────────────────────────────────────
#  ██  SCREEN: LEADERBOARD
# ─────────────────────────────────────────────────────────────
def screen_leaderboard():
    components.html(
        """
        <script>
        const hostWindow = window.parent;
        const mainSection = hostWindow.document.querySelector('section.main');
        const appView = hostWindow.document.querySelector('[data-testid="stAppViewContainer"]');
        hostWindow.scrollTo({top: 0, behavior: 'instant'});
        if (mainSection) {
          mainSection.scrollTo({top: 0, behavior: 'instant'});
        }
        if (appView) {
          appView.scrollTo({top: 0, behavior: 'instant'});
        }
        </script>
        """,
        height=0,
        width=0,
    )
    st.markdown('<div class="lb-title">🏆 Leaderboard</div>', unsafe_allow_html=True)
    st.markdown('<p class="lb-sub">Top scores from today\'s event</p>', unsafe_allow_html=True)

    _render_leaderboard_live()

    mascot_path = APP_DIR / "static" / "mascot_cool_cutout.png"
    mascot_src = _image_data_uri(str(mascot_path)) if mascot_path.exists() else ""
    if mascot_src:
        st.markdown(
            f"""
            <div class="final-step-card" style="margin-top:20px;margin-bottom:16px">
              <img class="final-step-mascot" src="{mascot_src}" alt="Cloudeva mascot">
              <div class="final-step-copy">
                <div class="final-step-kicker">Experience EVA</div>
                <div class="final-step-text">Unlock full cloud intelligence with your free preview</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <a class="cta-link" href="https://app.cloudeva.ai/auth/register" target="_blank" rel="noopener noreferrer">
          <span class="cta-copy">
            <span class="cta-text primary">Start Free Preview →</span>
            <span class="cta-text alt">Win Smartwatch →</span>
          </span>
        </a>
        """,
        unsafe_allow_html=True,
    )

    c_a, c_b = st.columns(2)
    with c_a:
        if st.button("← Back", use_container_width=True, key="lb_back"):
            go("register")
    with c_b:
        if st.button("🔄  Refresh", use_container_width=True, key="lb_refresh"):
            st.rerun()


# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────
def _reset_for_play_again():
    for k in ["player", "game_cards", "selections", "active_pain",
              "game_start_time", "time_left", "submitted", "score", "session_id"]:
        st.session_state.pop(k, None)
    _init_state()


# ─────────────────────────────────────────────────────────────
#  ROUTER
# ─────────────────────────────────────────────────────────────
SCREENS = {
    "register":    screen_register,
    "game":        screen_game,
    "results":     screen_results,
    "leaderboard": screen_leaderboard,
}
current_screen = SCREENS.get(st.session_state.get("screen", "register"), screen_register)
current_screen()
