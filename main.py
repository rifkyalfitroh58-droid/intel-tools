"""
OSINT Intelligence Suite — main.py
Entry point utama. Jalankan dengan: streamlit run main.py
"""
import streamlit as st
import sys, os

# Tambah path agar semua modul bisa diimport
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "core"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "modules"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "components"))

from app.core.database import ensure_db
from app.core.styles import BASE_CSS

# ── Page config (harus paling pertama) ────────────────────────────────────────
st.set_page_config(
    page_title="OSINT Intelligence Suite",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Init DB ────────────────────────────────────────────────────────────────────
ensure_db()

# ── Init session state ─────────────────────────────────────────────────────────
DEFAULTS = {
    "page":             "home",
    "from_module":      "",
    "pending_keyword":  "",
    "show_panel":       False,
    "panel_article_id": None,
    "highlight_url":    "",
    "context":          {},
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── Inject base CSS ────────────────────────────────────────────────────────────
st.markdown(BASE_CSS, unsafe_allow_html=True)

# ── Render sidebar (selalu tampil) ─────────────────────────────────────────────
from app.components.sidebar import render_sidebar
current_page = st.session_state.get("page", "home")
monitor_id, monitor_kw = render_sidebar(current_page)

# ── Router halaman ─────────────────────────────────────────────────────────────
page = st.session_state.get("page", "home")

if page == "home":
    from app.home import render_home
    render_home()

elif page == "person":
    from app.modules.person_intel import render_person_intel
    render_person_intel(monitor_id, monitor_kw or "")

elif page == "threat":
    from app.modules.threat_intel import render_threat_intel
    render_threat_intel(monitor_id, monitor_kw or "")

elif page == "geo":
    from app.modules.geo_intel import render_geo_intel
    render_geo_intel(monitor_id, monitor_kw or "")

elif page == "media":
    from app.modules.media_intel import render_media_intel
    render_media_intel(monitor_id, monitor_kw or "")

elif page == "report":
    from app.components.report import render_report
    render_report()

else:
    st.session_state["page"] = "home"
    st.rerun()
