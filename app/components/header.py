"""
OSINT Intelligence Suite — header.py
Header + breadcrumb navigasi tiap modul
"""
import streamlit as st
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core.config import MODULE_COLORS, MODULE_LABELS, MODULE_ICONS
from core.styles import _hex_to_rgb


MODULE_THEMES = {
    "home":   {"bg": "0a0f1e,0d1b2a,1a2744", "accent": "#9B59B6", "border": "#2d1b5e"},
    "person": {"bg": "0a0f1e,0d1b2a,0a1a2e", "accent": "#4FC3F7", "border": "#1E3A5F"},
    "threat": {"bg": "0d0a0a,1a0a0a,2a1010", "accent": "#E74C3C", "border": "#3d1515"},
    "geo":    {"bg": "0a0d0a,0d1a0d,0f2010", "accent": "#2ECC71", "border": "#1a3d1a"},
    "media":  {"bg": "0d0c0a,1a180a,2a2510", "accent": "#F39C12", "border": "#3d3515"},
}

MODULE_SUBTITLES = {
    "home":   "Intelligence Operations Center",
    "person": "Person &amp; Entity Intelligence",
    "threat": "Threat &amp; Disinformation Detection",
    "geo":    "Geospatial Incident Mapping",
    "media":  "Media &amp; Narrative Intelligence",
}


def render_header(module: str, keyword: str = "", unread_alerts: int = 0):
    """Render header dengan gradient warna sesuai modul aktif."""
    theme    = MODULE_THEMES.get(module, MODULE_THEMES["home"])
    accent   = theme["accent"]
    border   = theme["border"]
    bg_parts = theme["bg"].split(",")

    now_str  = datetime.now().strftime("%d %b %Y %H:%M")
    icon     = MODULE_ICONS.get(module, "◈")
    title    = MODULE_LABELS.get(module, "OSINT SUITE").upper()
    subtitle = MODULE_SUBTITLES.get(module, "Intelligence System")
    rgb      = _hex_to_rgb(accent)

    alert_badge = ""
    if unread_alerts > 0:
        alert_badge = f'<span style="display:inline-block;font-family:DM Mono,monospace;font-size:.65rem;background:rgba(231,76,60,.15);border:1px solid rgba(231,76,60,.4);color:#E74C3C;border-radius:4px;padding:2px 8px;margin-left:6px">&#9888; {unread_alerts} ALERT</span>'

    kw_badge = ""
    if keyword:
        kw_badge = f'<span style="display:inline-block;font-family:DM Mono,monospace;font-size:.65rem;background:rgba({rgb},.1);border:1px solid rgba({rgb},.3);color:{accent};border-radius:4px;padding:2px 8px;margin-left:6px">&#128269; {keyword}</span>'

    # Breadcrumb jika ada from_module
    breadcrumb = ""
    if st.session_state.get("from_module"):
        from_mod   = st.session_state["from_module"]
        from_label = MODULE_LABELS.get(from_mod, from_mod)
        from_icon  = MODULE_ICONS.get(from_mod, "")
        breadcrumb = f"""
        <div style="font-family:'DM Mono',monospace;font-size:.65rem;
                    color:rgba(255,255,255,.3);margin-bottom:4px">
            {from_icon} {from_label}
            <span style="margin:0 6px">&#8250;</span>
            {icon} {title}
        </div>"""

    bg3 = bg_parts[2] if len(bg_parts) > 2 else bg_parts[1]
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#{bg_parts[0]} 0%,#{bg_parts[1]} 50%,#{bg3} 100%);
                border:1px solid {border};border-radius:12px;
                padding:1.2rem 2rem;margin-bottom:1rem;position:relative;overflow:hidden">
        <div style="position:absolute;top:0;left:0;right:0;bottom:0;
                    background:repeating-linear-gradient(0deg,transparent,transparent 2px,
                    rgba({rgb},.03) 2px,rgba({rgb},.03) 4px)"></div>
        {breadcrumb}
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
                <div style="font-family:'DM Mono',monospace;font-size:1.4rem;
                            font-weight:500;color:{accent};letter-spacing:.08em">
                    {icon} {title}
                </div>
                <div style="font-family:'DM Mono',monospace;font-size:.7rem;
                            color:rgba({rgb},.5);letter-spacing:.12em;
                            text-transform:uppercase;margin-top:2px">
                    {subtitle}
                </div>
                <div style="margin-top:8px">
                    <span style="display:inline-block;font-family:'DM Mono',monospace;
                                 font-size:.65rem;background:rgba({rgb},.1);
                                 border:1px solid rgba({rgb},.3);color:{accent};
                                 border-radius:4px;padding:2px 8px">AKTIF</span>
                    {kw_badge}{alert_badge}
                </div>
            </div>
            <div style="font-family:'DM Mono',monospace;font-size:.7rem;
                        color:rgba({rgb},.4);text-align:right">
                {now_str}<br>
                <span style="color:rgba({rgb},.2)">SYSTEM: ONLINE</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
