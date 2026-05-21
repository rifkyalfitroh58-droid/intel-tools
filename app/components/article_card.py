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
                        show_scores: bool = True,
                        idx: int = 0):
    article_id   = int(row.get("id", 0))
    title        = str(row.get("title", ""))[:100]
    source       = str(row.get("source", ""))
    url          = str(row.get("url", "") or "#")
    pub          = ""
    if pd.notna(row.get("published_at")):
        try:
            pub = pd.to_datetime(row["published_at"]).strftime("%d %b %Y")
        except Exception:
            pub = str(row.get("published_at", ""))[:10]

    threat_sc    = float(row.get("threat_score", 0))
    hoax_sc      = float(row.get("hoax_score", 0))
    hate_sc      = float(row.get("hate_score", 0))
    severity     = float(row.get("severity", 0))
    location     = str(row.get("location", "") or "")
    threat_color = get_threat_color(threat_sc)
    threat_str   = str(int(threat_sc)) + "/100"

    # ── Badge modul terhubung ────────────────────────────────────────────────
    badges     = get_link_badges(article_id) if show_badges and article_id > 0 else []
    badge_html = ""
    if badges:
        parts = []
        for b in badges[:4]:
            mod    = b["module"]
            lbl    = MODULE_LABELS.get(mod, mod)
            icon   = MODULE_ICONS.get(mod, "")
            sc     = b["score"]
            parts.append(
                '<span class="mod-badge ' + mod + '" '
                'title="Terhubung ke ' + lbl + ' (score:' + str(round(sc, 2)) + ')">'
                + icon + ' ' + lbl + '</span>'
            )
        badge_html = '<div style="margin-top:5px">' + "".join(parts) + '</div>'

    # ── Skor baris ───────────────────────────────────────────────────────────
    scores_html = ""
    if show_scores:
        parts = []
        if hoax_sc >= 20:
            c = get_threat_color(hoax_sc)
            parts.append('<span style="color:' + c + '">HOAX:' + str(int(hoax_sc)) + '</span>')
        if hate_sc >= 20:
            c = get_threat_color(hate_sc)
            parts.append('<span style="color:' + c + '">HATE:' + str(int(hate_sc)) + '</span>')
        if threat_sc >= 20:
            parts.append('<span style="color:' + threat_color + '">THREAT:' + str(int(threat_sc)) + '</span>')
        if severity >= 25 and location:
            c = get_threat_color(severity) if severity >= 50 else "#F39C12"
            parts.append('<span style="color:' + c + '">SEV:' + str(int(severity)) + ' \U0001f4cd' + location + '</span>')
        scores_html = " &nbsp;\u00b7&nbsp; ".join(parts)

    scores_mid = (" &nbsp;\u00b7&nbsp; " + scores_html) if scores_html else ""

    # ── Build HTML ───────────────────────────────────────────────────────────
    html = (
        '<div class="article-card" style="border-left:3px solid ' + threat_color + '">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">'
        '<div class="article-title" style="flex:1">' + title + '</div>'
        '<div style="font-family:DM Mono,monospace;font-size:.75rem;'
        'color:' + threat_color + ';white-space:nowrap;font-weight:500">'
        + threat_str +
        '</div>'
        '</div>'
        '<div class="article-meta">'
        '[' + source + '] &nbsp;\u00b7\u00a0 ' + pub
        + scores_mid +
        ' &nbsp;\u00b7&nbsp; <a href="' + url + '" target="_blank" '
        'style="color:rgba(79,195,247,.5);text-decoration:none">&#8599; SOURCE</a>'
        '</div>'
        + badge_html +
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

    # ── Tombol panel keterhubungan ────────────────────────────────────────────
    if badges and article_id > 0:
        col_nav, col_panel = st.columns([3, 1])
        with col_panel:
            if st.button("🔗 Lihat keterhubungan",
                         key="panel_" + str(article_id) + "_" + current_module + "_" + str(idx)):
                st.session_state["panel_article_id"] = article_id
                st.session_state["show_panel"]       = True
        with col_nav:
            for b in badges:
                mod   = b["module"]
                label = MODULE_LABELS.get(mod, mod)
                icon  = MODULE_ICONS.get(mod, "")
                if st.button(icon + " Buka di " + label + " →",
                             key="goto_" + str(article_id) + "_" + mod + "_" + current_module + "_" + str(idx)):
                    st.session_state["page"]          = mod
                    st.session_state["highlight_url"] = row.get("url", "")
                    st.session_state["from_module"]   = current_module
                    st.rerun()


def render_link_panel(article_id: int, panel_key: str = ""):
    data = get_panel_data(article_id)
    if not data.get("links_by_module"):
        st.info("Artikel ini belum terhubung ke modul lain.")
        return

    article = data.get("article", {})
    title   = str(article.get("title", ""))[:80]

    st.markdown(
        '<div class="link-panel">'
        '<div class="link-panel-title">'
        '&#128279; PANEL KETERHUBUNGAN \u2014 ' + title + '...'
        '</div></div>',
        unsafe_allow_html=True
    )

    for mod, items in data["links_by_module"].items():
        color = MODULE_COLORS.get(mod, "#888")
        label = MODULE_LABELS.get(mod, mod)
        icon  = MODULE_ICONS.get(mod, "")

        with st.expander(icon + " " + label + " \u2014 " + str(len(items)) + " artikel terhubung", expanded=True):
            for item in items[:5]:
                threat_c = get_threat_color(item["threat_score"])
                link_map = {
                    "same_article":  "artikel sama",
                    "similar_title": "judul mirip",
                    "shared_entity": "entitas sama",
                    "same_topic":    "topik sama",
                }
                link_tag  = link_map.get(item.get("link_type", ""), item.get("link_type", ""))
                item_url  = str(item.get("url", "") or "#")
                item_src  = str(item.get("source", ""))
                item_title = str(item.get("title", ""))[:80]

                scores = []
                if item["hoax_score"] >= 20:
                    scores.append("HOAX:" + str(int(item["hoax_score"])))
                if item["threat_score"] >= 20:
                    scores.append("THREAT:" + str(int(item["threat_score"])))
                if item["severity"] >= 25:
                    scores.append("SEV:" + str(int(item["severity"])))
                if item.get("location"):
                    scores.append("\U0001f4cd" + item["location"])
                score_str = " \u00b7 ".join(scores)

                st.markdown(
                    '<div class="link-item">'
                    '<div style="font-weight:500;font-size:.82rem;color:white;margin-bottom:3px">'
                    + item_title +
                    ' <span class="link-type-tag">' + link_tag + '</span>'
                    '</div>'
                    '<div style="font-family:DM Mono,monospace;font-size:.68rem;'
                    'color:rgba(255,255,255,.4)">'
                    '[' + item_src + '] &nbsp;\u00b7&nbsp; '
                    '<span style="color:' + threat_c + '">' + score_str + '</span>'
                    ' &nbsp;\u00b7&nbsp; '
                    '<a href="' + item_url + '" target="_blank" '
                    'style="color:rgba(79,195,247,.4);text-decoration:none">&#8599;</a>'
                    '</div>'
                    '</div>',
                    unsafe_allow_html=True
                )

            if st.button("Buka semua di " + label + " →",
                         key="open_mod_" + mod + "_" + str(article_id) + "_" + panel_key):
                st.session_state["page"]        = mod
                st.session_state["from_module"] = article.get("module", "")
                st.rerun()
