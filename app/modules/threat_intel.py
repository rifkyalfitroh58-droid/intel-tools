"""
OSINT Intelligence Suite — threat_intel.py
Modul B: Threat & Disinformation Intelligence
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys, os, re
from datetime import datetime
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core.config import THREAT_CATEGORIES, PLOT_THEME
from core.database import load_articles, load_narratives, load_alerts, get_global_stats, mark_alerts_read
from core.analyzer import get_threat_color, get_threat_label
from core.styles import BASE_CSS, module_css
from components.header import render_header
from components.article_card import render_article_card, render_link_panel
import json


def _compute_spread(df_art):
    """Hitung spread rate dari dataframe."""
    import math
    if df_art.empty:
        return {"score":0,"velocity":0,"peak_hour":"N/A","trend":"stable"}
    try:
        df_ts = df_art.dropna(subset=["published_at"]).copy()
        if df_ts.empty:
            return {"score":0,"velocity":0,"peak_hour":"N/A","trend":"stable"}
        df_ts["hour"] = df_ts["published_at"].dt.floor("h")
        hourly = df_ts.groupby("hour").size()
        velocity  = float(hourly.mean())
        peak_hour = str(hourly.idxmax().strftime("%d %b %H:00")) if not hourly.empty else "N/A"
        max_vol   = int(hourly.max())
        score     = min(math.log1p(max_vol) / math.log1p(50) * 100, 100)
        if len(hourly) >= 3:
            recent = hourly.iloc[-3:].mean()
            older  = hourly.iloc[:-3].mean() if len(hourly) > 3 else recent
            trend  = "rising" if recent > older*1.2 else "falling" if recent < older*0.8 else "stable"
        else:
            trend = "stable"
        return {"score":round(score,1),"velocity":round(velocity,2),
                "peak_hour":peak_hour,"trend":trend}
    except Exception:
        return {"score":0,"velocity":0,"peak_hour":"N/A","trend":"stable"}


def _hex_rgb(h):
    h = h.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


def render_threat_intel(monitor_id: int, monitor_kw: str):
    st.markdown(BASE_CSS + module_css("threat"), unsafe_allow_html=True)
    render_header("threat", monitor_kw,
                  unread_alerts=get_global_stats().get("unread_alerts", 0))

    if not monitor_id:
        st.info("👈 Tambah keyword di sidebar untuk mulai analisis.")
        return

    df_art  = load_articles(monitor_id)
    df_narr = load_narratives(monitor_id)
    df_alrt = load_alerts()

    if df_art.empty:
        st.warning("Belum ada data. Coba update di sidebar.")
        return

    n         = len(df_art)
    n_high    = int((df_art["threat_score"] >= 60).sum())
    n_hoax    = int((df_art["hoax_score"]   >= 50).sum())
    n_hate    = int((df_art["hate_score"]   >= 40).sum())
    n_provok  = int((df_art["provok_score"] >= 40).sum())
    avg_thr   = float(df_art["threat_score"].mean())
    spread    = _compute_spread(df_art)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⚠ OVERVIEW", "🔥 THREAT FEED", "📊 ANALISIS", "📡 SPREAD", "📋 LAPORAN"
    ])

    # ── TAB 1: OVERVIEW ───────────────────────────────────────────────────────
    with tab1:
        c1,c2,c3,c4,c5 = st.columns(5)
        for col, val, lbl, color in [
            (c1, str(n),       "TOTAL KONTEN",   "#4FC3F7"),
            (c2, str(n_high),  "ANCAMAN TINGGI", "#E74C3C"),
            (c3, str(n_hoax),  "HOAKS",          "#E67E22"),
            (c4, str(n_hate),  "HATE SPEECH",    "#F39C12"),
            (c5, f"{avg_thr:.0f}", "AVG THREAT", get_threat_color(avg_thr)),
        ]:
            with col:
                st.markdown(f"""
                <div class="suite-card threat">
                    <div class="metric-num" style="color:{color}">{val}</div>
                    <div class="metric-label">{lbl}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown('<hr style="border-color:#3d1515;margin:.8rem 0">',
                    unsafe_allow_html=True)
        col_g, col_d, col_f = st.columns([1,1,2])

        with col_g:
            st.markdown('<div class="sec-title threat">&#9661; THREAT LEVEL</div>',
                        unsafe_allow_html=True)
            tc = get_threat_color(avg_thr)
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number", value=avg_thr,
                gauge=dict(
                    axis=dict(range=[0,100],
                              tickfont=dict(color="rgba(255,255,255,0.3)", size=9)),
                    bar=dict(color=tc, thickness=0.3),
                    bgcolor="#080202", bordercolor="#3d1515",
                    steps=[
                        dict(range=[0,40],   color="rgba(46,204,113,0.06)"),
                        dict(range=[40,60],  color="rgba(243,156,18,0.06)"),
                        dict(range=[60,80],  color="rgba(230,126,34,0.06)"),
                        dict(range=[80,100], color="rgba(231,76,60,0.08)"),
                    ],
                ),
                number=dict(font=dict(color=tc, size=34, family="DM Mono"),
                            suffix="/100"),
                title=dict(text=get_threat_label(avg_thr),
                           font=dict(color=tc, size=12, family="DM Mono")),
            ))
            _plot = {k:v for k,v in PLOT_THEME.items() if k not in ["xaxis","yaxis"]}
            _plot["plot_bgcolor"] = "#080202"
            _plot["paper_bgcolor"]= "#0d0505"
            fig_g.update_layout(**_plot, height=220)
            st.plotly_chart(fig_g, use_container_width=True)

            for lbl2, val2, mx2, c2 in [
                ("Hoax",      float(df_art["hoax_score"].mean()),   100, "#E74C3C"),
                ("Hate",      float(df_art["hate_score"].mean()),   100, "#E67E22"),
                ("Provokasi", float(df_art["provok_score"].mean()), 100, "#F39C12"),
            ]:
                pct = val2/mx2*100
                st.markdown(f"""
                <div style="font-family:'DM Mono',monospace;font-size:.68rem;
                            color:rgba(255,255,255,.5);margin-bottom:6px">
                    {lbl2:<12} {val2:5.1f}/100
                    <div style="background:#3d1515;border-radius:3px;height:4px;margin-top:2px">
                        <div style="background:{c2};height:4px;border-radius:3px;
                                    width:{pct:.1f}%"></div>
                    </div>
                </div>""", unsafe_allow_html=True)

        with col_d:
            st.markdown('<div class="sec-title threat">&#9661; DISTRIBUSI</div>',
                        unsafe_allow_html=True)
            dom_counts = df_art["threat_dominant"].value_counts()
            colors_pie = [THREAT_CATEGORIES.get(k,{}).get("color","#888")
                          for k in dom_counts.index]
            labels_pie = [THREAT_CATEGORIES.get(k,{}).get("label",k)
                          for k in dom_counts.index]
            fig_pie = go.Figure(go.Pie(
                labels=labels_pie, values=dom_counts.values,
                marker_colors=colors_pie, hole=0.55,
                hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
            ))
            _plot_p = {k:v for k,v in PLOT_THEME.items() if k not in ["xaxis","yaxis"]}
            _plot_p["plot_bgcolor"]  = "#080202"
            _plot_p["paper_bgcolor"] = "#0d0505"
            fig_pie.update_layout(**_plot_p, height=240,
                showlegend=True,
                legend=dict(font=dict(size=9, color="rgba(255,255,255,0.4)"),
                            orientation="h", y=-0.15),
                annotations=[dict(text=f"<b>{n}</b>", x=0.5, y=0.5,
                                  font_size=16, font_color="#E74C3C",
                                  showarrow=False)],
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            # Spread info
            trend_c = "#E74C3C" if spread["trend"]=="rising" else \
                      "#2ECC71" if spread["trend"]=="falling" else "#F39C12"
            trend_i = "↑" if spread["trend"]=="rising" else \
                      "↓" if spread["trend"]=="falling" else "→"
            st.markdown(f"""
            <div style="background:#0d0505;border:1px solid #3d1515;
                        border-radius:8px;padding:.6rem .9rem">
                <div style="font-family:'DM Mono',monospace;font-size:.62rem;
                            color:rgba(231,76,60,.4);margin-bottom:4px">SPREAD</div>
                <div style="font-family:'DM Mono',monospace;font-size:1.2rem;
                            color:{trend_c}">{trend_i} {spread['score']:.0f}/100</div>
                <div style="font-size:.7rem;color:rgba(255,255,255,.3);margin-top:2px">
                    Peak: {spread['peak_hour']}
                </div>
            </div>""", unsafe_allow_html=True)

        with col_f:
            st.markdown('<div class="sec-title threat">&#9661; KONTEN ANCAMAN TERBARU</div>',
                        unsafe_allow_html=True)
            high_arts = df_art[df_art["threat_score"] >= 40].head(6)
            if high_arts.empty:
                st.markdown('<div class="intel-box low">Tidak ada ancaman signifikan.</div>',
                            unsafe_allow_html=True)
            else:
                for _, row in high_arts.iterrows():
                    render_article_card(row.to_dict(), "threat")

        if st.session_state.get("show_panel") and st.session_state.get("panel_article_id"):
            st.markdown('<div class="sec-title neutral">&#9661; PANEL KETERHUBUNGAN</div>',
                        unsafe_allow_html=True)
            render_link_panel(st.session_state["panel_article_id"])

        # Timeline
        st.markdown('<div class="sec-title threat">&#9661; TIMELINE ANCAMAN</div>',
                    unsafe_allow_html=True)
        df_ts = df_art.dropna(subset=["published_at"]).copy()
        if not df_ts.empty:
            df_ts["date"] = df_ts["published_at"].dt.date
            tl = df_ts.groupby("date").agg(
                count=("id","count"),
                avg_threat=("threat_score","mean"),
            ).reset_index()
            fig_tl = make_subplots(specs=[[{"secondary_y":True}]])
            fig_tl.add_trace(go.Bar(
                x=tl["date"], y=tl["count"], name="Volume",
                marker_color="#E74C3C", marker_opacity=0.6,
            ), secondary_y=False)
            fig_tl.add_trace(go.Scatter(
                x=tl["date"], y=tl["avg_threat"], name="Avg Threat",
                line=dict(color="#F39C12", width=2), mode="lines+markers",
            ), secondary_y=True)
            _plot_tl = {k:v for k,v in PLOT_THEME.items() if k not in ["xaxis","yaxis"]}
            _plot_tl["plot_bgcolor"]  = "#080202"
            _plot_tl["paper_bgcolor"] = "#0d0505"
            fig_tl.update_layout(**_plot_tl, height=220,
                title=dict(text="Volume &amp; Threat Score per Hari",
                           font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0),
                xaxis=dict(showgrid=True, gridcolor="#3d1515"),
                yaxis=dict(showgrid=True, gridcolor="#3d1515"),
                yaxis2=dict(overlaying="y", side="right",
                            showgrid=False, range=[0,100]),
                hovermode="x unified",
                legend=dict(orientation="h", y=-0.25,
                            font=dict(size=10, color="rgba(255,255,255,0.4)")),
            )
            st.plotly_chart(fig_tl, use_container_width=True)

        # Tombol lanjut
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Kembali ke Person Intel", use_container_width=True):
                st.session_state["page"] = "person"
                st.session_state["from_module"] = "threat"
                st.rerun()
        with c2:
            if st.button("🗺 Lanjut ke Geo Intel →", use_container_width=True):
                st.session_state["page"] = "geo"
                st.session_state["from_module"] = "threat"
                st.session_state["pending_keyword"] = monitor_kw
                st.rerun()

    # ── TAB 2: THREAT FEED ────────────────────────────────────────────────────
    with tab2:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_type = st.selectbox(
                "Tipe filter",
                ["Semua","Hoaks","Hate Speech","Provokasi","Kritis"],
                label_visibility="collapsed", key="threat_filter_type"
            )
        with col_f2:
            filter_score = st.slider("Min threat score", 0, 100, 0,
                                     key="threat_filter_score")
        with col_f3:
            sort_by = st.selectbox(
                "Urutkan berdasarkan",
                ["Threat Score","Hoax Score","Hate Score","Terbaru"],
                label_visibility="collapsed", key="threat_sort"
            )

        df_feed = df_art.copy()
        if filter_type == "Hoaks":        df_feed = df_feed[df_feed["hoax_score"]>=40]
        elif filter_type == "Hate Speech": df_feed = df_feed[df_feed["hate_score"]>=40]
        elif filter_type == "Provokasi":   df_feed = df_feed[df_feed["provok_score"]>=40]
        elif filter_type == "Kritis":      df_feed = df_feed[df_feed["threat_score"]>=80]
        df_feed = df_feed[df_feed["threat_score"] >= filter_score]
        sort_map = {"Threat Score":"threat_score","Hoax Score":"hoax_score",
                    "Hate Score":"hate_score","Terbaru":"published_at"}
        df_feed = df_feed.sort_values(sort_map[sort_by], ascending=False)

        st.markdown(
            f'<div style="font-family:DM Mono;font-size:.7rem;'
            f'color:rgba(255,255,255,.3);margin-bottom:8px">'
            f'{len(df_feed)} konten ditemukan</div>',
            unsafe_allow_html=True
        )
        for _, row in df_feed.head(30).iterrows():
            render_article_card(row.to_dict(), "threat")

        if st.session_state.get("show_panel") and st.session_state.get("panel_article_id"):
            render_link_panel(st.session_state["panel_article_id"])

    # ── TAB 3: ANALISIS ───────────────────────────────────────────────────────
    with tab3:
        c1, c2 = st.columns(2)
        with c1:
            fig_sc = go.Figure(go.Scatter(
                x=df_art["hoax_score"], y=df_art["hate_score"],
                mode="markers",
                marker=dict(
                    color=df_art["threat_score"],
                    colorscale=[[0,"#2ECC71"],[0.4,"#F39C12"],
                                [0.7,"#E67E22"],[1,"#E74C3C"]],
                    size=8, opacity=0.7,
                    colorbar=dict(title="Threat", thickness=10,
                                  tickfont=dict(color="rgba(255,255,255,0.4)", size=9)),
                    showscale=True,
                ),
                hovertemplate="Hoax: %{x:.1f}<br>Hate: %{y:.1f}<extra></extra>",
            ))
            _pt = {**PLOT_THEME,
                   "plot_bgcolor":  "#080202",
                   "paper_bgcolor": "#0d0505",
                   "xaxis": dict(showgrid=True, gridcolor="#3d1515",
                                 tickfont=dict(color="rgba(255,255,255,0.4)")),
                   "yaxis": dict(showgrid=True, gridcolor="#3d1515",
                                 tickfont=dict(color="rgba(255,255,255,0.4)"))}
            fig_sc.update_layout(**_pt, height=280,
                title=dict(text="Hoax vs Hate Speech Score",
                           font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0))
            st.plotly_chart(fig_sc, use_container_width=True)

        with c2:
            src_threat = df_art.groupby("source").agg(
                avg_threat=("threat_score","mean"),
                count=("id","count"),
            ).sort_values("avg_threat", ascending=False).head(10).reset_index()
            colors_src = [get_threat_color(s) for s in src_threat["avg_threat"]]
            fig_src = go.Figure(go.Bar(
                x=src_threat["avg_threat"], y=src_threat["source"],
                orientation="h", marker_color=colors_src,
                text=[f"{v:.0f} ({c})" for v,c in
                      zip(src_threat["avg_threat"], src_threat["count"])],
                textfont=dict(size=10), textposition="outside",
            ))
            fig_src.update_layout(**_pt, height=280,
                title=dict(text="Sumber Ancaman Tertinggi",
                           font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0))
            st.plotly_chart(fig_src, use_container_width=True)

        # Narratif
        st.markdown('<div class="sec-title threat">&#9661; KLASTER NARASI</div>',
                    unsafe_allow_html=True)
        NARR_COLORS = ["#E74C3C","#E67E22","#F39C12","#9B59B6","#3498DB"]
        if not df_narr.empty:
            for i in range(0, min(len(df_narr),6), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i+j >= len(df_narr): break
                    row  = df_narr.iloc[i+j]
                    color = NARR_COLORS[(i+j) % len(NARR_COLORS)]
                    rgb   = _hex_rgb(color)
                    try:
                        kws = json.loads(row["keywords"]) if isinstance(row["keywords"],str) else []
                    except Exception:
                        kws = []
                    tags = " ".join([
                        f'<span style="font-family:DM Mono,monospace;font-size:.68rem;'
                        f'background:rgba({rgb},.12);border:1px solid rgba({rgb},.3);'
                        f'color:{color};padding:1px 7px;border-radius:3px">{kw}</span>'
                        for kw in kws[:5]
                    ])
                    with col:
                        st.markdown(f"""
                        <div class="intel-box" style="border-color:rgba({rgb},.3)">
                            <div style="font-family:'DM Mono',monospace;font-size:.65rem;
                                        color:rgba(255,255,255,.3)">NARASI {row['id']:02d}
                                · {row['count']} konten</div>
                            <div style="color:{color};font-weight:500;margin:4px 0">
                                {row['label']}</div>
                            <div>{tags}</div>
                        </div>""", unsafe_allow_html=True)
        else:
            st.info("Belum ada klaster narasi.")

    # ── TAB 4: SPREAD ─────────────────────────────────────────────────────────
    with tab4:
        c1,c2,c3 = st.columns(3)
        trend_c = "#E74C3C" if spread["trend"]=="rising" else \
                  "#2ECC71" if spread["trend"]=="falling" else "#F39C12"
        for col, val, lbl in [
            (c1, f"{spread['score']:.0f}", "SPREAD SCORE"),
            (c2, f"{spread['velocity']:.1f}", "ARTIKEL/JAM"),
            (c3, {"rising":"↑ NAIK","falling":"↓ TURUN","stable":"→ STABIL"}.get(spread["trend"],"→"), "TREN"),
        ]:
            with col:
                st.markdown(f"""
                <div class="suite-card threat">
                    <div class="metric-num" style="color:{trend_c}">{val}</div>
                    <div class="metric-label">{lbl}</div>
                </div>""", unsafe_allow_html=True)

        # Alert history
        st.markdown('<div class="sec-title threat">&#9661; RIWAYAT ALERT</div>',
                    unsafe_allow_html=True)
        if df_alrt.empty:
            st.markdown('<div class="intel-box low">Belum ada alert.</div>',
                        unsafe_allow_html=True)
        else:
            for _, row in df_alrt.head(15).iterrows():
                sc   = row["threat_score"]
                color= get_threat_color(sc)
                cat  = THREAT_CATEGORIES.get(row["alert_type"],{})
                crat = row["created_at"].strftime("%d %b %H:%M") \
                       if pd.notna(row["created_at"]) else ""
                st.markdown(f"""
                <div style="display:flex;align-items:flex-start;gap:10px;
                            background:#0d0505;border:1px solid #3d1515;
                            border-radius:8px;padding:.6rem .9rem;margin-bottom:6px">
                    <div style="width:8px;height:8px;border-radius:50%;
                                background:{color};flex-shrink:0;margin-top:4px"></div>
                    <div>
                        <div style="font-size:.82rem;color:rgba(255,255,255,.8)">
                            {row['message']}</div>
                        <div style="font-family:'DM Mono',monospace;font-size:.68rem;
                                    color:rgba(255,255,255,.35);margin-top:2px">
                            {crat} · {cat.get('label',row['alert_type'])} ·
                            <span style="color:{color}">THREAT:{sc:.0f}</span>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)
            if st.button("✓ Tandai semua sudah dibaca",
                         key="mark_read_threat"):
                mark_alerts_read()
                st.rerun()

    # ── TAB 5: LAPORAN ────────────────────────────────────────────────────────
    with tab5:
        now_rpt  = datetime.now().strftime("%d %B %Y %H:%M")
        top3     = df_art.nlargest(3,"threat_score")
        top_src  = df_art.groupby("source")["threat_score"].mean().sort_values(ascending=False).head(5)
        n_kritis = int((df_art["threat_score"]>=80).sum())
        type_bd  = df_art["threat_dominant"].value_counts()
        type_lines = "\n".join(
            f"   {THREAT_CATEGORIES.get(k,{}).get('label',k):<25}: {v}"
            for k,v in type_bd.items()
        )
        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║         LAPORAN THREAT INTELLIGENCE (B)                         ║
╚══════════════════════════════════════════════════════════════════╝

NOMOR  : THREAT-{monitor_id:04d}-{datetime.now().strftime('%Y%m%d')}
TANGGAL: {now_rpt}
KEYWORD: {monitor_kw}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. RINGKASAN
   Total Konten  : {n}
   Ancaman Kritis: {n_kritis}
   Ancaman Tinggi: {int((df_art['threat_score']>=60).sum())}
   Avg Threat    : {avg_thr:.1f}/100 — {get_threat_label(avg_thr)}

2. BREAKDOWN ANCAMAN
{type_lines}

3. SPREAD RATE
   Score    : {spread['score']:.1f}/100
   Velocity : {spread['velocity']:.2f} artikel/jam
   Trend    : {spread['trend'].upper()}
   Peak     : {spread['peak_hour']}

4. KONTEN PALING BERBAHAYA
{chr(10).join(f"   [{r['source']}] {str(r['title'])[:65]}... (THREAT:{r['threat_score']:.0f})" for _,r in top3.iterrows())}

5. SUMBER BERISIKO
{chr(10).join(f"   {i+1}. {s} — avg: {v:.0f}" for i,(s,v) in enumerate(top_src.items()))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[AKHIR LAPORAN B] — OSINT Intelligence Suite v1.0
"""
        st.markdown(f'<div class="report-box">{report}</div>',
                    unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            st.download_button("⬇ Download (.txt)", data=report,
                file_name=f"threat_{monitor_kw.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain")
        with c2:
            csv = df_art[["title","source","published_at","threat_score",
                           "hoax_score","hate_score","provok_score","url"]].to_csv(index=False)
            st.download_button("⬇ Export (.csv)", data=csv,
                file_name=f"threat_data_{monitor_kw.replace(' ','_')}.csv",
                mime="text/csv")
