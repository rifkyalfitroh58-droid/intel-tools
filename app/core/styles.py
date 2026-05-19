"""
OSINT Intelligence Suite — styles.py
CSS terpusat untuk semua modul
"""

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1rem; padding-bottom: 1rem; }

/* ── Cards ── */
.suite-card {
    background: #0D1B2A; border: 1px solid #1E3A5F;
    border-radius: 10px; padding: 1rem 1.2rem;
    text-align: center; position: relative; overflow: hidden;
    cursor: default;
}
.suite-card::after {
    content: ''; position: absolute;
    bottom: 0; left: 0; right: 0; height: 2px;
}
.suite-card.person::after { background: #4FC3F7; }
.suite-card.threat::after { background: #E74C3C; }
.suite-card.geo::after    { background: #2ECC71; }
.suite-card.media::after  { background: #F39C12; }
.suite-card.neutral::after{ background: #9B59B6; }

.metric-num   { font-family:'DM Mono',monospace; font-size:1.9rem; font-weight:500; line-height:1.1; }
.metric-label { font-size:.72rem; color:rgba(255,255,255,.4); margin-top:4px; letter-spacing:.06em; text-transform:uppercase; }

/* ── Section titles ── */
.sec-title {
    font-family:'DM Mono',monospace; font-size:.78rem; font-weight:500;
    letter-spacing:.12em; text-transform:uppercase;
    padding-bottom:6px; border-bottom:1px solid #1E3A5F;
    margin:1.2rem 0 .8rem;
}
.sec-title.person { color:#4FC3F7; }
.sec-title.threat { color:#E74C3C; }
.sec-title.geo    { color:#2ECC71; }
.sec-title.media  { color:#F39C12; }
.sec-title.neutral{ color:#9B59B6; }

/* ── Article cards ── */
.article-card {
    background:#0D1B2A; border:1px solid #1E3A5F;
    border-radius:8px; padding:.75rem 1rem; margin-bottom:6px;
}
.article-title { color:white; font-weight:500; font-size:.85rem; margin-bottom:4px; }
.article-meta  { color:rgba(255,255,255,.35); font-size:.7rem;
                 font-family:'DM Mono',monospace; }

/* ── Badges ── */
.mod-badge {
    display:inline-block; font-family:'DM Mono',monospace;
    font-size:.65rem; padding:2px 8px; border-radius:3px;
    margin:2px; border:1px solid; cursor:pointer;
    transition: opacity .15s;
}
.mod-badge:hover { opacity: .7; }
.mod-badge.person { background:rgba(79,195,247,.12); border-color:rgba(79,195,247,.3); color:#4FC3F7; }
.mod-badge.threat { background:rgba(231,76,60,.12);  border-color:rgba(231,76,60,.3);  color:#E74C3C; }
.mod-badge.geo    { background:rgba(46,204,113,.12); border-color:rgba(46,204,113,.3); color:#2ECC71; }
.mod-badge.media  { background:rgba(243,156,18,.12); border-color:rgba(243,156,18,.3); color:#F39C12; }

/* ── Panel keterhubungan ── */
.link-panel {
    background:#070d14; border:1px solid #1E3A5F;
    border-radius:10px; padding:1rem;
}
.link-panel-title {
    font-family:'DM Mono',monospace; font-size:.75rem;
    color:#9B59B6; letter-spacing:.1em; text-transform:uppercase;
    margin-bottom:.8rem; padding-bottom:6px;
    border-bottom:1px solid #1E3A5F;
}
.link-item {
    background:#0D1B2A; border:1px solid #1E3A5F;
    border-radius:6px; padding:.6rem .8rem; margin-bottom:5px;
    font-size:.8rem;
}
.link-type-tag {
    display:inline-block; font-family:'DM Mono',monospace;
    font-size:.6rem; padding:1px 5px; border-radius:2px;
    background:rgba(155,89,182,.15); border:1px solid rgba(155,89,182,.3);
    color:#9B59B6; margin-left:6px;
}

/* ── Intel boxes ── */
.intel-box {
    background:#0A0F1E; border:1px solid #1E3A5F;
    border-radius:8px; padding:.9rem 1.1rem;
    margin-bottom:.6rem; font-size:.84rem;
    color:rgba(255,255,255,.8); line-height:1.6;
}
.intel-box.critical { border-color:rgba(231,76,60,.5); background:rgba(231,76,60,.05); }
.intel-box.high     { border-color:rgba(230,126,34,.4); background:rgba(230,126,34,.04); }
.intel-box.medium   { border-color:rgba(243,156,18,.3); background:rgba(243,156,18,.04); }
.intel-box.low      { border-color:rgba(46,204,113,.3); background:rgba(46,204,113,.04); }
.intel-box.info     { border-color:rgba(79,195,247,.3); background:rgba(79,195,247,.04); }

/* ── Report box ── */
.report-box {
    background:#050A10; border:1px solid #1E3A5F; border-radius:8px;
    padding:1.2rem; font-family:'DM Mono',monospace; font-size:.75rem;
    color:rgba(255,255,255,.75); line-height:1.8; white-space:pre-wrap;
    max-height:500px; overflow-y:auto;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background:#050A14; }
section[data-testid="stSidebar"] * { color:rgba(255,255,255,.8) !important; }
section[data-testid="stSidebar"] hr { border-color:#1E3A5F !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background:transparent; border-bottom:1px solid #1E3A5F; gap:4px;
}
.stTabs [data-baseweb="tab"] {
    font-family:'DM Mono',monospace; font-size:.73rem;
    letter-spacing:.06em; padding:8px 14px;
    border-radius:6px 6px 0 0;
    color:rgba(255,255,255,.4) !important;
    background:transparent; border:none;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-track { background:#0A0F1E; }
::-webkit-scrollbar-thumb { background:#1E3A5F; border-radius:4px; }
</style>
"""


def module_css(module: str) -> str:
    """Return CSS tambahan spesifik untuk tiap modul (warna tab aktif)."""
    colors = {
        "person": "#4FC3F7",
        "threat": "#E74C3C",
        "geo":    "#2ECC71",
        "media":  "#F39C12",
    }
    color = colors.get(module, "#9B59B6")
    return f"""
<style>
.stTabs [aria-selected="true"] {{
    background:rgba({_hex_to_rgb(color)},.1) !important;
    color:{color} !important;
    border-bottom:2px solid {color} !important;
}}
div[data-testid="stButton"] button {{
    background:rgba({_hex_to_rgb(color)},.1) !important;
    color:{color} !important;
    border:1px solid rgba({_hex_to_rgb(color)},.3) !important;
    border-radius:6px !important;
    font-family:'DM Mono',monospace !important;
    font-size:.78rem !important;
    letter-spacing:.04em !important;
}}
div[data-testid="stButton"] button:hover {{
    background:rgba({_hex_to_rgb(color)},.2) !important;
}}
</style>
"""


def _hex_to_rgb(h: str) -> str:
    h = h.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))
