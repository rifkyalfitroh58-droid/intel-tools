"""
OSINT Intelligence Suite — person_intel.py
Modul A: Person & Entity Intelligence
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import networkx as nx
import sys, os, re
from datetime import datetime
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core.config import ENTITY_COLORS, ENTITY_LABELS, PLOT_THEME, MODULE_COLORS
from core.database import (load_articles, load_entities, load_relations,
                            get_global_stats)
from core.analyzer import (compute_risk_score, get_risk_color, get_risk_label,
                            get_threat_color, cluster_narratives)
from core.styles import BASE_CSS, module_css
from components.header import render_header
from components.article_card import render_article_card, render_link_panel


def _hex_rgb(h):
    h = h.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


def render_person_intel(monitor_id: int, monitor_kw: str):
    st.markdown(BASE_CSS + module_css("person"), unsafe_allow_html=True)
    render_header("person", monitor_kw,
                  unread_alerts=get_global_stats().get("unread_alerts", 0))

    if not monitor_id:
        st.info("👈 Tambah keyword di sidebar untuk mulai analisis.")
        return

    # Load data
    df_art = load_articles(monitor_id)
    df_ent = load_entities(monitor_id)
    df_rel = load_relations(monitor_id)

    if df_art.empty:
        st.warning("Belum ada data. Coba update di sidebar.")
        return

    # Metrics
    rs     = compute_risk_score(df_art)
    n      = len(df_art)
    pos_n  = int((df_art["sentiment"] > 0.05).sum())
    neg_n  = int((df_art["sentiment"] < -0.05).sum())
    n_src  = int(df_art["source"].nunique())
    n_ent  = len(df_ent)
    avg_s  = float(df_art["sentiment"].mean())
    risk_sc= rs["total"]

    tab1, tab2, tab3, tab4 = st.tabs([
        "👤 OVERVIEW", "📊 SENTIMEN", "🕸 ENTITAS", "📋 LAPORAN"
    ])

    # ── TAB 1: OVERVIEW ───────────────────────────────────────────────────────
    with tab1:
        c1,c2,c3,c4,c5 = st.columns(5)
        for col, val, lbl, color in [
            (c1, str(n),              "ARTIKEL",    "#4FC3F7"),
            (c2, str(n_src),          "SUMBER",     "#4FC3F7"),
            (c3, str(n_ent),          "ENTITAS",    "#9B59B6"),
            (c4, str(int(risk_sc)),   "RISK SCORE", get_risk_color(risk_sc)),
            (c5, str(round(avg_s,3)), "SENTIMEN",   "#2ECC71" if avg_s > 0 else "#E74C3C"),
        ]:
            with col:
                st.markdown(
                    '<div class="suite-card person">'
                    '<div class="metric-num" style="color:' + color + '">' + val + '</div>'
                    '<div class="metric-label">' + lbl + '</div>'
                    '</div>',
                    unsafe_allow_html=True
                )

        st.markdown('<hr style="border-color:#1E3A5F;margin:.8rem 0">', unsafe_allow_html=True)
        col_g, col_t = st.columns([1,2])

        with col_g:
            st.markdown('<div class="sec-title person">&#9661; RISK ASSESSMENT</div>',
                        unsafe_allow_html=True)
            rc = get_risk_color(risk_sc)
            fig_g = go.Figure(go.Indicator(
                mode="gauge+number", value=risk_sc,
                gauge=dict(
                    axis=dict(range=[0,100],
                              tickfont=dict(color="rgba(255,255,255,0.3)", size=9)),
                    bar=dict(color=rc, thickness=0.3),
                    bgcolor="#0A0F1E", bordercolor="#1E3A5F",
                    steps=[
                        dict(range=[0,40],   color="rgba(46,204,113,0.06)"),
                        dict(range=[40,70],  color="rgba(243,156,18,0.06)"),
                        dict(range=[70,100], color="rgba(231,76,60,0.08)"),
                    ],
                ),
                number=dict(font=dict(color=rc, size=34, family="DM Mono"),
                            suffix="/100"),
                title=dict(text=get_risk_label(risk_sc),
                           font=dict(color=rc, size=12, family="DM Mono")),
            ))
            _plot = {k:v for k,v in PLOT_THEME.items() if k not in ["xaxis","yaxis"]}
            fig_g.update_layout(**_plot, height=260)
            st.plotly_chart(fig_g, use_container_width=True)

            for lbl2, score2, mx2 in [
                ("Volume",    rs["volume"],    25),
                ("Sentimen-", rs["sentimen"],  30),
                ("Keragaman", rs["keragaman"], 20),
                ("Sensitif",  rs["sensitif"],  25),
            ]:
                pct = str(round(score2 / mx2 * 100 if mx2 > 0 else 0, 1))
                st.markdown(
                    '<div style="font-family:DM Mono,monospace;font-size:.68rem;'
                    'color:rgba(255,255,255,.5);margin-bottom:6px">'
                    + lbl2 + ' '
                    '<span style="float:right;color:rgba(255,255,255,.3)">'
                    + str(round(score2,1)) + "/" + str(mx2) + '</span>'
                    '<div style="background:#1E3A5F;border-radius:3px;height:4px;margin-top:4px;clear:both">'
                    '<div style="background:' + rc + ';height:4px;border-radius:3px;width:' + pct + '%"></div>'
                    '</div></div>',
                    unsafe_allow_html=True
                )

        with col_t:
            st.markdown('<div class="sec-title person">&#9661; TIMELINE PEMBERITAAN</div>',
                        unsafe_allow_html=True)
            df_ts = df_art.dropna(subset=["published_at"]).copy()
            if not df_ts.empty:
                df_ts["date"] = df_ts["published_at"].dt.date
                tl = df_ts.groupby("date").agg(
                    count=("id","count"),
                    avg_sent=("sentiment","mean"),
                ).reset_index()
                fig_tl = make_subplots(specs=[[{"secondary_y":True}]])
                fig_tl.add_trace(go.Bar(
                    x=tl["date"], y=tl["count"], name="Artikel",
                    marker_color="#4FC3F7", marker_opacity=0.7,
                ), secondary_y=False)
                fig_tl.add_trace(go.Scatter(
                    x=tl["date"], y=tl["avg_sent"], name="Sentimen",
                    line=dict(color="#2ECC71", width=2), mode="lines+markers",
                ), secondary_y=True)
                _plot2 = {k:v for k,v in PLOT_THEME.items()
                          if k not in ["xaxis","yaxis"]}
                fig_tl.update_layout(**_plot2, height=260,
                    title=dict(text="Volume &amp; Sentimen per Hari",
                               font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0),
                    xaxis=dict(showgrid=True, gridcolor="#1E3A5F"),
                    yaxis=dict(showgrid=True, gridcolor="#1E3A5F"),
                    yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                range=[-1,1]),
                    hovermode="x unified",
                    legend=dict(orientation="h", y=-0.25,
                                font=dict(size=10, color="rgba(255,255,255,0.4)")),
                )
                st.plotly_chart(fig_tl, use_container_width=True)

        # Artikel terbaru dengan badge
        st.markdown('<div class="sec-title person">&#9661; ARTIKEL TERBARU</div>',
                    unsafe_allow_html=True)
        for _idx, (_, row) in enumerate(df_art.head(6).iterrows()):
            render_article_card(row.to_dict(), "person", idx=_idx)

        # Panel keterhubungan
        if st.session_state.get("show_panel") and st.session_state.get("panel_article_id"):
            st.markdown('<div class="sec-title neutral">&#9661; PANEL KETERHUBUNGAN</div>',
                        unsafe_allow_html=True)
            render_link_panel(st.session_state["panel_article_id"])

        # Tombol lanjut
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚠ Lanjut ke Threat Intel →", use_container_width=True):
            st.session_state["page"]            = "threat"
            st.session_state["from_module"]     = "person"
            st.session_state["pending_keyword"] = monitor_kw
            st.rerun()

    # ── TAB 2: SENTIMEN ───────────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="sec-title person">&#9661; DISTRIBUSI SENTIMEN</div>',
                    unsafe_allow_html=True)
        neu_n = n - pos_n - neg_n
        c1,c2 = st.columns(2)
        with c1:
            fig_pie = go.Figure(go.Pie(
                labels=["Positif","Negatif","Netral"],
                values=[pos_n, neg_n, neu_n],
                marker_colors=["#2ECC71","#E74C3C","#4FC3F7"],
                hole=0.55,
                hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
            ))
            _plot_p = {k:v for k,v in PLOT_THEME.items() if k not in ["xaxis","yaxis"]}
            fig_pie.update_layout(**_plot_p, height=260,
                title=dict(text="Distribusi Sentimen",
                           font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0),
                showlegend=True,
                legend=dict(font=dict(size=10, color="rgba(255,255,255,0.4)"),
                            orientation="h", y=-0.1),
                annotations=[dict(text=f"<b>{n}</b><br>Artikel",
                                  x=0.5, y=0.5, font_size=13,
                                  font_color="#4FC3F7", showarrow=False)],
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with c2:
            cols_bar = ["#2ECC71" if s>0.05 else "#E74C3C" if s<-0.05 else "#4FC3F7"
                        for s in df_art["sentiment"]]
            fig_bar = go.Figure(go.Bar(
                x=list(range(len(df_art))), y=df_art["sentiment"],
                marker_color=cols_bar, marker_opacity=0.8,
            ))
            mean_s = float(df_art["sentiment"].mean())
            fig_bar.add_hline(y=0, line_color="rgba(255,255,255,0.2)",
                              line_dash="dash", line_width=1)
            fig_bar.add_hline(y=mean_s, line_color="#F39C12",
                              line_dash="dot", line_width=1.5,
                              annotation_text=f"Mean:{mean_s:.3f}",
                              annotation_font_color="#F39C12",
                              annotation_font_size=10)
            fig_bar.update_layout(**PLOT_THEME, height=260,
                title=dict(text="Sentimen per Artikel",
                           font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0))
            st.plotly_chart(fig_bar, use_container_width=True)

        # Sentimen per sumber
        src_sent = df_art.groupby("source").agg(
            avg_sent=("sentiment","mean"),
            count=("id","count"),
        ).sort_values("avg_sent").reset_index()
        if not src_sent.empty:
            cols_s = ["#E74C3C" if s<-0.05 else "#2ECC71" if s>0.05 else "#4FC3F7"
                      for s in src_sent["avg_sent"]]
            fig_src = go.Figure(go.Bar(
                x=src_sent["avg_sent"], y=src_sent["source"],
                orientation="h", marker_color=cols_s,
                text=[f"{v:.3f} ({c})" for v,c in
                      zip(src_sent["avg_sent"],src_sent["count"])],
                textfont=dict(size=10), textposition="outside",
            ))
            fig_src.add_vline(x=0, line_color="rgba(255,255,255,0.2)",
                              line_dash="dash", line_width=1)
            fig_src.update_layout(**PLOT_THEME,
                height=max(200, len(src_sent)*40),
                title=dict(text="Sentimen per Sumber",
                           font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0))
            st.plotly_chart(fig_src, use_container_width=True)

    # ── TAB 3: ENTITAS ────────────────────────────────────────────────────────
    with tab3:
        if df_ent.empty:
            st.markdown(
                '<div class="intel-box medium">Belum ada data entitas.</div>',
                unsafe_allow_html=True)
        else:
            c_ent, c_net = st.columns([1,2])
            with c_ent:
                st.markdown('<div class="sec-title person">&#9661; TOP ENTITAS</div>',
                            unsafe_allow_html=True)
                for lk, ln in ENTITY_LABELS.items():
                    ents = df_ent[df_ent["label"]==lk].head(6)
                    if ents.empty:
                        continue
                    color = ENTITY_COLORS.get(lk,"#888")
                    rgb   = _hex_rgb(color)
                    st.markdown(
                        f'<div style="font-family:DM Mono,monospace;font-size:.65rem;'
                        f'color:rgba(255,255,255,.35);text-transform:uppercase;margin:6px 0 3px">'
                        f'{ln}</div>',
                        unsafe_allow_html=True
                    )
                    tags = "".join([
                        f'<span style="display:inline-block;font-family:DM Mono,monospace;'
                        f'font-size:.68rem;background:rgba({rgb},.12);'
                        f'border:1px solid rgba({rgb},.3);color:{color};'
                        f'border-radius:3px;padding:2px 8px;margin:2px">'
                        f'{r["text"]} <span style="opacity:.5">x{r["count"]}</span></span>'
                        for _, r in ents.iterrows()
                    ])
                    st.markdown(f'<div>{tags}</div>', unsafe_allow_html=True)

            with c_net:
                st.markdown('<div class="sec-title person">&#9661; ENTITY NETWORK</div>',
                            unsafe_allow_html=True)
                if not df_rel.empty:
                    try:
                        G = nx.Graph()
                        ent_dict = {r["text"]:(r["label"],r["count"])
                                    for _,r in df_ent.iterrows()}
                        for _,r in df_rel.iterrows():
                            G.add_edge(r["entity_a"],r["entity_b"],
                                       weight=r["weight"])
                        pos_g = nx.spring_layout(G, k=1.8, seed=42)
                        edge_tr = []
                        for e in G.edges(data=True):
                            x0,y0=pos_g[e[0]]; x1,y1=pos_g[e[1]]
                            edge_tr.append(go.Scatter(
                                x=[x0,x1,None], y=[y0,y1,None],
                                mode="lines",
                                line=dict(width=min(e[2].get("weight",1)*.5+.5,4),
                                          color="rgba(79,195,247,.2)"),
                                hoverinfo="none", showlegend=False,
                            ))
                        nx_c,ny_c,nc_c,ns_c,nt_c = [],[],[],[],[]
                        for nd in G.nodes():
                            lb,ct = ent_dict.get(nd,("ORG",1))
                            nx_c.append(pos_g[nd][0])
                            ny_c.append(pos_g[nd][1])
                            nc_c.append(ENTITY_COLORS.get(lb,"#888"))
                            ns_c.append(min(10+ct*3,50))
                            nt_c.append(f"<b>{nd}</b><br>{lb} x{ct}")
                        node_tr = go.Scatter(
                            x=nx_c, y=ny_c, mode="markers+text",
                            text=[nd[:18]+"…" if len(nd)>18 else nd
                                  for nd in G.nodes()],
                            textposition="top center",
                            textfont=dict(size=9,
                                         color="rgba(255,255,255,0.7)",
                                         family="DM Mono"),
                            hovertext=nt_c, hoverinfo="text",
                            marker=dict(color=nc_c, size=ns_c,
                                        line=dict(color="rgba(255,255,255,0.2)",
                                                  width=1)),
                            showlegend=False,
                        )
                        fig_net = go.Figure(data=edge_tr+[node_tr])
                        _plot_n = {k:v for k,v in PLOT_THEME.items()
                                   if k not in ["xaxis","yaxis"]}
                        fig_net.update_layout(**_plot_n, height=480,
                            title=dict(text=f"Entity Network — {monitor_kw}",
                                       font=dict(size=12,
                                                 color="rgba(255,255,255,0.5)"), x=0),
                            xaxis=dict(showgrid=False, showticklabels=False,
                                       zeroline=False),
                            yaxis=dict(showgrid=False, showticklabels=False,
                                       zeroline=False),
                            hovermode="closest",
                        )
                        st.plotly_chart(fig_net, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Graph error: {e}")
                else:
                    st.info("Belum ada data relasi.")

    # ── TAB 4: LAPORAN ────────────────────────────────────────────────────────
    with tab4:
        now_rpt  = datetime.now().strftime("%d %B %Y %H:%M")
        persons  = df_ent[df_ent["label"]=="PERSON"]["text"].head(5).tolist() if not df_ent.empty else []
        orgs     = df_ent[df_ent["label"]=="ORG"]["text"].head(5).tolist()    if not df_ent.empty else []
        locs     = df_ent[df_ent["label"]=="GPE"]["text"].head(5).tolist()    if not df_ent.empty else []
        top_src  = df_art["source"].value_counts().head(5)
        top3     = df_art.nlargest(3,"threat_score")

        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║          LAPORAN PERSON & ENTITY INTELLIGENCE (A)               ║
╚══════════════════════════════════════════════════════════════════╝

NOMOR  : PERSON-{monitor_id:04d}-{datetime.now().strftime('%Y%m%d')}
TANGGAL: {now_rpt}
TARGET : {monitor_kw}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. RINGKASAN
   Total Artikel : {n} dari {n_src} sumber
   Risk Score    : {risk_sc:.1f}/100 — {get_risk_label(risk_sc)}
   Avg Sentimen  : {avg_s:.4f}

2. BREAKDOWN RISK
   Volume        : {rs['volume']:.1f}/25
   Sentimen-     : {rs['sentimen']:.1f}/30
   Keragaman     : {rs['keragaman']:.1f}/20
   Sensitif      : {rs['sensitif']:.1f}/25

3. SENTIMEN
   Positif: {pos_n} ({pos_n/n*100:.1f}%)
   Negatif: {neg_n} ({neg_n/n*100:.1f}%)

4. ENTITAS
   Individu  : {', '.join(persons) if persons else 'N/A'}
   Organisasi: {', '.join(orgs) if orgs else 'N/A'}
   Lokasi    : {', '.join(locs) if locs else 'N/A'}

5. SUMBER UTAMA
{chr(10).join(f"   {i+1}. {s} ({c})" for i,(s,c) in enumerate(top_src.items()))}

6. ARTIKEL PERLU PERHATIAN
{chr(10).join(f"   [{r['source']}] {str(r['title'])[:65]}..." for _,r in top3.iterrows())}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[AKHIR LAPORAN A] — OSINT Intelligence Suite v1.0
"""
        st.markdown(f'<div class="report-box">{report}</div>',
                    unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇ Download Laporan (.txt)", data=report,
                file_name=f"person_{monitor_kw.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
            )
        with c2:
            csv = df_art[["title","source","published_at","sentiment",
                           "threat_score","url"]].to_csv(index=False)
            st.download_button(
                "⬇ Export Data (.csv)", data=csv,
                file_name=f"person_data_{monitor_kw.replace(' ','_')}.csv",
                mime="text/csv",
            )
