"""
app.py — Agentic-Cut v4.1 Web3/Agency Edition
Strictly bold, high-contrast black/neon yellow aesthetic modeled after desh.group.
UI Enriched with Quick Actions and Export Settings.
"""

import os
import traceback
import google.generativeai as genai
from dotenv import load_dotenv
import time
from datetime import datetime
from pathlib import Path
import streamlit as st

# ── Page config MUST be first ─────────────────────────────────────────────
st.set_page_config(
    page_title="AGENTIC-CUT",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

from agent import run_agent, get_video_metadata

# ============================================================
# CSS — Web3/Agency Theme
# ============================================================

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@400;600;800;900&display=swap');

:root {
    /* Core */
    --pure-black:     #000000;
    --pure-white:     #FFFFFF;
    --neon-yellow:    #E5FF00;

    /* Surfaces */
    --surface:        #111111;
    --surface-2:      #191919;
    --input-bg:       #0C0C0C;

    /* Borders */
    --border-soft:    #242424;
    --border-mid:     #333333;

    /* Text */
    --text-primary:   #EEEEEE;
    --text-secondary: #777777;
    --text-muted:     #444444;
    --fog:            #888888;

    /* Accents */
    --accent-amber:   #E5FF00;
    --accent-green:   #39D98A;
    --accent-blue:    #4A9EFF;
    --accent-error:   #FF6B6B;

    /* Fonts */
    --font-display: 'Outfit', sans-serif;
    --font-mono:    'JetBrains Mono', monospace;
    --font-body:    'Outfit', sans-serif;
    
    /* Misc */
    --bg-slate:       #000000;
}

/* === Cursor (system cursor stays visible; JS adds trail overlay) === */
* { caret-color: var(--neon-yellow); box-sizing: border-box; }

/* === Base === */
html, body, [class*="css"] {
    font-family: var(--font-display) !important;
    background-color: var(--pure-black) !important;
    color: var(--text-primary) !important;
}

/* Dot Grid */
.stApp {
    background-color: var(--pure-black);
    background-image: radial-gradient(var(--border-soft) 1px, transparent 1px);
    background-size: 40px 40px;
}

/* Hide Streamlit chrome — but NOT stToolbar (it contains sidebar toggle) */
#MainMenu, footer { display: none !important; }
header { background: transparent !important; box-shadow: none !important; }
[data-testid="stHeader"] { background: transparent !important; }

/* Hide toolbar decoration but keep the sidebar expand button visible */
[data-testid="stToolbar"] {
    background: transparent !important;
    box-shadow: none !important;
    /* Do NOT hide the toolbar — it contains stExpandSidebarButton */
}
/* Hide the Streamlit GitHub badge in the top right */
.viewerBadge_container__1QSob,
.viewerBadge_link__1S137,
.styles_viewerBadge__1yB5_,
[data-testid="stGitHubBadge"] {
    display: none !important;
}

/* Sidebar expand/collapse toggle — subtle dark button with neon accent */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 9999 !important;
    background: rgba(20,20,20,0.85) !important;
    border: 1px solid rgba(229,255,0,0.35) !important;
    border-radius: 8px !important;
    box-shadow: 0 0 8px rgba(229,255,0,0.15), inset 0 0 0 1px rgba(229,255,0,0.08) !important;
    backdrop-filter: blur(8px) !important;
    transition: border-color 200ms ease, box-shadow 200ms ease, transform 150ms ease !important;
}
[data-testid="stExpandSidebarButton"]:hover,
[data-testid="stSidebarCollapseButton"]:hover,
[data-testid="collapsedControl"]:hover {
    border-color: rgba(229,255,0,0.75) !important;
    box-shadow: 0 0 20px rgba(229,255,0,0.35), inset 0 0 0 1px rgba(229,255,0,0.15) !important;
    transform: scale(1.06) !important;
}
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="collapsedControl"] svg {
    fill: rgba(229,255,0,0.85) !important;
}

/* === Typography === */
h1, h2, h3 {
    font-family: var(--font-display) !important;
    color: var(--pure-white) !important;
    font-weight: 900 !important;
    letter-spacing: -0.04em;
}
.mono-text { font-family: var(--font-mono) !important; }

