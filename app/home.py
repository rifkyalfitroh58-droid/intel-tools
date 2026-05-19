"""
OSINT Intelligence Suite — home.py
Halaman utama: 4 kartu modul + status sistem + workflow guide
"""
import streamlit as st
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core.config import MODULE_COLORS, MODULE_LABELS, MODULE_ICONS
from core.database import get_global_stats, count_unread_alerts, get_monitors
from core.styles import _hex_to_rgb


def render_home():
    stats  = get_global_stats()
    unread = count_unread_alerts()
    mod_s  = stats.get("modules", {})

    # ── Hero section ──────────────────────────────────────────────────────────
    st.markdown("""
    <div style="text-align:center;padding:2rem 0 1rem">
        <div style="font-family:'DM Mono',monospace;font-size:2rem;
                    font-weight:500;color:#9B59B6;letter-spacing:.08em">
            &#9670; OSINT INTELLIGENCE SUITE
        </div>
        <div style="font-family:'DM Mono',monospace;font-size:.8rem;
                    color:rgba(155,89,182,.5);letter-spacing:.15em;
                    text-transform:uppercase;margin-top:8px">
            Sistem Intelijen Sumber Terbuka Terpadu v1.0
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Global metrics ────────────────────────────────────────────────────────
    c1,c2,c3,c4 = st.columns(4)
    for col, val, lbl, color, cc in [
        (c1, str(stats.get("total",0)),    "TOTAL ARTIKEL",  "#9B59B6", "rgba(155,89,182,.15)"),
        (c2, str(stats.get("links",0)),    "ARTIKEL TERHUBUNG","#4FC3F7","rgba(79,195,247,.15)"),
        (c3, str(stats.get("monitors",0)), "MONITOR AKTIF",  "#2ECC71", "rgba(46,204,113,.15)"),
        (c4, str(unread),                  "ALERT BELUM DIBACA","#E74C3C","rgba(231,76,60,.15)"),
    ]:
        with col:
            rgb = _hex_to_rgb(color)
            st.markdown(f"""
            <div style="background:{cc};border:1px solid rgba({rgb},.3);
                        border-radius:10px;padding:1rem;text-align:center">
                <div style="font-family:'DM Mono',monospace;font-size:1.8rem;
                            color:{color};font-weight:500">{val}</div>
                <div style="font-size:.7rem;color:rgba(255,255,255,.4);
                            margin-top:4px;letter-spacing:.06em">{lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 4 Module cards ────────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:.75rem;
                color:rgba(255,255,255,.4);letter-spacing:.12em;
                text-transform:uppercase;text-align:center;margin-bottom:1rem">
        PILIH MODUL ANALISIS
    </div>
    """, unsafe_allow_html=True)

    modules_info = [
        ("person", "Person &amp; Entity Intel",
         "Kumpulkan dan analisis informasi publik tentang individu atau organisasi dari berbagai sumber terbuka.",
         ["Profil lengkap target","Analisis sentimen media","Peta entitas & jaringan","Risk score 0-100"]),
        ("threat", "Threat &amp; Disinformation Intel",
         "Monitor dan deteksi narasi ancaman, hoaks, atau disinformasi yang menyebar di ruang publik digital.",
         ["Hoax detector","Hate speech classifier","Spread rate tracker","Alert otomatis"]),
        ("geo", "Geospatial Intel",
         "Analisis data lokasi publik — peta kejadian, persebaran insiden, heatmap wilayah dari data terbuka.",
         ["Peta interaktif Indonesia","Heatmap 34 provinsi","Hotspot insiden","Timeline geospasial"]),
        ("media", "Media &amp; Narrative Intel",
         "Lacak bagaimana isu berkembang di media online — siapa yang memulai, ke mana menyebar, seberapa cepat.",
         ["Klaster narasi","Network media","Timeline isu","Sumber dominan"]),
    ]

    col_left, col_right = st.columns(2)
    for idx, (mod, title, desc, features) in enumerate(modules_info):
        color = MODULE_COLORS[mod]
        icon  = MODULE_ICONS[mod]
        rgb   = _hex_to_rgb(color)
        n_art = mod_s.get(mod, 0)
        n_mon = len(get_monitors(mod))

        with (col_left if idx % 2 == 0 else col_right):
            st.markdown(f"""
            <div style="background:#0D1B2A;border:1px solid rgba({rgb},.3);
                        border-radius:12px;padding:1.2rem 1.4rem;margin-bottom:12px;
                        border-left:3px solid {color}">
                <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                        <div style="font-size:1.2rem;margin-bottom:4px">{icon}</div>
                        <div style="font-family:'DM Mono',monospace;font-size:.85rem;
                                    font-weight:500;color:{color}">{title}</div>
                    </div>
                    <div style="text-align:right;font-family:'DM Mono',monospace;font-size:.7rem;
                                color:rgba(255,255,255,.35)">
                        {n_art} artikel<br>{n_mon} monitor
                    </div>
                </div>
                <div style="font-size:.82rem;color:rgba(255,255,255,.55);
                            margin:8px 0;line-height:1.5">{desc}</div>
                <div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:8px">
                    {"".join(f'<span style="font-family:DM Mono,monospace;font-size:.65rem;background:rgba({rgb},.1);border:1px solid rgba({rgb},.25);color:{color};border-radius:3px;padding:1px 7px">{f}</span>' for f in features)}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"{icon} Buka {MODULE_LABELS[mod]}",
                         key=f"open_{mod}", use_container_width=True):
                st.session_state["page"]       = mod
                st.session_state["from_module"] = "home"
                st.rerun()

    # ── Workflow guide ────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'DM Mono',monospace;font-size:.75rem;
                color:rgba(255,255,255,.4);letter-spacing:.12em;
                text-transform:uppercase;text-align:center;margin-bottom:1rem">
        ALUR INVESTIGASI YANG DISARANKAN
    </div>
    <div style="display:flex;align-items:center;justify-content:center;
                gap:8px;flex-wrap:wrap;padding:.5rem 0">
        <div style="background:rgba(79,195,247,.1);border:1px solid rgba(79,195,247,.3);
                    border-radius:8px;padding:.6rem 1rem;text-align:center">
            <div style="font-size:1.2rem">👤</div>
            <div style="font-family:'DM Mono',monospace;font-size:.7rem;color:#4FC3F7">A. Profil Target</div>
            <div style="font-size:.68rem;color:rgba(255,255,255,.4)">Siapa targetnya?</div>
        </div>
        <div style="color:rgba(255,255,255,.3);font-size:1.2rem">&#8250;</div>
        <div style="background:rgba(231,76,60,.1);border:1px solid rgba(231,76,60,.3);
                    border-radius:8px;padding:.6rem 1rem;text-align:center">
            <div style="font-size:1.2rem">⚠</div>
            <div style="font-family:'DM Mono',monospace;font-size:.7rem;color:#E74C3C">B. Ancaman</div>
            <div style="font-size:.68rem;color:rgba(255,255,255,.4)">Ada hoaks/ancaman?</div>
        </div>
        <div style="color:rgba(255,255,255,.3);font-size:1.2rem">&#8250;</div>
        <div style="background:rgba(46,204,113,.1);border:1px solid rgba(46,204,113,.3);
                    border-radius:8px;padding:.6rem 1rem;text-align:center">
            <div style="font-size:1.2rem">🗺</div>
            <div style="font-family:'DM Mono',monospace;font-size:.7rem;color:#2ECC71">C. Lokasi</div>
            <div style="font-size:.68rem;color:rgba(255,255,255,.4)">Di mana terjadi?</div>
        </div>
        <div style="color:rgba(255,255,255,.3);font-size:1.2rem">&#8250;</div>
        <div style="background:rgba(243,156,18,.1);border:1px solid rgba(243,156,18,.3);
                    border-radius:8px;padding:.6rem 1rem;text-align:center">
            <div style="font-size:1.2rem">📰</div>
            <div style="font-family:'DM Mono',monospace;font-size:.7rem;color:#F39C12">D. Narasi</div>
            <div style="font-size:.68rem;color:rgba(255,255,255,.4)">Bagaimana menyebar?</div>
        </div>
        <div style="color:rgba(255,255,255,.3);font-size:1.2rem">&#8250;</div>
        <div style="background:rgba(155,89,182,.1);border:1px solid rgba(155,89,182,.3);
                    border-radius:8px;padding:.6rem 1rem;text-align:center">
            <div style="font-size:1.2rem">📋</div>
            <div style="font-family:'DM Mono',monospace;font-size:.7rem;color:#9B59B6">Laporan</div>
            <div style="font-size:.68rem;color:rgba(255,255,255,.4)">Unified report</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
