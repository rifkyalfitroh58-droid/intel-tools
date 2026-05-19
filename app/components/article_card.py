"""
OSINT Intelligence Suite — article_card.py
Komponen kartu artikel dengan badge keterhubungan + panel analisis lintas modul
"""
import streamlit as st
import pandas as pd
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core.config import MODULE_COLORS, MODULE_LABELS, MODULE_ICONS
from core.analyzer import get_threat_color, get_threat_label, get_risk_color
from core.linker import get_link_badges, get_panel_data


def _hex_rgb(h: str) -> str:
    h = h.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


def render_article_card(row: dict, current_module: str,
                        show_badges: bool = True,
                        show_scores: bool = True):
    """
    Render satu kartu artikel lengkap dengan:
    - Badge modul terhubung (klik → pindah modul)
    - Tombol panel keterhubungan
    - Score breakdown (hoax, hate, threat, severity)
    """
    article_id = int(row.get("id", 0))
    title      = str(row.get("title",""))[:100]
    source     = row.get("source","")
    url        = row.get("url","") or "#"
    pub        = ""
    if pd.notna(row.get("published_at")):
        try:
            pub = pd.to_datetime(row["published_at"]).strftime("%d %b %Y")
        except Exception:
            pub = str(row.get("published_at",""))[:10]

    threat_sc  = float(row.get("threat_score",0))
    hoax_sc    = float(row.get("hoax_score",0))
    hate_sc    = float(row.get("hate_score",0))
    severity   = float(row.get("severity",0))
    location   = row.get("location","")

    threat_color = get_threat_color(threat_sc)

    # Badge modul terhubung
    badges = get_link_badges(article_id) if show_badges and article_id > 0 else []
    badge_html = ""
    if badges:
        badge_parts = []
        for b in badges[:4]:
            mod   = b["module"]
            color = b["color"]
            rgb   = _hex_rgb(color)
            icon  = MODULE_ICONS.get(mod,"")
            lbl   = MODULE_LABELS.get(mod, mod)
            _score = b["score"]
            badge_parts.append(
                f'<span class="mod-badge {mod}" '
                f'title="Terhubung ke {lbl} (score:{_score:.2f})">'
                f'{icon} {lbl}</span>'
            )
        badge_html = "<div style='margin-top:5px'>" + "".join(badge_parts) + "</div>"

    # Skor baris
    scores_html = ""
    if show_scores:
        parts = []
        if hoax_sc >= 20:
            c = get_threat_color(hoax_sc)
            parts.append(f'<span style="color:{c}">HOAX:{hoax_sc:.0f}</span>')
        if hate_sc >= 20:
            c = get_threat_color(hate_sc)
            parts.append(f'<span style="color:{c}">HATE:{hate_sc:.0f}</span>')
        if threat_sc >= 20:
            parts.append(f'<span style="color:{threat_color}">THREAT:{threat_sc:.0f}</span>')
        if severity >= 25 and location:
            c = get_threat_color(severity) if severity >= 50 else "#F39C12"
            parts.append(f'<span style="color:{c}">SEV:{severity:.0f} 📍{location}</span>')
        scores_html = " &nbsp;·&nbsp; ".join(parts)

    st.markdown(f"""
    <div class="article-card" style="border-left:3px solid {threat_color}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
            <div class="article-title" style="flex:1">{title}</div>
            <div style="font-family:'DM Mono',monospace;font-size:.75rem;
                        color:{threat_color};white-space:nowrap;font-weight:500">
                {threat_sc:.0f}/100
            </div>
        </div>
        <div class="article-meta">
            [{source}] &nbsp;·&nbsp; {pub}
            {(' &nbsp;·&nbsp; ' + scores_html) if scores_html else ''}
            &nbsp;·&nbsp; <a href="{url}" target="_blank"
            style="color:rgba(79,195,247,.5);text-decoration:none">&#8599; SOURCE</a>
        </div>
        {badge_html}
    </div>
    """, unsafe_allow_html=True)

    # Tombol panel keterhubungan
    if badges and article_id > 0:
        col_nav, col_panel = st.columns([3, 1])
        with col_panel:
            if st.button(f"🔗 Lihat keterhubungan",
                         key=f"panel_{article_id}_{current_module}"):
                st.session_state["panel_article_id"] = article_id
                st.session_state["show_panel"]       = True

        # Badge navigasi cepat
        with col_nav:
            for b in badges:
                mod   = b["module"]
                color = b["color"]
                label = MODULE_LABELS.get(mod, mod)
                icon  = MODULE_ICONS.get(mod,"")
                if st.button(f"{icon} Buka di {label} →",
                             key=f"goto_{article_id}_{mod}_{current_module}"):
                    st.session_state["page"]            = mod
                    st.session_state["highlight_url"]   = row.get("url","")
                    st.session_state["from_module"]      = current_module
                    st.rerun()


def render_link_panel(article_id: int):
    """
    Render panel keterhubungan lengkap untuk satu artikel.
    Tampil sebagai expander di bawah artikel.
    """
    data = get_panel_data(article_id)
    if not data.get("links_by_module"):
        st.info("Artikel ini belum terhubung ke modul lain.")
        return

    article = data.get("article", {})
    title   = str(article.get("title",""))[:80]

    st.markdown(f"""
    <div class="link-panel">
        <div class="link-panel-title">
            &#128279; PANEL KETERHUBUNGAN — {title}...
        </div>
    </div>
    """, unsafe_allow_html=True)

    for mod, items in data["links_by_module"].items():
        color = MODULE_COLORS.get(mod,"#888")
        label = MODULE_LABELS.get(mod, mod)
        icon  = MODULE_ICONS.get(mod,"")
        rgb   = _hex_rgb(color)

        with st.expander(f"{icon} {label} — {len(items)} artikel terhubung", expanded=True):
            for item in items[:5]:
                threat_c = get_threat_color(item["threat_score"])
                link_tag = {
                    "same_article":  "artikel sama",
                    "similar_title": "judul mirip",
                    "shared_entity": "entitas sama",
                    "same_topic":    "topik sama",
                }.get(item.get("link_type",""), item.get("link_type",""))

                scores = []
                if item["hoax_score"] >= 20:
                    scores.append(f"HOAX:{item['hoax_score']:.0f}")
                if item["threat_score"] >= 20:
                    scores.append(f"THREAT:{item['threat_score']:.0f}")
                if item["severity"] >= 25:
                    scores.append(f"SEV:{item['severity']:.0f}")
                if item.get("location"):
                    scores.append(f"📍{item['location']}")

                score_str = " · ".join(scores)
                url       = item.get("url","") or "#"

                st.markdown(f"""
                <div class="link-item">
                    <div style="font-weight:500;font-size:.82rem;color:white;margin-bottom:3px">
                        {str(item['title'])[:80]}
                        <span class="link-type-tag">{link_tag}</span>
                    </div>
                    <div style="font-family:'DM Mono',monospace;font-size:.68rem;
                                color:rgba(255,255,255,.4)">
                        [{item['source']}] &nbsp;·&nbsp;
                        <span style="color:{threat_c}">{score_str}</span>
                        &nbsp;·&nbsp;
                        <a href="{url}" target="_blank"
                        style="color:rgba(79,195,247,.4);text-decoration:none">&#8599;</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Tombol navigasi ke modul
            if st.button(f"Buka semua di {label} →",
                         key=f"open_mod_{mod}_{article_id}"):
                st.session_state["page"] = mod
                st.session_state["from_module"] = article.get("module","")
                st.rerun()