/* === Top Nav === */
.top-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 0 1.5rem 0;
    margin-top: -2.5rem;
    padding-right: 130px; /* prevent overlap with Streamlit toolbar */
    border-bottom: 1px solid var(--border-soft);
    margin-bottom: 0;
}
.nav-brand {
    font-family: var(--font-display);
    font-size: 1.6rem;
    font-weight: 900;
    letter-spacing: -0.05em;
    display: flex;
    align-items: center;
    gap: 0.65rem;
    white-space: nowrap;
    color: var(--pure-white);
}
.brand-mark {
    width: 22px; height: 22px;
    background-color: var(--neon-yellow);
    border-radius: 5px;
    flex-shrink: 0;
}
.nav-links {
    display: flex;
    gap: 2.5rem;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    color: var(--text-secondary);
    letter-spacing: 0.02em;
}
.pill {
    background: transparent;
    color: var(--text-primary);
    border: 1px solid var(--border-mid);
    padding: 0.45rem 1.1rem;
    border-radius: 9999px;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 0.85rem;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    transition: border-color 150ms ease, box-shadow 150ms ease;
    text-decoration: none;
    cursor: pointer;
}
.pill:hover {
    border-color: var(--text-primary);
    box-shadow: 0 0 10px rgba(255,255,255,0.1);
}
.pill-solid {
    background: var(--pure-white);
    color: var(--pure-black);
    border-color: var(--pure-white);
}
.pill-solid:hover {
    background: #e0e0e0;
    border-color: #e0e0e0;
}

/* === Hero Section === */
.hero-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 3.5rem 0 2.5rem 0;
    text-align: center;
}
.hero-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--surface);
    border: 1px solid var(--border-soft);
    padding: 0.35rem 1rem;
    border-radius: 9999px;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--text-secondary);
    letter-spacing: 0.04em;
    margin-bottom: 1.5rem;
}
.hero-headline {
    font-family: var(--font-display);
    font-size: 5.5rem;
    font-weight: 900;
    line-height: 1.0;
    letter-spacing: -0.05em;
    text-transform: uppercase;
    color: var(--pure-white);
    max-width: 1000px;
    margin: 0 auto;
}
.hero-sub {
    font-family: var(--font-mono);
    font-size: 0.88rem;
    color: var(--text-secondary);
    margin-top: 2rem;
    letter-spacing: 0.01em;
}

/* === Sidebar === */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border-soft) !important;
}
[data-testid="stSidebar"] hr {
    border-color: var(--border-soft) !important;
    margin: 1.25rem 0 !important;
}

/* === Buttons === */
.stButton > button {
    background: var(--surface-2) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 9999px !important;
    font-family: var(--font-display) !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.55rem 1.1rem !important;
    transition: all 160ms ease !important;
    box-shadow: none !important;
    min-height: 44px !important;
    letter-spacing: 0.01em;
}
/* Secondary buttons: neon-yellow glow on hover */
.stButton > button:hover {
    background: var(--surface-2) !important;
    color: var(--neon-yellow) !important;
    border-color: var(--neon-yellow) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 0 18px rgba(229,255,0,0.25), 0 4px 20px rgba(0,0,0,0.4) !important;
    text-shadow: 0 0 8px rgba(229,255,0,0.5);
}
.stButton > button:active { transform: translateY(0) !important; }

/* Primary Run Edit button — logo neon yellow base */
button[data-testid="baseButton-primary"] {
    background: #E5FF00 !important;
    color: #000000 !important;
    border: none !important;
    font-weight: 800 !important;
    letter-spacing: 0.02em !important;
    box-shadow: 0 0 16px rgba(229,255,0,0.25) !important;
    height: 58px !important;
}
/* On hover: intensify neon yellow glow, don't invert */
button[data-testid="baseButton-primary"]:hover {
    background: #E5FF00 !important;
    border: none !important;
    box-shadow: 0 0 40px rgba(229,255,0,0.7), 0 0 80px rgba(229,255,0,0.25) !important;
    transform: translateY(-1px) !important;
    color: #000000 !important;
}

/* === Inputs === */
.stTextInput > div > div > input {
    background: var(--input-bg) !important;
    border: 1px solid rgba(198,255,0,0.4) !important;
    border-radius: 9999px !important;
    color: rgba(255,255,255,0.95) !important;
    font-family: var(--font-display) !important;
    font-size: 1rem !important;
    padding: 0.75rem 22px !important;
    min-height: 58px !important;
    transition: border-color 200ms ease, box-shadow 200ms ease;
}
.stTextInput > div > div > input:hover {
    border-color: rgba(198,255,0,0.8) !important;
}
.stTextInput > div > div > input:focus {
    border-color: #C6FF00 !important;
    box-shadow: 0 0 0 3px rgba(198,255,0,0.12) !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder {
    color: rgba(255,255,255,0.6) !important;
}
.stTextArea textarea {
    background: var(--input-bg) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 12px !important;
    color: var(--text-primary) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.85rem !important;
}
.stSelectbox [data-baseweb="select"] > div {
    background: var(--input-bg) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
}

/* === UI Labels === */
.ui-label {
    font-family: var(--font-mono);
    font-size: 0.68rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
}

/* === Workspace Panels === */
.workspace-panel {
    background: var(--surface);
    border: 1px solid var(--border-soft);
    border-radius: 16px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    overflow: hidden;
}

/* === Log Box === */
.log-box {
    font-family: var(--font-mono);
    font-size: 0.78rem;
    color: var(--text-secondary);
    line-height: 1.9;
}
.log-success { color: var(--accent-green); }
.log-error   { color: var(--accent-error); }

/* Focus */
*:focus-visible {
    outline: 2px solid var(--neon-yellow) !important;
    outline-offset: 3px !important;
}

/* Block container */
.block-container { padding-top: 2.5rem !important; padding-bottom: 3rem !important; }

/* ====================================================
   FINAL POLISH ADDITIONS
   ==================================================== */

/* === Hero Glow Blob === */
.hero-container {
    position: relative;
}
.hero-container::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -55%);
    width: 600px;
    height: 300px;
    background: radial-gradient(ellipse, rgba(229,255,0,0.07) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
    filter: blur(40px);
}
.hero-container > * { position: relative; z-index: 1; }

