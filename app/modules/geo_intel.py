"""
OSINT Intelligence Suite — geo_intel.py
Modul C: Geospatial Intelligence
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core.config import INCIDENT_TYPES, PROVINCES, PLOT_THEME
from core.database import (load_articles, load_province_stats,
                            update_province_stats, get_global_stats)
from core.analyzer import get_sev_color, get_threat_color
from core.styles import BASE_CSS, module_css
from components.header import render_header
from components.article_card import render_article_card, render_link_panel


def _hex_rgb(h):
    h = h.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


def _get_sev_label(score: float) -> str:
    if score >= 75: return "🔴 KRITIS"
    if score >= 50: return "🟠 TINGGI"
    if score >= 25: return "🟡 SEDANG"
    return "🟢 RENDAH"


def render_geo_intel(monitor_id: int, monitor_kw: str):
    st.markdown(BASE_CSS + module_css("geo"), unsafe_allow_html=True)
    render_header("geo", monitor_kw,
                  unread_alerts=get_global_stats().get("unread_alerts", 0))

    if not monitor_id:
        st.info("👈 Tambah keyword di sidebar untuk mulai analisis.")
        return

    df_art = load_articles(monitor_id)

    if df_art.empty:
        st.warning("Belum ada data. Coba update di sidebar.")
        return

    # Filter artikel yang punya lokasi
    df_geo = df_art[
        (df_art["location"].notna()) &
        (df_art["location"] != "") &
        (df_art["lat"] != 0) &
        (df_art["lon"] != 0)
    ].copy()

    # Update province stats
    if not df_geo.empty:
        df_geo_s = df_geo.copy()
        df_geo_s["id"] = df_geo_s.index
        update_province_stats(monitor_id, df_geo_s)

    df_prov = load_province_stats(monitor_id)

    n       = len(df_art)
    n_geo   = len(df_geo)
    n_krit  = int((df_geo["severity"] >= 75).sum()) if not df_geo.empty else 0
    n_prov  = int(df_geo["province"].nunique()) if not df_geo.empty else 0
    avg_sev = float(df_geo["severity"].mean()) if not df_geo.empty else 0.0

    tab1, tab2, tab3, tab4 = st.tabs([
        "🗺 PETA INTERAKTIF", "🔥 HEATMAP PROVINSI", "📍 HOTSPOT", "📋 LAPORAN"
    ])

    # ── TAB 1: PETA INTERAKTIF ────────────────────────────────────────────────
    with tab1:
        c1,c2,c3,c4,c5 = st.columns(5)
        for col, val, lbl, color in [
            (c1, str(n),       "TOTAL ARTIKEL",   "#4FC3F7"),
            (c2, str(n_geo),   "ARTIKEL TERPETAKAN","#2ECC71"),
            (c3, str(n_krit),  "INSIDEN KRITIS",  "#E74C3C"),
            (c4, str(n_prov),  "PROVINSI",        "#F39C12"),
            (c5, f"{avg_sev:.0f}", "AVG SEVERITY", get_sev_color(avg_sev)),
        ]:
            with col:
                st.markdown(f"""
                <div class="suite-card geo">
                    <div class="metric-num" style="color:{color}">{val}</div>
                    <div class="metric-label">{lbl}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown('<hr style="border-color:#1a3d1a;margin:.8rem 0">',
                    unsafe_allow_html=True)

        if df_geo.empty:
            st.markdown(
                '<div class="intel-box medium">Tidak ada artikel dengan lokasi terdeteksi. '
                'Coba keyword yang lebih spesifik tentang lokasi Indonesia.</div>',
                unsafe_allow_html=True
            )
        else:
            # Filter
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                type_opts = ["Semua"] + list(INCIDENT_TYPES.keys())
                type_filter = st.selectbox(
                    "Tipe insiden", type_opts,
                    label_visibility="collapsed", key="geo_type"
                )
            with col_f2:
                sev_filter = st.slider("Min severity", 0, 100, 0, key="geo_sev")
            with col_f3:
                map_style = st.selectbox(
                    "Style peta",
                    ["carto-darkmatter","open-street-map","stamen-terrain"],
                    label_visibility="collapsed", key="geo_style"
                )

            df_map = df_geo.copy()
            if type_filter != "Semua":
                df_map = df_map[df_map["inc_type"] == type_filter]
            df_map = df_map[df_map["severity"] >= sev_filter]

            if df_map.empty:
                st.info("Tidak ada insiden yang sesuai filter.")
            else:
                fig_map = go.Figure()
                for inc_type, info in INCIDENT_TYPES.items():
                    subset = df_map[df_map["inc_type"] == inc_type]
                    if subset.empty:
                        continue
                    fig_map.add_trace(go.Scattermap(
                        lat=subset["lat"], lon=subset["lon"],
                        mode="markers",
                        marker=dict(
                            size=subset["severity"].apply(
                                lambda x: max(8, min(x/3, 30))
                            ),
                            color=info["color"],
                            opacity=0.8,
                        ),
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "Lokasi: %{customdata[1]}<br>"
                            "Severity: %{customdata[2]:.0f}/100<extra></extra>"
                        ),
                        customdata=subset[["title","location","severity"]].values,
                        name=f"{info['label']}",
                    ))

                fig_map.update_layout(
                    map=dict(style=map_style,
                             center=dict(lat=-2.5, lon=118.0), zoom=4),
                    paper_bgcolor="#0a0d0a",
                    height=500,
                    margin=dict(l=0, r=0, t=0, b=0),
                    legend=dict(
                        bgcolor="rgba(10,13,10,0.8)",
                        bordercolor="#1a3d1a", borderwidth=1,
                        font=dict(color="rgba(255,255,255,0.6)", size=10),
                    ),
                )
                st.plotly_chart(fig_map, use_container_width=True)
                st.markdown(
                    f'<div style="font-family:DM Mono;font-size:.7rem;'
                    f'color:rgba(255,255,255,.3);text-align:center">'
                    f'{len(df_map)} insiden ditampilkan</div>',
                    unsafe_allow_html=True
                )

        # Tombol lanjut
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("← Kembali ke Threat Intel", use_container_width=True):
                st.session_state["page"] = "threat"
                st.session_state["from_module"] = "geo"
                st.rerun()
        with c2:
            if st.button("📰 Lanjut ke Media Intel →", use_container_width=True):
                st.session_state["page"] = "media"
                st.session_state["from_module"] = "geo"
                st.session_state["pending_keyword"] = monitor_kw
                st.rerun()

    # ── TAB 2: HEATMAP PROVINSI ───────────────────────────────────────────────
    with tab2:
        if df_prov.empty:
            st.info("Belum ada data statistik provinsi.")
        else:
            df_prov_s = df_prov.sort_values("count", ascending=True).tail(20)
            colors_p  = [get_sev_color(s) for s in df_prov_s["avg_risk"]]

            fig_prov = go.Figure(go.Bar(
                x=df_prov_s["count"], y=df_prov_s["province"],
                orientation="h", marker_color=colors_p,
                text=[f"{c} ({s:.0f})" for c,s in
                      zip(df_prov_s["count"],
                          df_prov_s["avg_risk"])],
                textfont=dict(size=10), textposition="outside",
            ))
            _pt = {**PLOT_THEME,
                   "plot_bgcolor":"#070a07",
                   "paper_bgcolor":"#0a0d0a"}
            _pt["xaxis"] = dict(showgrid=True, gridcolor="#1a3d1a",
                                tickfont=dict(color="rgba(255,255,255,0.4)"))
            _pt["yaxis"] = dict(showgrid=False,
                                tickfont=dict(color="rgba(255,255,255,0.6)"))
            fig_prov.update_layout(**_pt,
                height=max(300, len(df_prov_s)*35),
                title=dict(text="Insiden per Provinsi",
                           font=dict(size=12, color="rgba(255,255,255,0.5)"), x=0))
            st.plotly_chart(fig_prov, use_container_width=True)

            # Bubble map
            prov_coords = []
            for _, row in df_prov.iterrows():
                if row["province"] in PROVINCES:
                    coord = PROVINCES[row["province"]]
                    prov_coords.append({
                        "province": row["province"],
                        "lat":      coord["lat"],
                        "lon":      coord["lon"],
                        "count":    row["count"],
                        "avg_sev":  row["avg_risk"],
                    })

            if prov_coords:
                df_bc = pd.DataFrame(prov_coords)
                fig_bc = go.Figure(go.Scattermap(
                    lat=df_bc["lat"], lon=df_bc["lon"],
                    mode="markers+text",
                    marker=dict(
                        size=df_bc["count"].apply(lambda x: min(10+x*5,50)),
                        color=df_bc["avg_sev"].apply(get_sev_color),
                        opacity=0.7,
                    ),
                    text=df_bc["province"].apply(lambda x: x[:10]),
                    textfont=dict(size=8, color="white"),
                    hovertemplate=(
                        "<b>%{text}</b><br>"
                        "Insiden: %{customdata[0]}<br>"
                        "Avg Sev: %{customdata[1]:.0f}<extra></extra>"
                    ),
                    customdata=df_bc[["count","avg_sev"]].values,
                ))
                fig_bc.update_layout(
                    map=dict(style="carto-darkmatter",
                             center=dict(lat=-2.5, lon=118.0), zoom=3.5),
                    paper_bgcolor="#0a0d0a",
                    height=460,
                    margin=dict(l=0,r=0,t=0,b=0),
                )
                st.plotly_chart(fig_bc, use_container_width=True)

            # Tabel
            df_prov_d = df_prov.copy()
            df_prov_d["Level"] = df_prov_d["avg_risk"].apply(_get_sev_label)
            df_prov_d["Tipe"]  = "—"  # dominant_type tidak tersimpan di province_stats
            st.dataframe(
                df_prov_d[["province","count","avg_risk","Level"]]
                .rename(columns={"province":"Provinsi","count":"Insiden",
                                 "avg_risk":"Avg Severity"})
                .sort_values("Insiden", ascending=False),
                use_container_width=True, hide_index=True,
            )

    # ── TAB 3: HOTSPOT ────────────────────────────────────────────────────────
    with tab3:
        if df_geo.empty:
            st.info("Tidak ada data lokasi.")
        else:
            hotspots = df_geo.groupby(["location","province","lat","lon"]).agg(
                count=("id","count"),
                avg_sev=("severity","mean"),
            ).reset_index().sort_values("count", ascending=False)

            col_hs, col_hmap = st.columns([1,2])
            with col_hs:
                st.markdown('<div class="sec-title geo">&#9661; TOP HOTSPOT</div>',
                            unsafe_allow_html=True)
                for _, row in hotspots.head(10).iterrows():
                    sc    = row["avg_sev"]
                    color = get_sev_color(sc)
                    st.markdown(f"""
                    <div style="background:#0a0d0a;border:1px solid #1a3d1a;
                                border-radius:8px;padding:.6rem .9rem;
                                margin-bottom:5px;display:flex;
                                align-items:center;gap:10px">
                        <div style="width:34px;height:34px;border-radius:50%;
                                    background:{color}22;border:2px solid {color};
                                    display:flex;align-items:center;
                                    justify-content:center;font-size:.9rem;
                                    flex-shrink:0">📍</div>
                        <div style="flex:1">
                            <div style="font-weight:500;font-size:.82rem">
                                {row['location']}</div>
                            <div style="font-family:'DM Mono',monospace;
                                        font-size:.68rem;color:rgba(255,255,255,.4)">
                                {row['province']} · {row['count']} insiden ·
                                <span style="color:{color}">SEV:{sc:.0f}</span>
                            </div>
                        </div>
                    </div>""", unsafe_allow_html=True)

            with col_hmap:
                fig_hs = go.Figure(go.Scattermap(
                    lat=hotspots["lat"], lon=hotspots["lon"],
                    mode="markers",
                    marker=dict(
                        size=hotspots["count"].apply(lambda x: min(10+x*8,60)),
                        color=hotspots["avg_sev"].apply(get_sev_color),
                        opacity=0.75,
                    ),
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Insiden: %{customdata[1]}<br>"
                        "Avg Sev: %{customdata[2]:.0f}<extra></extra>"
                    ),
                    customdata=hotspots[["location","count","avg_sev"]].values,
                ))
                fig_hs.update_layout(
                    map=dict(style="carto-darkmatter",
                             center=dict(lat=-2.5, lon=118.0), zoom=4),
                    paper_bgcolor="#0a0d0a",
                    height=400,
                    margin=dict(l=0,r=0,t=0,b=0),
                )
                st.plotly_chart(fig_hs, use_container_width=True)

        # Artikel terbaru dengan lokasi + badge
        st.markdown('<div class="sec-title geo">&#9661; INSIDEN TERBARU</div>',
                    unsafe_allow_html=True)
        df_show = df_geo.head(8) if not df_geo.empty else df_art.head(6)
        for _idx, (_, row) in enumerate(df_show.iterrows()):
            render_article_card(row.to_dict(), "geo", idx=_idx)

        if st.session_state.get("show_panel") and st.session_state.get("panel_article_id"):
            render_link_panel(st.session_state["panel_article_id"])

    # ── TAB 4: LAPORAN ────────────────────────────────────────────────────────
    with tab4:
        now_rpt  = datetime.now().strftime("%d %B %Y %H:%M")
        top3_inc = df_geo.nlargest(3,"severity") if not df_geo.empty else df_art.head(3)
        top5_prov= df_prov.nlargest(5,"count") if not df_prov.empty else pd.DataFrame()
        type_bd  = df_geo["inc_type"].value_counts() if not df_geo.empty else pd.Series()
        type_lines = "\n".join(
            f"   {INCIDENT_TYPES.get(k,{}).get('label',k):<25}: {v}"
            for k,v in type_bd.items()
        ) if not type_bd.empty else "   Tidak ada data"

        prov_lines = "\n".join(
            f"   {i+1}. {row['province']:<30}: {row['count']} insiden"
            for i,(_,row) in enumerate(top5_prov.iterrows())
        ) if not top5_prov.empty else "   Tidak ada data"

        report = f"""
╔══════════════════════════════════════════════════════════════════╗
║         LAPORAN GEOSPATIAL INTELLIGENCE (C)                     ║
╚══════════════════════════════════════════════════════════════════╝

NOMOR  : GEOINT-{monitor_id:04d}-{datetime.now().strftime('%Y%m%d')}
TANGGAL: {now_rpt}
KEYWORD: {monitor_kw}
CAKUPAN: Indonesia (34 Provinsi)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. RINGKASAN
   Total Artikel     : {n}
   Artikel Terpetakan: {n_geo}
   Insiden Kritis    : {n_krit}
   Provinsi Terdampak: {n_prov}
   Avg Severity      : {avg_sev:.1f}/100

2. TIPE INSIDEN
{type_lines}

3. PROVINSI PALING TERDAMPAK
{prov_lines}

4. INSIDEN PALING KRITIS
{chr(10).join(f"   [{r['source']}] {str(r['title'])[:65]}... (SEV:{r['severity']:.0f})" for _,r in top3_inc.iterrows())}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[AKHIR LAPORAN C] — OSINT Intelligence Suite v1.0
"""
        st.markdown(f'<div class="report-box">{report}</div>',
                    unsafe_allow_html=True)
        c1,c2 = st.columns(2)
        with c1:
            st.download_button("⬇ Download (.txt)", data=report,
                file_name=f"geo_{monitor_kw.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain")
        with c2:
            csv = df_geo[["title","source","published_at","location","province",
                           "lat","lon","inc_type","severity","url"]].to_csv(index=False) \
                  if not df_geo.empty else df_art.head(0).to_csv(index=False)
            st.download_button("⬇ Export (.csv)", data=csv,
                file_name=f"geo_data_{monitor_kw.replace(' ','_')}.csv",
                mime="text/csv")
