"""
OSINT Intelligence Suite — media_intel.py
Modul D: Media & Narrative Intelligence
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import networkx as nx
import re, json, sys, os
from datetime import datetime
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core.config import PLOT_THEME
from core.database import load_articles, load_narratives, get_global_stats
from core.analyzer import get_threat_color, get_risk_color, cluster_narratives

_STOPWORDS = {
    "yang","di","ke","dan","dari","dengan","ini","itu","tidak","untuk",
    "ada","bisa","pada","juga","akan","sudah","karena","saat","oleh",
    "the","a","an","in","of","to","and","or","for","on","at","is","are",
    "was","were","with","this","that","it","as","be","has","have","had",
    "will","would","can","could","from","but","not","so","by","via",
}
from core.styles import BASE_CSS, module_css
from components.header import render_header
from components.article_card import render_article_card, render_link_panel


NARR_COLORS = ["#E74C3C","#3498DB","#F39C12","#9B59B6","#2ECC71","#1ABC9C","#E67E22"]


def _hex_rgb(h):
    h = h.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


def _media_velocity(df_art: pd.DataFrame) -> dict:
    """Hitung kecepatan penyebaran isu di media."""
    if df_art.empty:
        return {"articles_per_day": 0, "unique_sources": 0,
                "peak_day": "N/A", "momentum": "stable"}
    try:
        df_ts = df_art.dropna(subset=["published_at"]).copy()
        if df_ts.empty:
            return {"articles_per_day": 0, "unique_sources": 0,
                    "peak_day": "N/A", "momentum": "stable"}
        df_ts["date"] = df_ts["published_at"].dt.date
        daily     = df_ts.groupby("date").size()
        apd       = float(daily.mean())
        peak_day  = str(daily.idxmax()) if not daily.empty else "N/A"
        n_src     = int(df_art["source"].nunique())
        if len(daily) >= 3:
            recent = daily.iloc[-3:].mean()
            older  = daily.iloc[:-3].mean() if len(daily) > 3 else recent
            mom    = "rising" if recent > older*1.2 else \
                     "falling" if recent < older*0.8 else "stable"
        else:
            mom = "stable"
        return {"articles_per_day": round(apd,1), "unique_sources": n_src,
                "peak_day": peak_day, "momentum": mom}
    except Exception:
        return {"articles_per_day": 0, "unique_sources": 0,
                "peak_day": "N/A", "momentum": "stable"}


def _source_network(df_art: pd.DataFrame):
    """Bangun network graph antar sumber berdasarkan co-occurrence keyword."""
    if df_art.empty or len(df_art) < 3:
        return None
    sources = df_art["source"].value_counts().head(15).index.tolist()
    texts_by_src = {
        src: " ".join(df_art[df_art["source"]==src]["title"].fillna("").tolist())
        for src in sources
    }
    G = nx.Graph()
    for src in sources:
        G.add_node(src, count=int((df_art["source"]==src).sum()))

    for i, s1 in enumerate(sources):
        for s2 in sources[i+1:]:
            w1 = set(re.findall(r'[a-zA-Z]{4,}', texts_by_src[s1].lower()))
            w2 = set(re.findall(r'[a-zA-Z]{4,}', texts_by_src[s2].lower()))
            w1 = {w for w in w1 if w not in _STOPWORDS}
            w2 = {w for w in w2 if w not in _STOPWORDS}
            shared = len(w1 & w2)
            if shared >= 3:
                G.add_edge(s1, s2, weight=shared)
    return G


def render_media_intel(monitor_id: int, monitor_kw: str):
    st.markdown(BASE_CSS + module_css("media"), unsafe_allow_html=True)
    render_header("media", monitor_kw,
                  unread_alerts=get_global_stats().get("unread_alerts", 0))

    if not monitor_id:
        st.info("👈 Tambah keyword di sidebar untuk mulai analisis.")
        return

    df_art  = load_articles(monitor_id)
    df_narr = load_narratives(monitor_id)

    if df_art.empty:
        st.warning("Belum ada data. Coba update di sidebar.")
        return

    n       = len(df_art)
    n_src   = int(df_art["source"].nunique())
    avg_thr = float(df_art["threat_score"].mean())
    vel     = _media_velocity(df_art)
    clusters= cluster_narratives(df_art.to_dict("records"), n_clusters=5)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📰 OVERVIEW", "🕸 NARRATIVE WEB", "📡 VELOCITY", "🔗 SOURCE NETWORK", "📋 LAPORAN"
    ])

    # ── TAB 1: OVERVIEW ───────────────────────────────────────────────────────
    with tab1:
        c1,c2,c3,c4,c5 = st.columns(5)
        mom_c = "#E74C3C" if vel["momentum"]=="rising" else \
                "#2ECC71" if vel["momentum"]=="falling" else "#F39C12"
        for col, val, lbl, color in [
            (c1, str(n),                 "TOTAL ARTIKEL",  "#F39C12"),
            (c2, str(n_src),             "SUMBER MEDIA",   "#4FC3F7"),
            (c3, str(len(clusters)),     "NARASI AKTIF",   "#9B59B6"),
            (c4, f"{vel['articles_per_day']:.1f}", "ARTIKEL/HARI", "#F39C12"),
            (c5, f"{avg_thr:.0f}",       "AVG THREAT",     get_threat_color(avg_thr)),
        ]:
            with col:
                st.markdown(f"""
                <div class="suite-card media">
                    <div class="metric-num" style="color:{color}">{val}</div>
                    <div class="metric-label">{lbl}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown('<hr style="border-color:#3d3515;margin:.8rem 0">',
                    unsafe_allow_html=True)

        # Klaster narasi ringkasan
        st.markdown('<div class="sec-title media">&#9661; NARASI YANG TERIDENTIFIKASI</div>',
                    unsafe_allow_html=True)
        if clusters:
            for i in range(0, len(clusters), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i+j >= len(clusters): break
                    t     = clusters[i+j]
                    color = NARR_COLORS[(i+j) % len(NARR_COLORS)]
                    rgb   = _hex_rgb(color)
                    kws   = " ".join([
                        f'<span style="font-family:DM Mono,monospace;font-size:.68rem;'
                        f'background:rgba({rgb},.12);border:1px solid rgba({rgb},.3);'
                        f'color:{color};padding:1px 7px;border-radius:3px">{kw}</span>'
                        for kw in t["keywords"][:5]
                    ])
                    with col:
                        st.markdown(f"""
                        <div class="intel-box" style="border-color:rgba({rgb},.3)">
                            <div style="font-family:'DM Mono',monospace;font-size:.65rem;
                                        color:rgba(255,255,255,.3)">
                                NARASI {t['id']:02d} · {t['count']} artikel</div>
                            <div style="color:{color};font-weight:500;margin:4px 0">
                                {t['label']}</div>
                            <div>{kws}</div>
                        </div>""", unsafe_allow_html=True)
        else:
            st.info("Belum ada klaster narasi — perlu lebih banyak artikel.")

        # Artikel terbaru
        st.markdown('<div class="sec-title media">&#9661; ARTIKEL TERBARU</div>',
                    unsafe_allow_html=True)
        for _idx, (_, row) in enumerate(df_art.head(6).iterrows()):
            render_article_card(row.to_dict(), "media", idx=int(str(1000 + _idx)))

        if st.session_state.get("show_panel") and st.session_state.get("panel_article_id"):
            render_link_panel(st.session_state["panel_article_id"])

        # Tombol navigasi
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Kembali ke Geo Intel", use_container_width=True):
                st.session_state["page"] = "geo"
                st.session_state["from_module"] = "media"
                st.rerun()
        with c2:
            if st.button("📋 Lihat Laporan Terpadu →", use_container_width=True):
                st.session_state["page"] = "report"
                st.session_state["from_module"] = "media"
                st.rerun()

    # ── TAB 2: NARRATIVE WEB ──────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="sec-title media">&#9661; PETA NARASI</div>',
                    unsafe_allow_html=True)
        if not clusters:
            st.info("Belum ada klaster narasi.")
        else:
            selected_narr = st.selectbox(
                "Pilih narasi",
                [f"Narasi {t['id']} — {t['label']}" for t in clusters],
                label_visibility="collapsed",
                key="media_narr_sel"
            )
            t_idx = int(selected_narr.split(" ")[1]) - 1
            t_sel = clusters[t_idx]
            kws_lw = [k.lower() for k in t_sel["keywords"][:4]]
            mask = (
                df_art["title"].str.lower().apply(
                    lambda x: any(k in str(x) for k in kws_lw)
                ) | df_art["description"].str.lower().apply(
                    lambda x: any(k in str(x) for k in kws_lw)
                )
            )
            df_narr_arts = df_art[mask].head(10)

            color = NARR_COLORS[t_idx % len(NARR_COLORS)]
            rgb   = _hex_rgb(color)

            st.markdown(f"""
            <div class="intel-box" style="border-color:rgba({rgb},.4)">
                <div style="font-family:'DM Mono',monospace;font-size:.7rem;
                            color:rgba(255,255,255,.3);margin-bottom:4px">NARASI</div>
                <div style="color:{color};font-size:1rem;font-weight:500">
                    {t_sel['label']}</div>
                <div style="font-size:.82rem;color:rgba(255,255,255,.5);margin-top:4px">
                    {t_sel['count']} artikel terkait ·
                    Keywords: {', '.join(t_sel['keywords'][:6])}
                </div>
            </div>""", unsafe_allow_html=True)

            if df_narr_arts.empty:
                st.info("Tidak ada artikel yang cocok dengan narasi ini.")
            else:
                for _idx, (_, row) in enumerate(df_narr_arts.iterrows()):
                    render_article_card(row.to_dict(), "media", idx=int(str(2000 + _idx)))

    # ── TAB 3: VELOCITY ───────────────────────────────────────────────────────
    with tab3:
        st.markdown('<div class="sec-title media">&#9661; KECEPATAN PENYEBARAN ISU</div>',
                    unsafe_allow_html=True)

        c1,c2,c3 = st.columns(3)
        mom_color = "#E74C3C" if vel["momentum"]=="rising" else \
                    "#2ECC71" if vel["momentum"]=="falling" else "#F39C12"
        for col, val, lbl in [
            (c1, f"{vel['articles_per_day']}", "ARTIKEL/HARI"),
            (c2, str(vel["unique_sources"]),   "SUMBER UNIK"),
            (c3, {"rising":"↑ NAIK","falling":"↓ TURUN","stable":"→ STABIL"}.get(
                  vel["momentum"],"→"), "MOMENTUM"),
        ]:
            with col:
                st.markdown(f"""
                <div class="suite-card media">
                    <div class="metric-num" style="color:{mom_color}">{val}</div>
                    <div class="metric-label">{lbl}</div>
                </div>""", unsafe_allow_html=True)

        # Timeline volume per sumber
        df_ts = df_art.dropna(subset=["published_at"]).copy()
        if not df_ts.empty:
            df_ts["date"] = df_ts["published_at"].dt.date
            top_srcs = df_art["source"].value_counts().head(5).index.tolist()
            _pt = {**PLOT_THEME,
                   "plot_bgcolor":  "#070c06",
                   "paper_bgcolor": "#0a0e09",
                   "xaxis": dict(showgrid=True, gridcolor="#3d3515",
                                 tickfont=dict(color="rgba(255,255,255,0.4)")),
                   "yaxis": dict(showgrid=True, gridcolor="#3d3515",
                                 tickfont=dict(color="rgba(255,255,255,0.4)"))}

            fig_vel = go.Figure()
            for i, src in enumerate(top_srcs):
                df_src = df_ts[df_ts["source"]==src].groupby("date").size().reset_index(name="count")
                fig_vel.add_trace(go.Scatter(
                    x=df_src["date"], y=df_src["count"],
                    name=src[:25],
                    mode="lines+markers",
                    line=dict(width=2,
                              color=NARR_COLORS[i % len(NARR_COLORS)]),
                    marker=dict(size=6),
                ))
            fig_vel.update_layout(**_pt, height=300,
                title=dict(text="Volume Artikel per Sumber per Hari",
                           font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0),
                hovermode="x unified",
                legend=dict(font=dict(size=10, color="rgba(255,255,255,0.5)"),
                            orientation="h", y=-0.25),
            )
            st.plotly_chart(fig_vel, use_container_width=True)

        # Bar sumber
        src_counts = df_art["source"].value_counts().head(15)
        src_threat  = df_art.groupby("source")["threat_score"].mean()
        fig_src = go.Figure(go.Bar(
            x=src_counts.values,
            y=src_counts.index,
            orientation="h",
            marker_color=[get_threat_color(src_threat.get(s,0))
                          for s in src_counts.index],
            marker_opacity=0.8,
            hovertemplate="%{y}: %{x} artikel<extra></extra>",
        ))
        _pt2 = {k:v for k,v in _pt.items()}
        fig_src.update_layout(**_pt2,
            height=max(200, len(src_counts)*35),
            title=dict(text="Sumber Paling Aktif (warna = threat level)",
                       font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0))
        st.plotly_chart(fig_src, use_container_width=True)

    # ── TAB 4: SOURCE NETWORK ─────────────────────────────────────────────────
    with tab4:
        st.markdown('<div class="sec-title media">&#9661; JARINGAN SUMBER MEDIA</div>',
                    unsafe_allow_html=True)
        G = _source_network(df_art)
        if G is None or len(G.nodes()) < 2:
            st.info("Tidak cukup data untuk membangun network sumber. Perlu lebih banyak artikel.")
        else:
            pos_g = nx.spring_layout(G, k=2.0, seed=42)
            edge_tr = []
            for e in G.edges(data=True):
                x0,y0=pos_g[e[0]]; x1,y1=pos_g[e[1]]
                w = e[2].get("weight",1)
                edge_tr.append(go.Scatter(
                    x=[x0,x1,None], y=[y0,y1,None], mode="lines",
                    line=dict(width=min(w*.3+.5,4),
                              color="rgba(243,156,18,0.25)"),
                    hoverinfo="none", showlegend=False,
                ))
            nc_x,nc_y,nc_s,nc_t = [],[],[],[]
            for nd in G.nodes():
                ct = G.nodes[nd].get("count",1)
                nc_x.append(pos_g[nd][0])
                nc_y.append(pos_g[nd][1])
                nc_s.append(min(10+ct*4, 50))
                nc_t.append(f"<b>{nd}</b><br>{ct} artikel")
            node_tr = go.Scatter(
                x=nc_x, y=nc_y, mode="markers+text",
                text=[nd[:20]+"…" if len(nd)>20 else nd for nd in G.nodes()],
                textposition="top center",
                textfont=dict(size=9, color="rgba(255,255,255,0.7)",
                              family="DM Mono"),
                hovertext=nc_t, hoverinfo="text",
                marker=dict(color="#F39C12", size=nc_s, opacity=0.8,
                            line=dict(color="rgba(255,255,255,0.2)", width=1)),
                showlegend=False,
            )
            _pt3 = {k:v for k,v in PLOT_THEME.items() if k not in ["xaxis","yaxis"]}
            _pt3["plot_bgcolor"]  = "#070c06"
            _pt3["paper_bgcolor"] = "#0a0e09"
            fig_net = go.Figure(data=edge_tr+[node_tr])
            fig_net.update_layout(**_pt3, height=480,
                title=dict(text=f"Source Network — {monitor_kw}",
                           font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0),
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                hovermode="closest",
            )
            st.plotly_chart(fig_net, use_container_width=True)

    # ── TAB 5: LAPORAN ────────────────────────────────────────────────────────
    with tab5:
        now_rpt   = datetime.now().strftime("%d %B %Y %H:%M")
        top_src_5 = df_art["source"].value_counts().head(5)
        top3_art  = df_art.nlargest(3,"threat_score")

        narr_lines = "\n".join(
            f"   {t['id']}. {t['label']:<25} — {', '.join(t['keywords'][:4])} ({t['count']} artikel)"
            for t in clusters
        ) if clusters else "   Belum ada narasi teridentifikasi"

        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║        LAPORAN MEDIA & NARRATIVE INTELLIGENCE (D)               ║