/* === Gradient Headline Text === */
.hero-headline {
    background: linear-gradient(160deg, #FFFFFF 0%, #E0E0E0 60%, #B8B8B8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* === Scanline Noise Overlay === */
.stApp::after {
    content: '';
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 9998;
    background-image: repeating-linear-gradient(
        0deg,
        rgba(0,0,0,0.03) 0px,
        rgba(0,0,0,0.03) 1px,
        transparent 1px,
        transparent 2px
    );
    background-size: 100% 2px;
}

/* === Button Shimmer on Hover === */
.stButton > button {
    overflow: hidden !important;
    position: relative !important;
}
.stButton > button::before {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 60%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
    transform: skewX(-20deg);
    transition: left 0.5s ease;
    pointer-events: none;
}
.stButton > button:hover::before { left: 160%; }

/* === Nav Links Hover Animation === */
.nav-links a {
    position: relative;
    transition: color 200ms ease;
    text-decoration: none;
    color: inherit;
    cursor: pointer;
}
.nav-links a::after {
    content: '';
    position: absolute;
    bottom: -3px; left: 0;
    width: 0; height: 1px;
    background: var(--neon-yellow);
    transition: width 250ms ease;
}
.nav-links a:hover { color: var(--text-primary) !important; }
.nav-links a:hover::after { width: 100%; }

/* === Workspace Panel Glass Effect === */
.workspace-panel {
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    background: rgba(17,17,17,0.85) !important;
    transition: border-color 250ms ease, box-shadow 250ms ease;
}
.workspace-panel:hover {
    border-color: var(--border-mid) !important;
    box-shadow: 0 0 0 1px rgba(229,255,0,0.06), 0 8px 32px rgba(0,0,0,0.4);
}

/* === Hero Pill Animated Dot === */
.hero-pill::before {
    content: '';
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--neon-yellow);
    box-shadow: 0 0 6px var(--neon-yellow);
    margin-right: 0.4rem;
    animation: blink-dot 2s ease-in-out infinite;
}
@keyframes blink-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.2; }
}

/* === Run Edit button shimmer === */
button[data-testid="baseButton-primary"] {
    overflow: hidden !important;
    position: relative !important;
}
button[data-testid="baseButton-primary"]::before {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 60%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent);
    transform: skewX(-20deg);
    transition: left 0.5s ease;
    pointer-events: none;
}
button[data-testid="baseButton-primary"]:hover::before { left: 160%; }

/* === Expander (Agent Inspector) styling === */
.stExpander {
    background: var(--surface) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 12px !important;
}
.stExpander summary {
    font-family: var(--font-mono) !important;
    font-size: 0.8rem !important;
    color: var(--text-secondary) !important;
    letter-spacing: 0.05em !important;
}

/* === Scrollbar === */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-mid); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--fog); }

/* === Sidebar brand area === */
[data-testid="stSidebar"] .nav-brand {
    font-size: 1.2rem !important;
    border-bottom: 1px solid var(--border-soft);
    padding-bottom: 1.25rem;
    margin-bottom: 1.25rem;
    width: 100%;
}

/* Removed duplicate input focus glow */

/* === Pipeline container glass card === */
.pipeline-wrap {
    background: rgba(17,17,17,0.6) !important;
    border: 1px solid var(--border-soft) !important;
    border-radius: 12px !important;
    padding: 1.25rem 2rem !important;
    backdrop-filter: blur(4px);
}
</style>
"""

# ============================================================
# COMPONENT: PIPELINE
# ============================================================

def render_pipeline_html(current_step: int, status: str = "running"):
    """
    Renders the pipeline as a connected system flow visualization.
    """
    html = f"""<style>
