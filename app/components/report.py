"""
OSINT Intelligence Suite — report.py
Halaman Laporan Terpadu dari semua modul A+B+C+D
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core.config import MODULE_COLORS, MODULE_LABELS, MODULE_ICONS, PLOT_THEME
from core.database import (load_all_articles, get_global_stats,
                            count_unread_alerts, get_monitors)
from core.analyzer import get_threat_color
from core.linker import get_cross_module_stats
from core.styles import BASE_CSS, module_css


def _hex_rgb(h: str) -> str:
    h = h.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


def _card(rgb: str, color: str, val: str, lbl: str) -> str:
    return (
        '<div style="background:rgba(' + rgb + ',.08);border:1px solid rgba(' + rgb + ',.25);'
        'border-radius:10px;padding:.9rem;text-align:center">'
        '<div style="font-family:DM Mono,monospace;font-size:1.8rem;'
        'color:' + color + ';font-weight:500">' + val + '</div>'
        '<div style="font-size:.7rem;color:rgba(255,255,255,.4);'
        'margin-top:4px;letter-spacing:.06em">' + lbl + '</div>'
        '</div>'
    )


def _section_label(text: str) -> str:
    return (
        '<div style="font-family:DM Mono,monospace;font-size:.75rem;'
        'color:rgba(255,255,255,.4);letter-spacing:.12em;'
        'text-transform:uppercase;margin-bottom:.8rem">' + text + '</div>'
    )


def render_report():
    st.markdown(BASE_CSS + module_css("home"), unsafe_allow_html=True)

    now_str = datetime.now().strftime("%d %b %Y %H:%M")
    st.markdown(
        '<div style="background:linear-gradient(135deg,#0a0f1e,#0d1b2a,#1a1040);'
        'border:1px solid #2d1b5e;border-radius:12px;'
        'padding:1.2rem 2rem;margin-bottom:1rem">'
        '<div style="font-family:DM Mono,monospace;font-size:1.4rem;'
        'font-weight:500;color:#9B59B6;letter-spacing:.08em">'
        '\U0001f4cb UNIFIED INTELLIGENCE REPORT</div>'
        '<div style="font-family:DM Mono,monospace;font-size:.7rem;'
        'color:rgba(155,89,182,.5);letter-spacing:.12em;'
        'text-transform:uppercase;margin-top:2px">'
        'Laporan Terpadu \u2014 Semua Modul A+B+C+D</div>'
        '<div style="margin-top:8px">'
        '<span style="display:inline-block;font-family:DM Mono,monospace;'
        'font-size:.65rem;background:rgba(155,89,182,.1);'
        'border:1px solid rgba(155,89,182,.3);color:#9B59B6;'
        'border-radius:4px;padding:2px 8px">' + now_str + '</span>'
        '</div></div>',
        unsafe_allow_html=True
    )

    df_all = load_all_articles()
    stats  = get_global_stats()
    cs     = get_cross_module_stats()
    unread = count_unread_alerts()
    mod_s  = stats.get("modules", {})

    if df_all.empty:
        st.info("Belum ada data dari modul manapun. Mulai dengan mengisi keyword di salah satu modul.")
        if st.button("\u2190 Kembali ke Beranda"):
            st.session_state["page"] = "home"
            st.rerun()
        return

    tab1, tab2, tab3 = st.tabs([
        "\U0001f4ca RINGKASAN TERPADU",
        "\U0001f517 ANALISIS KETERHUBUNGAN",
        "\U0001f4cb LAPORAN LENGKAP",
    ])

    # ── TAB 1 ─────────────────────────────────────────────────────────────────
    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        for col, val, lbl, color in [
            (c1, str(stats.get("total", 0)),    "TOTAL ARTIKEL",         "#9B59B6"),
            (c2, str(stats.get("links", 0)),    "KONEKSI ANTAR ARTIKEL", "#4FC3F7"),
            (c3, str(stats.get("monitors", 0)), "MONITOR AKTIF",         "#2ECC71"),
            (c4, str(unread),                   "ALERT BELUM DIBACA",    "#E74C3C"),
        ]:
            with col:
                st.markdown(_card(_hex_rgb(color), color, val, lbl), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(_section_label("BREAKDOWN PER MODUL"), unsafe_allow_html=True)

        cols = st.columns(4)
        for i, (mod, col) in enumerate(zip(["person", "threat", "geo", "media"], cols)):
            color   = MODULE_COLORS[mod]
            icon    = MODULE_ICONS[mod]
            label   = MODULE_LABELS[mod]
            rgb     = _hex_rgb(color)
            n_art   = mod_s.get(mod, 0)
            mod_df  = df_all[df_all["module"] == mod] if not df_all.empty else pd.DataFrame()
            avg_thr = float(mod_df["threat_score"].mean()) if not mod_df.empty else 0
            n_mon   = len(get_monitors(mod))
            thr_color = get_threat_color(avg_thr)

            with col:
                st.markdown(
                    '<div style="background:rgba(' + rgb + ',.08);border:1px solid rgba(' + rgb + ',.25);'
                    'border-left:3px solid ' + color + ';border-radius:8px;'
                    'padding:.9rem;margin-bottom:8px">'
                    '<div style="font-size:1.1rem;margin-bottom:4px">' + icon + '</div>'
                    '<div style="font-family:DM Mono,monospace;font-size:.75rem;'
                    'color:' + color + ';font-weight:500">' + label + '</div>'
                    '<div style="font-family:DM Mono,monospace;font-size:.68rem;'
                    'color:rgba(255,255,255,.4);margin-top:6px;line-height:1.8">'
                    'Artikel: ' + str(n_art) + '<br>'
                    'Monitor: ' + str(n_mon) + '<br>'
                    'Avg Threat: <span style="color:' + thr_color + '">' + str(int(avg_thr)) + '</span>'
                    '</div></div>',
                    unsafe_allow_html=True
                )
                if st.button(icon + " Buka", key="rpt_open_" + mod, use_container_width=True):
                    st.session_state["page"] = mod
                    st.session_state["from_module"] = "report"
                    st.rerun()

        st.markdown(_section_label("PERBANDINGAN METRIK ANTAR MODUL"), unsafe_allow_html=True)

        categories = ["Avg Threat", "Hoax Rate", "Hate Rate", "Coverage", "Velocity"]
        radar_data = {}
        for mod in ["person", "threat", "geo", "media"]:
            mod_df = df_all[df_all["module"] == mod] if not df_all.empty else pd.DataFrame()
            if mod_df.empty:
                radar_data[mod] = [0, 0, 0, 0, 0]
                continue
            radar_data[mod] = [
                float(mod_df["threat_score"].mean()),
                float((mod_df["hoax_score"] >= 50).sum() / len(mod_df) * 100),
                float((mod_df["hate_score"] >= 40).sum() / len(mod_df) * 100),
                min(float(mod_df["source"].nunique()) / 10 * 100, 100),
                min(float(len(mod_df)) / 50 * 100, 100),
            ]

        fig_radar = go.Figure()
        for mod, values in radar_data.items():
            color = MODULE_COLORS[mod]
            fig_radar.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name=MODULE_LABELS[mod],
                line_color=color,
                fillcolor="rgba(" + _hex_rgb(color) + ",0.15)",
                opacity=0.8,
            ))
        fig_radar.update_layout(**PLOT_THEME, height=380,
            polar=dict(
                bgcolor="#0A0F1E",
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="#1E3A5F",
                                tickfont=dict(color="rgba(255,255,255,0.3)", size=9)),
                angularaxis=dict(gridcolor="#1E3A5F",
                                 tickfont=dict(color="rgba(255,255,255,0.5)", size=10)),
            ),
            legend=dict(font=dict(color="rgba(255,255,255,0.6)", size=10),
                        orientation="h", y=-0.1),
            title=dict(text="Radar Perbandingan Modul",
                       font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        st.markdown(_section_label("TIMELINE GABUNGAN SEMUA MODUL"), unsafe_allow_html=True)
        df_tl = df_all.dropna(subset=["published_at"]).copy()
        if not df_tl.empty:
            df_tl["date"] = pd.to_datetime(df_tl["published_at"], errors="coerce").dt.date
            fig_tl = go.Figure()
            for mod in ["person", "threat", "geo", "media"]:
                mod_tl = df_tl[df_tl["module"] == mod].groupby("date").size().reset_index(name="count")
                if not mod_tl.empty:
                    fig_tl.add_trace(go.Scatter(
                        x=mod_tl["date"], y=mod_tl["count"],
                        name=MODULE_LABELS[mod], mode="lines+markers",
                        line=dict(color=MODULE_COLORS[mod], width=2),
                        marker=dict(size=6),
                    ))
            fig_tl.update_layout(**PLOT_THEME, height=280,
                title=dict(text="Volume Artikel per Modul per Hari",
                           font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0),
                hovermode="x unified",
                xaxis=dict(gridcolor="rgba(255,255,255,.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,.05)"),
                legend=dict(font=dict(size=10, color="rgba(255,255,255,0.5)"),
                            orientation="h", y=-0.25),
            )
            st.plotly_chart(fig_tl, use_container_width=True)

    # ── TAB 2 ─────────────────────────────────────────────────────────────────
    with tab2:
        st.markdown(_section_label("ARTIKEL YANG TERHUBUNG LINTAS MODUL"), unsafe_allow_html=True)

        from core.database import get_conn
        try:
            conn = get_conn()
            df_links = pd.read_sql("""
                SELECT cl.link_type, cl.score, cl.modules,
                    a1.title as title_a, s1.module as mod_a,
                    a1.source as src_a, a1.threat_score as thr_a,
                    a2.title as title_b, s2.module as mod_b,
                    a2.source as src_b, a2.threat_score as thr_b
                FROM cross_article_links cl
                JOIN articles a1 ON cl.article_id = a1.id
                JOIN articles a2 ON cl.linked_id  = a2.id
                JOIN sessions s1 ON a1.session_id = s1.id
                JOIN sessions s2 ON a2.session_id = s2.id
                WHERE s1.module != s2.module
                ORDER BY cl.score DESC LIMIT 50
            """, conn)
            conn.close()
        except Exception:
            df_links = pd.DataFrame()

        if df_links.empty:
            st.markdown(
                '<div class="intel-box medium">'
                'Belum ada keterhubungan terdeteksi antar modul.<br>'
                'Pastikan sudah fetch data di minimal 2 modul berbeda dengan keyword yang sama.'
                '</div>',
                unsafe_allow_html=True
            )
        else:
            n_links = len(df_links)
            st.markdown(
                '<div style="font-family:DM Mono;font-size:.7rem;'
                'color:rgba(255,255,255,.3);margin-bottom:8px">'
                + str(n_links) + ' koneksi lintas modul ditemukan</div>',
                unsafe_allow_html=True
            )
            link_type_map = {
                "same_article":  "Artikel Sama",
                "similar_title": "Judul Mirip",
                "shared_entity": "Entitas Sama",
                "same_topic":    "Topik Sama",
            }
            for _, row in df_links.head(20).iterrows():
                ca    = MODULE_COLORS.get(row["mod_a"], "#888")
                cb    = MODULE_COLORS.get(row["mod_b"], "#888")
                ia    = MODULE_ICONS.get(row["mod_a"], "")
                ib    = MODULE_ICONS.get(row["mod_b"], "")
                la    = MODULE_LABELS.get(row["mod_a"], "")
                lb    = MODULE_LABELS.get(row["mod_b"], "")
                ltype = link_type_map.get(row["link_type"], row["link_type"])
                sc    = float(row["score"])
                ta    = str(row["title_a"])[:55] + "..."
                tb    = str(row["title_b"])[:55] + "..."

                st.markdown(
                    '<div style="background:#0D1B2A;border:1px solid #1E3A5F;'
                    'border-radius:8px;padding:.75rem 1rem;margin-bottom:6px">'
                    '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
                    '<span style="font-family:DM Mono,monospace;font-size:.65rem;'
                    'background:rgba(155,89,182,.12);border:1px solid rgba(155,89,182,.3);'
                    'color:#9B59B6;padding:1px 6px;border-radius:3px">' + ltype + '</span>'
                    '<span style="font-family:DM Mono,monospace;font-size:.65rem;'
                    'color:rgba(255,255,255,.3)">SCORE: ' + str(round(sc, 2)) + '</span>'
                    '</div>'
                    '<div style="display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center">'
                    '<div style="background:rgba(' + _hex_rgb(ca) + ',.08);'
                    'border:1px solid rgba(' + _hex_rgb(ca) + ',.2);'
                    'border-radius:6px;padding:.5rem .7rem">'
                    '<div style="font-family:DM Mono,monospace;font-size:.65rem;'
                    'color:' + ca + ';margin-bottom:2px">' + ia + ' ' + la + '</div>'
                    '<div style="font-size:.8rem;font-weight:500;color:white">' + ta + '</div>'
                    '<div style="font-family:DM Mono,monospace;font-size:.65rem;'
                    'color:rgba(255,255,255,.35)">[' + str(row["src_a"]) + '] THREAT:' + str(int(row["thr_a"])) + '</div>'
                    '</div>'
                    '<div style="color:rgba(155,89,182,.6);font-size:1.2rem;text-align:center">&#8596;</div>'
                    '<div style="background:rgba(' + _hex_rgb(cb) + ',.08);'
                    'border:1px solid rgba(' + _hex_rgb(cb) + ',.2);'
                    'border-radius:6px;padding:.5rem .7rem">'
                    '<div style="font-family:DM Mono,monospace;font-size:.65rem;'
                    'color:' + cb + ';margin-bottom:2px">' + ib + ' ' + lb + '</div>'
                    '<div style="font-size:.8rem;font-weight:500;color:white">' + tb + '</div>'
                    '<div style="font-family:DM Mono,monospace;font-size:.65rem;'
                    'color:rgba(255,255,255,.35)">[' + str(row["src_b"]) + '] THREAT:' + str(int(row["thr_b"])) + '</div>'
                    '</div>'
                    '</div></div>',
                    unsafe_allow_html=True
                )

    # ── TAB 3 ─────────────────────────────────────────────────────────────────
    with tab3:
        now_rpt = datetime.now().strftime("%d %B %Y %H:%M")
        mod_summaries = {}
        for mod in ["person", "threat", "geo", "media"]:
            mod_df = df_all[df_all["module"] == mod] if not df_all.empty else pd.DataFrame()
            if mod_df.empty:
                mod_summaries[mod] = "   Belum ada data"
                continue
            top_kw = get_monitors(mod)["keyword"].tolist()[:3] if not get_monitors(mod).empty else []
            mod_summaries[mod] = (
                "   Artikel   : " + str(len(mod_df)) + "\n"
                "   Avg Threat: " + str(round(float(mod_df["threat_score"].mean()), 1)) + "/100\n"
                "   Tinggi    : " + str(int((mod_df["threat_score"] >= 60).sum())) + "\n"
                "   Sumber    : " + str(int(mod_df["source"].nunique())) + "\n"
                "   Keyword   : " + (", ".join(top_kw) if top_kw else "N/A")
            )

        report = (
            "\u2554" + "\u2550" * 66 + "\u2557\n"
            "\u2551         UNIFIED INTELLIGENCE REPORT \u2014 OSINT SUITE              \u2551\n"
            "\u2551              LAPORAN TERPADU SEMUA MODUL A+B+C+D               \u2551\n"
            "\u255a" + "\u2550" * 66 + "\u255d\n\n"
            "NOMOR  : UNIFIED-" + datetime.now().strftime("%Y%m%d%H%M") + "\n"
            "TANGGAL: " + now_rpt + "\n"
            "SISTEM : OSINT Intelligence Suite v1.0\n"
            "STATUS : AKTIF\n\n"
            "\u2501" * 66 + "\n\n"
            "1. RINGKASAN EKSEKUTIF\n"
            "   Total Artikel Terkumpul : " + str(stats.get("total", 0)) + "\n"
            "   Koneksi Lintas Modul    : " + str(stats.get("links", 0)) + "\n"
            "   Monitor Aktif           : " + str(stats.get("monitors", 0)) + "\n"
            "   Alert Belum Dibaca      : " + str(unread) + "\n\n"
            "2. MODUL A \u2014 PERSON & ENTITY INTELLIGENCE\n" + mod_summaries.get("person", "") + "\n\n"
            "3. MODUL B \u2014 THREAT INTELLIGENCE\n" + mod_summaries.get("threat", "") + "\n\n"
            "4. MODUL C \u2014 GEOSPATIAL INTELLIGENCE\n" + mod_summaries.get("geo", "") + "\n\n"
            "5. MODUL D \u2014 MEDIA & NARRATIVE INTELLIGENCE\n" + mod_summaries.get("media", "") + "\n\n"
            "6. ANALISIS KETERHUBUNGAN\n"
            "   Total koneksi terdeteksi: " + str(stats.get("links", 0)) + " hubungan lintas modul.\n\n"
            "\u2501" * 66 + "\n"
            "[AKHIR LAPORAN TERPADU] \u2014 OSINT Intelligence Suite v1.0\n"
        )

        st.markdown('<div class="report-box">' + report + '</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "\u2b07 Download Laporan Terpadu (.txt)", data=report,
                file_name="unified_report_" + datetime.now().strftime("%Y%m%d%H%M") + ".txt",
                mime="text/plain",
            )
        with c2:
            if not df_all.empty:
                csv = df_all[["module","title","source","published_at",
                              "threat_score","hoax_score","hate_score",
                              "location","province","severity","url"]].to_csv(index=False)
                st.download_button(
                    "\u2b07 Export Semua Data (.csv)", data=csv,
                    file_name="all_data_" + datetime.now().strftime("%Y%m%d") + ".csv",
                    mime="text/csv",
                )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("\u2190 Kembali ke Beranda", use_container_width=True):
        st.session_state["page"] = "home"
        st.rerun()