╚══════════════════════════════════════════════════════════════════╝

NOMOR  : MEDIA-{monitor_id:04d}-{datetime.now().strftime('%Y%m%d')}
TANGGAL: {now_rpt}
KEYWORD: {monitor_kw}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. RINGKASAN
   Total Artikel   : {n}
   Sumber Unik     : {n_src}
   Narasi Aktif    : {len(clusters)}
   Artikel/Hari    : {vel['articles_per_day']}
   Momentum        : {vel['momentum'].upper()}
   Peak Hari       : {vel['peak_day']}

2. NARASI YANG TERIDENTIFIKASI
{narr_lines}

3. SUMBER PALING AKTIF
{chr(10).join(f"   {i+1}. {src} — {cnt} artikel" for i,(src,cnt) in enumerate(top_src_5.items()))}

4. ARTIKEL PERLU PERHATIAN
{chr(10).join(f"   [{r['source']}] {str(r['title'])[:65]}... (THREAT:{r['threat_score']:.0f})" for _,r in top3_art.iterrows())}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[AKHIR LAPORAN D] — OSINT Intelligence Suite v1.0
"""
        st.markdown(f'<div class="report-box">{report}</div>',
                    unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            st.download_button("⬇ Download (.txt)", data=report,
                file_name=f"media_{monitor_kw.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain")
        with c2:
            csv = df_art[["title","source","published_at","threat_score","url"]].to_csv(index=False)
            st.download_button("⬇ Export (.csv)", data=csv,
                file_name=f"media_data_{monitor_kw.replace(' ','_')}.csv",
                mime="text/csv")