.pipeline-wrap {{
    background: transparent;
    font-family: var(--font-display);
    display: flex; gap: 0;
    align-items: center;
    justify-content: center;
    padding: 1.5rem 0;
}}
.pipeline-node {{
    display: flex; align-items: center; gap: 0.75rem;
    font-size: 0.85rem; font-weight: 600;
    color: var(--text-secondary);
    transition: all 0.3s;
    letter-spacing: 0.02em;
}}
.pipeline-node .tally {{
    width: 10px; height: 10px;
    border-radius: 50%;
    background: var(--border-soft);
    box-shadow: 0 0 0 4px rgba(255,255,255,0.02);
}}
.pipeline-line {{
    width: 40px; height: 1px;
    background: var(--border-soft);
    margin: 0 1rem;
}}

/* States */
.pipeline-node.active {{ color: var(--text-primary); }}
.pipeline-node.active .tally {{ 
    background: var(--accent-amber); 
    box-shadow: 0 0 12px rgba(229,255,0,0.5), 0 0 0 4px rgba(229,255,0,0.1);
    animation: tally-pulse 1.2s ease-in-out infinite;
}}
@keyframes tally-pulse {{
    0%, 100% {{ box-shadow: 0 0 12px rgba(229,255,0,0.5), 0 0 0 4px rgba(229,255,0,0.1); }}
    50%        {{ box-shadow: 0 0 24px rgba(229,255,0,0.8), 0 0 0 8px rgba(229,255,0,0.15); }}
}}

.pipeline-node.success {{ color: var(--text-primary); }}
.pipeline-node.success .tally {{ 
    background: var(--accent-green); 
    box-shadow: 0 0 12px rgba(62, 207, 142, 0.4), 0 0 0 4px rgba(62, 207, 142, 0.1);
}}

.pipeline-node.error {{ color: var(--accent-error); }}
.pipeline-node.error .tally {{ 
    background: var(--accent-error); 
    box-shadow: 0 0 12px rgba(255, 107, 107, 0.4), 0 0 0 4px rgba(255, 107, 107, 0.1);
}}
</style>
<div class="pipeline-wrap">"""

    names = ["PLANNER", "CODER", "GUARDRAIL", "EXECUTOR"]

    for i, name in enumerate(names):
        cls = ""
        msg = name
        
        if current_step == -1:
            if status == "success":
                cls = "success"
            elif status == "error":
                cls = "error"
        else:
            if i < current_step:
                cls = "success"
            elif i == current_step:
                cls = "active"
                msg = f"{name}..."
                
        html += f"""
<div class="pipeline-node {cls}">
    <div class="tally"></div>
    {msg}
</div>
"""
        if i < len(names) - 1:
            html += '<div class="pipeline-line"></div>'

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# ============================================================
# SESSION INIT & HELPERS
# ============================================================

# Models are now configured dynamically via text input.

def init_session():
    defaults = {
        "api_key":           "",  # Users enter their own key
        "video_path":        None,
        "output_path":       None,
        "uploaded_filename": None,
        "prompt":            "",
        "edit_plan":         "",
        "generated_code":    "",
        "logs":              [],
        "render_status":     "Pending",
        "running":           False,
        "error_message":     "",
        "video_meta":        {},
        "model_name":        "gemini-2.0-flash",
        "quality":           "high",
        "export_format":     "MP4",
        "trigger_run":       False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def colorize_log(line: str) -> str:
    if line.startswith("✅"):  return f'<span class="log-success">{line}</span>'
    if line.startswith("❌") or line.startswith("🚨"): return f'<span class="log-error">{line}</span>'
    if line.startswith("🔄") or line.startswith("⚠️"): return f'<span>{line}</span>'
    return line

# ============================================================
# MAIN APP
# ============================================================

def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    init_session()

    # ── ANIMATED CURSOR TRAIL ────────────────────────────────
    st.components.v1.html("""
<style>
/* Neon dot — sits exactly at the cursor tip */
#cursor-dot {
    position: fixed;
    pointer-events: none;
    z-index: 999999;
    border-radius: 50%;
    width: 7px;
    height: 7px;
    background: #E5FF00;
    box-shadow: 0 0 8px 3px rgba(229,255,0,0.8), 0 0 18px 6px rgba(229,255,0,0.3);
    transform: translate(-50%, -50%);
    transition: transform 0.08s ease, width 0.15s ease, height 0.15s ease;
    will-change: left, top;
}
#cursor-dot.on-interactive {
    width: 10px;
    height: 10px;
    background: #ffffff;
    box-shadow: 0 0 12px 4px rgba(229,255,0,1), 0 0 30px 10px rgba(229,255,0,0.4);
}
/* Trailing ring — lags behind with glow */
#cursor-aura {
    position: fixed;
    pointer-events: none;
    z-index: 999998;
    border-radius: 50%;
    transform: translate(-50%, -50%);
    width: 38px;
    height: 38px;
    border: 1.5px solid rgba(229,255,0,0.4);
    background: radial-gradient(circle, rgba(229,255,0,0.07) 0%, transparent 70%);
    transition: width 0.3s ease, height 0.3s ease, border-color 0.25s ease;
    will-change: left, top;
}
#cursor-aura.on-interactive {
    width: 58px;
    height: 58px;
    border-color: rgba(229,255,0,0.7);
    background: radial-gradient(circle, rgba(229,255,0,0.13) 0%, transparent 70%);
    box-shadow: 0 0 18px rgba(229,255,0,0.2);
}
/* Particle trail */
.cursor-particle {
    position: fixed;
    pointer-events: none;
    z-index: 999997;
    border-radius: 50%;
    background: rgba(229,255,0,0.7);
    transform: translate(-50%, -50%);
    animation: particle-fade 0.55s ease-out forwards;
}
@keyframes particle-fade {
    0%   { opacity: 0.8; width: 5px; height: 5px; }
    100% { opacity: 0;   width: 1px; height: 1px; }
}
</style>
<div id="cursor-dot"></div>
<div id="cursor-aura"></div>
<script>
(function() {
    const dot  = document.getElementById('cursor-dot');
    const aura = document.getElementById('cursor-aura');
    let mx = -300, my = -300;
    let ax = -300, ay = -300;
    let lastParticle = 0;

    // Dot tracks cursor instantly; aura lags behind
    function loop() {
        ax += (mx - ax) * 0.12;
        ay += (my - ay) * 0.12;
        aura.style.left = ax + 'px';
        aura.style.top  = ay + 'px';
        requestAnimationFrame(loop);
    }
    loop();

    document.addEventListener('mousemove', (e) => {
        mx = e.clientX;
        my = e.clientY;
        dot.style.left = mx + 'px';
        dot.style.top  = my + 'px';

        // Neon particle trail
        const now = Date.now();
        if (now - lastParticle > 35) {
            lastParticle = now;
            const p = document.createElement('div');
            p.className = 'cursor-particle';
            const size = (Math.random() * 4 + 2) + 'px';
            p.style.cssText = `left:${mx}px;top:${my}px;width:${size};height:${size};`;
            document.body.appendChild(p);
            setTimeout(() => p.remove(), 560);
        }
    });

    // Grow both on interactive elements
    document.addEventListener('mouseover', (e) => {
        const isInteractive = e.target.closest('button') || e.target.closest('a') || e.target.closest('input');
        dot.classList.toggle('on-interactive',  !!isInteractive);
        aura.classList.toggle('on-interactive', !!isInteractive);
    });
})();
</script>
""", height=0)


    # ── TOP NAVIGATION ───────────────────────────────────────
    st.markdown("""
    <div class="top-nav">
        <div class="nav-brand" style="font-size: 2.5rem; letter-spacing: -0.05em; gap: 0.75rem;">
            <div class="brand-mark" style="width: 28px; height: 28px; border-radius: 6px;"></div>
            AGENTIC-CUT
        </div>
        <div class="nav-links">
            <a href="https://github.com/Ishan-412/Agentic-Cut/blob/main/agent.py" target="_blank">Agents</a>
            <a href="https://github.com/Ishan-412/Agentic-Cut/blob/main/README.md" target="_blank">Documentation</a>
            <a href="https://github.com/Ishan-412/Agentic-Cut/issues" target="_blank">Community</a>
        </div>
        <div style="display:flex; gap:1rem;">
            <a href="https://github.com/Ishan-412/Agentic-Cut/issues/new" target="_blank" class="pill pill-solid">Feedback •</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── SIDEBAR ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div class="nav-brand" style="margin-bottom: 2rem;">
            <div class="brand-mark"></div>
            AGENTIC-CUT
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="ui-label">Gemini API Key</div>', unsafe_allow_html=True)
        api_key_val = st.text_input(
            "API Key", value=st.session_state.api_key,
            placeholder="Paste your Gemini API key...",
            type="password", label_visibility="collapsed",
        )
        if api_key_val:
            st.session_state.api_key = api_key_val
        st.markdown(
            '<div style="font-family:var(--font-mono);font-size:0.65rem;color:var(--text-muted);margin-top:0.4rem;">'
            'Get a free key at <a href="https://aistudio.google.com/app/apikey" target="_blank" '
            'style="color:var(--neon-yellow);text-decoration:none;">aistudio.google.com</a>'
            '</div>',
            unsafe_allow_html=True
        )
        if not st.session_state.api_key:
            st.markdown(
                '<div style="background:rgba(229,255,0,0.06);border:1px solid rgba(229,255,0,0.2);'
                'border-radius:8px;padding:0.6rem 0.8rem;margin-top:0.75rem;'
                'font-family:var(--font-mono);font-size:0.72rem;color:rgba(229,255,0,0.8);">'
                '⚠ Enter your API key above to run edits'
                '</div>',
                unsafe_allow_html=True
            )

        st.markdown('<div class="ui-label" style="margin-top:1rem">Model Engine</div>', unsafe_allow_html=True)
        
        available_models = []
        if st.session_state.api_key:
            try:
                genai.configure(api_key=st.session_state.api_key)
                for m in genai.list_models():
                    name = m.name.replace('models/', '')
                    # Filter out models known to throw 404 for new users
                    if 'generateContent' in m.supported_generation_methods and name not in ['gemini-1.5-flash', 'gemini-2.5-flash']:
                        available_models.append(name)
            except Exception:
                pass
                
        if available_models:
            # Try to select the default model if it exists in their allowed list
            default_index = 0
            if st.session_state.model_name in available_models:
                default_index = available_models.index(st.session_state.model_name)
            
            st.session_state.model_name = st.selectbox("Available Models (Auto-detected)", available_models, index=default_index, label_visibility="collapsed")
            st.markdown('<div style="font-size:0.65rem;color:var(--text-muted);margin-top:0.2rem;">Models loaded from your API key</div>', unsafe_allow_html=True)
        else:
            st.session_state.model_name = st.text_input("Model", value=st.session_state.model_name, label_visibility="collapsed")
            if st.session_state.api_key:
                st.markdown('<div style="font-size:0.65rem;color:var(--text-muted);margin-top:0.2rem;">Failed to fetch models. Type manually.</div>', unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        
        st.markdown('<div class="ui-label">Export Settings</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.export_format = st.selectbox("Format", ["MP4", "MOV", "GIF"], label_visibility="collapsed")
        with c2:
            st.session_state.quality = st.selectbox("Quality", ["High", "Medium", "Fast"], label_visibility="collapsed").lower()

        st.markdown("<hr>", unsafe_allow_html=True)
        
        st.markdown('<div class="ui-label">Upload Video</div>', unsafe_allow_html=True)
        uploaded = st.file_uploader("Upload", type=["mp4", "mov", "avi"], label_visibility="collapsed")
        
        if uploaded is not None:
            upload_key = f"{uploaded.name}_{uploaded.size}"
            if st.session_state.get("upload_key") != upload_key:
                suffix = Path(uploaded.name).suffix
                workspace = Path(__file__).parent / "workspace"
                upload_dir = workspace / "uploads"
                output_dir = workspace / "outputs"
                upload_dir.mkdir(parents=True, exist_ok=True)
                output_dir.mkdir(parents=True, exist_ok=True)

                # Clear old uploads to avoid taking up disk space and to prevent caching bugs
                for f in upload_dir.glob("*"):
                    try:
                        f.unlink()
                    except Exception:
                        pass

                upload_path = upload_dir / f"input_{int(time.time())}{suffix}"
                upload_path.write_bytes(uploaded.read())

                st.session_state.video_path = str(upload_path)
                st.session_state.uploaded_filename = uploaded.name
                st.session_state.upload_key = upload_key
                st.session_state.output_path = str(output_dir / f"output.{st.session_state.export_format.lower()}")
                
                if Path(st.session_state.output_path).exists():
                    Path(st.session_state.output_path).unlink(missing_ok=True)

                with st.spinner("Analyzing media..."):
                    st.session_state.video_meta = get_video_metadata(str(upload_path))
                st.rerun()
            
            st.markdown(f'<div class="mono-text" style="font-size:0.75rem;color:var(--pure-white);margin-top:1rem;">Active: {uploaded.name}</div>', unsafe_allow_html=True)

    # ── HERO SECTION ─────────────────────────────────────────
    if not st.session_state.video_path:
        st.markdown("""
        <div class="hero-container">
            <div class="hero-pill">We edit videos for humans</div>
            <div class="hero-headline">FULL-CYCLE AI<br>VIDEO AGENCY</div>
            <div class="mono-text hero-sub">Upload a video in the sidebar to begin editing.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Update output path suffix dynamically in case export format changed
        out_dir = Path(st.session_state.video_path).parent.parent / "outputs"
        st.session_state.output_path = str(out_dir / f"output.{st.session_state.export_format.lower()}")

    # ── PIPELINE & CONTROLS (ALWAYS VISIBLE) ─────────────────
    
    st.markdown('<div style="height:2rem;"></div>', unsafe_allow_html=True)
    
    # Text input and execution row
    cmd_col1, cmd_col2 = st.columns([4, 1], vertical_alignment="bottom")
    with cmd_col1:
        prompt_val = st.text_input(
            "Instruction", value=st.session_state.prompt,
            placeholder="✨ Describe how you want to edit your video...",
            label_visibility="collapsed"
        )
        st.session_state.prompt = prompt_val
    with cmd_col2:
        run_clicked = st.button("Run Edit", type="primary", use_container_width=True, disabled=st.session_state.running, key="run_btn")

    if run_clicked:
        st.session_state.trigger_run = True

    # Quick Actions Row
    st.markdown('<div class="ui-label" style="margin-top:0.5rem; margin-bottom: 0.5rem;">AI Command Presets</div>', unsafe_allow_html=True)
    q1, q2, q3, q4, q5, q6 = st.columns(6)
    def set_prompt(txt): 
        st.session_state.prompt = txt
    
    with q1:
        st.button("Trim first 5s", on_click=set_prompt, args=("Trim the first 5 seconds of the video",), use_container_width=True)
    with q2:
        st.button("Make B&W", on_click=set_prompt, args=("Convert the video to black and white",), use_container_width=True)
    with q3:
        st.button("Mute Audio", on_click=set_prompt, args=("Remove the audio track completely",), use_container_width=True)
    with q4:
        st.button("Speed 1.5x", on_click=set_prompt, args=("Speed up the video by 1.5x",), use_container_width=True)
    with q5:
        st.button("Reverse", on_click=set_prompt, args=("Reverse the video playback",), use_container_width=True)
    with q6:
        st.button("Resize 9:16", on_click=set_prompt, args=("Crop the video to 9:16 vertical ratio",), use_container_width=True)

    # ── PIPELINE STATUS ──
    pipeline_ph = st.empty()
    node_to_step = {"plan_node": 0, "code_node": 1, "execute_node": 2}
    current_step_idx = -1
    retries = st.session_state.logs.count("🔄") if st.session_state.logs else 0
    status_str = "running" if st.session_state.running else ("success" if st.session_state.render_status == "Success" else "error")
    
    if st.session_state.running:
        current_step_idx = 0

    # ── WORKSPACE ────────────────────────────────────────────
    if st.session_state.video_path:
        st.markdown('<div style="height:2rem;"></div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="ui-label">Original File</div>', unsafe_allow_html=True)
            st.markdown('<div class="workspace-panel">', unsafe_allow_html=True)
            if Path(st.session_state.video_path).exists():
                st.video(st.session_state.video_path)
            st.markdown('</div>', unsafe_allow_html=True)
    
        with col2:
            st.markdown('<div class="ui-label">Rendered Output</div>', unsafe_allow_html=True)
            st.markdown('<div class="workspace-panel">', unsafe_allow_html=True)
            if st.session_state.output_path and Path(st.session_state.output_path).exists():
                if st.session_state.export_format == "GIF":
                    st.image(st.session_state.output_path)
                else:
                    st.video(st.session_state.output_path)
            else:
                if st.session_state.render_status == "Failed":
                    st.markdown('<div class="mono-text" style="text-align:center;padding:4rem 0;color:var(--accent-error)">Render failed</div>', unsafe_allow_html=True)
                elif st.session_state.running:
                    st.markdown('<div class="mono-text" style="text-align:center;padding:4rem 0;color:var(--neon-yellow)">Processing...</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="mono-text" style="text-align:center;padding:4rem 0;color:var(--fog)">Waiting for instruction</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.session_state.output_path and Path(st.session_state.output_path).exists():
                with open(st.session_state.output_path, "rb") as f:
                    st.download_button(
                        f"Download {st.session_state.export_format}", data=f,
                        file_name=f"agentic_cut_output.{st.session_state.export_format.lower()}", 
                        mime=f"video/{st.session_state.export_format.lower()}" if st.session_state.export_format != "GIF" else "image/gif",
                    )

    # ── TIMELINE CONTROLS (ADVANCED) ─────────────────────────
    if st.session_state.video_path:
        st.markdown('<div class="ui-label" style="margin-top:1rem;">Timeline Controls</div>', unsafe_allow_html=True)
        t1, t2, t3, t4, t5, t6 = st.columns(6)
        
        with t1: 
            st.button("✂️ Split Clip", on_click=set_prompt, args=("Split the clip exactly in half",), use_container_width=True)
        with t2: 
            st.button("♫ Audio Mixer", on_click=set_prompt, args=("Normalize audio and add a 1-second fade in/out",), use_container_width=True)
        with t3: 
            st.button("✨ Auto Color", on_click=set_prompt, args=("Apply auto color correction and enhance contrast",), use_container_width=True)
        with t4: 
            st.button("A Text Overlay", on_click=set_prompt, args=("Add a cinematic text overlay in the center",), use_container_width=True)
        with t5: 
            st.button("fx Transitions", on_click=set_prompt, args=("Add a smooth crossfade transition",), use_container_width=True)
        with t6: 
            st.button("⚙️ Extract Audio", on_click=set_prompt, args=("Extract the audio track and save as MP3",), use_container_width=True)
            
        st.markdown('<hr style="border-color: var(--border-soft); margin: 1rem 0;">', unsafe_allow_html=True)

    # ── INSPECTOR ────────────────────────────────────────────
    st.markdown('<div style="height:2rem;"></div>', unsafe_allow_html=True)
    if st.session_state.edit_plan or st.session_state.generated_code or st.session_state.logs:
        with st.expander("Agent Inspector"):
            t1, t2, t3 = st.tabs(["Plan", "Code", "Logs"])
            with t1:
                st.markdown(f'<div class="mono-text" style="font-size:0.85rem">{st.session_state.edit_plan}</div>', unsafe_allow_html=True)
            with t2:
                st.code(st.session_state.generated_code, language="python")
            with t3:
                log_html = '<div class="log-box">' + "<br>".join(
                    colorize_log(line) for line in st.session_state.logs if line.strip()
                ) + "</div>"
                st.markdown(log_html, unsafe_allow_html=True)
                if st.session_state.error_message and st.session_state.render_status != "Success":
                    st.markdown("**Traceback:**")
                    st.code(st.session_state.error_message, language="python")

    # ── RUN EXECUTION ────────────────────────────────────────
    if st.session_state.trigger_run:
        st.session_state.trigger_run = False
        
        if not st.session_state.api_key:
            st.error("Missing API Key.")
            st.stop()
        if not st.session_state.video_path or not Path(st.session_state.video_path).exists():
            st.error("Upload a video first.")
            st.stop()
        if not st.session_state.prompt.strip():
            st.error("Enter an instruction.")
            st.stop()

        st.session_state.running = True
        st.session_state.render_status = "Pending"
        st.session_state.edit_plan = ""
        st.session_state.generated_code = ""
        st.session_state.logs = []
        st.session_state.error_message = ""
        
        if st.session_state.output_path and Path(st.session_state.output_path).exists():
            Path(st.session_state.output_path).unlink(missing_ok=True)
            
        st.rerun()

    if st.session_state.running:
        try:
            for update in run_agent(
                video_path=st.session_state.video_path,
                prompt=st.session_state.prompt,
                api_key=st.session_state.api_key,
                output_path=st.session_state.output_path,
                model_name=st.session_state.model_name,
                quality=st.session_state.quality,
            ):
                node_name  = update["node"]
                node_state = update["state"]

                step_idx = node_to_step.get(node_name, 1)
                
                if node_name == "execute_node":
                    if any("Executor" in l for l in node_state.get("logs",[])):
                        step_idx = 3
                    else:
                        step_idx = 2

                current_step_idx = step_idx
                
                render_status = node_state.get("render_status","Pending")
                is_err = render_status in ("Failed","SecurityError")
                curr_status = "error" if is_err else "running"
                
                with pipeline_ph:
                    render_pipeline_html(current_step_idx, curr_status)

                if node_state.get("edit_plan"):      st.session_state.edit_plan = node_state["edit_plan"]
                if node_state.get("generated_code"): st.session_state.generated_code = node_state["generated_code"]
                if node_state.get("logs"):           st.session_state.logs = node_state["logs"]
                if node_state.get("render_status"):  st.session_state.render_status = node_state["render_status"]
                if node_state.get("error_message"):  st.session_state.error_message = node_state["error_message"]

        except Exception as e:
            st.session_state.render_status = "Failed"
            error_str = str(e)
            if "429 RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                msg = "QUOTA EXCEEDED. USE FLASH."
                st.session_state.error_message = f"{msg}\n\n{error_str}"
                st.session_state.logs.append(f"❌ {msg}")
            else:
                st.session_state.error_message = error_str
                st.session_state.logs.append(f"❌ ERROR: {error_str}")

        st.session_state.running = False
        st.rerun()
        
    if not st.session_state.running:
        final_idx = 4 if st.session_state.render_status == "Success" else (current_step_idx if current_step_idx >=0 else -1)
        
        if st.session_state.render_status == "Success":
            status_str = "success"
        elif st.session_state.render_status in ("Failed", "SecurityError"):
            status_str = "error"
        else:
            status_str = "running"
            
        with pipeline_ph:
            render_pipeline_html(final_idx, status_str)

if __name__ == "__main__":
    main()
