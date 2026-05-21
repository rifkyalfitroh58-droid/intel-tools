"""
OSINT Intelligence Suite — sidebar.py
Sidebar global dengan navigasi modul + keyword input
"""
import streamlit as st
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from core.config import MODULE_COLORS, MODULE_LABELS, MODULE_ICONS
from core.database import (get_monitors, add_monitor, delete_monitor,
                            count_unread_alerts, get_global_stats)
from core.fetcher import fetch_articles
from core.linker import build_links



def _hex_rgb(h: str) -> str:
    h = h.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


def _clear_cache():
    for key in list(st.session_state.keys()):
        if key.startswith("cache_"):
            del st.session_state[key]


def render_sidebar(current_module: str):
    """
    Render sidebar global — navigasi modul + keyword input + quick stats.
    Return: (monitor_id, keyword) untuk modul aktif.
    """
    monitor_id  = None
    monitor_kw  = None

    with st.sidebar:
        # ── Logo ──────────────────────────────────────────────────────────────
        st.markdown("""
        <div style="padding:.8rem 0 .4rem">
            <div style="font-family:'DM Mono',monospace;font-size:1rem;
                        font-weight:500;color:#9B59B6;letter-spacing:.1em">
                &#9670; OSINT SUITE
            </div>
            <div style="font-family:'DM Mono',monospace;font-size:.62rem;
                        color:rgba(155,89,182,.4);letter-spacing:.12em;
                        text-transform:uppercase;margin-top:2px">
                Intelligence Operations Center
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        # ── Navigasi modul ────────────────────────────────────────────────────
        st.markdown(
            '<div style="font-family:DM Mono;font-size:.62rem;color:rgba(155,89,182,.5);'
            'letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px">&#9670; MODUL</div>',
            unsafe_allow_html=True
        )

        nav_items = [
            ("home",   "&#127968; Beranda",         "#9B59B6"),
            ("person", "&#128100; Person Intel",     "#4FC3F7"),
            ("threat", "&#9888; Threat Intel",       "#E74C3C"),
            ("geo",    "&#128506; Geo Intel",        "#2ECC71"),
            ("media",  "&#128240; Media Intel",      "#F39C12"),
        ]
        for mod, label, color in nav_items:
            is_active = current_module == mod
            bg = f"rgba({_hex_rgb(color)},.15)" if is_active else "transparent"
            border = f"1px solid rgba({_hex_rgb(color)},.4)" if is_active else "1px solid transparent"
            if st.button(
                label,
                key=f"nav_{mod}",
                use_container_width=True,
            ):
                st.session_state["page"]        = mod
                st.session_state["from_module"] = current_module if current_module != mod else ""
                st.session_state["show_panel"]  = False
                st.rerun()

        st.divider()

        # ── Keyword input untuk modul aktif ──────────────────────────────────
        if current_module not in ["home"]:
            color  = MODULE_COLORS.get(current_module, "#9B59B6")
            icon   = MODULE_ICONS.get(current_module, "◈")
            label  = MODULE_LABELS.get(current_module, "")

            rgb_c = _hex_rgb(color)
            st.markdown(
                '<div style="font-family:DM Mono;font-size:.62rem;'
                'color:rgba(' + rgb_c + ',.5);letter-spacing:.1em;'
                'text-transform:uppercase;margin-bottom:6px">'
                + icon + ' ' + label.upper() + '</div>',
                unsafe_allow_html=True
            )

            new_kw = st.text_input(
                "keyword",
                value=st.session_state.get("pending_keyword",""),
                placeholder="nama, topik, atau kejadian...",
                label_visibility="collapsed",
                key=f"kw_{current_module}",
            )
            col_fetch, col_n = st.columns([2,1])
            with col_fetch:
                fetch_btn = st.button("⬇ Ambil Data", use_container_width=True,
                                      key=f"fetch_{current_module}")
            with col_n:
                n_art = st.selectbox("n", [20,50,100],
                                     label_visibility="collapsed",
                                     key=f"n_{current_module}")

            if fetch_btn and new_kw.strip():
                with st.spinner(f"Mengambil & menganalisis: {new_kw}..."):
                    mid = add_monitor(current_module, new_kw.strip())
                    n_saved, err = fetch_articles(mid, current_module,
                                                  new_kw.strip(), n_art)
                if err:
                    st.error(f"❌ {err}")
                    delete_monitor(mid)
                else:
                    st.session_state["pending_keyword"] = ""
                    _clear_cache()
                    # Build links antar modul
                    with st.spinner("Membangun keterhubungan..."):
                        build_links()
                    st.success("✅ " + str(n_saved) + " artikel dari NewsAPI + GDELT + RSS Indonesia")
                    st.rerun()
            elif fetch_btn and not new_kw.strip():
                st.warning("Masukkan keyword dulu.")

            st.divider()

            # ── Pilih monitor aktif ───────────────────────────────────────────
            df_mon = get_monitors(current_module)
            if df_mon.empty:
                st.info("Belum ada data. Tambah keyword di atas.")
            else:
                st.markdown(
                    '<div style="font-family:DM Mono;font-size:.62rem;'
                    'color:rgba(255,255,255,.3);letter-spacing:.1em;'
                    'text-transform:uppercase;margin-bottom:4px">MONITOR AKTIF</div>',
                    unsafe_allow_html=True
                )
                opts = {f"{r['keyword']} (#{r['id']})": int(r['id'])
                        for _, r in df_mon.iterrows()}
                sel  = st.selectbox(
                    "Monitor pilihan",
                    list(opts.keys()),
                    label_visibility="collapsed",
                    key=f"sel_{current_module}",
                )
                monitor_id = opts[sel]
                monitor_kw = sel.split(" (#")[0]

                col_del, col_upd = st.columns(2)
                with col_del:
                    if st.button("🗑 Hapus", use_container_width=True,
                                 key=f"del_{current_module}"):
                        delete_monitor(monitor_id)
                        _clear_cache()
                        st.rerun()
                with col_upd:
                    if st.button("🔄 Update", use_container_width=True,
                                 key=f"upd_{current_module}"):
                        with st.spinner("Update..."):
                            n_s, err = fetch_articles(monitor_id, current_module,
                                                      monitor_kw, 50)
                        if err:
                            st.error(f"❌ {err}")
                        else:
                            _clear_cache()
                            with st.spinner("Rebuild links..."):
                                build_links()
                            st.success("✅ " + str(n_s) + " artikel baru (multi-source)")
                            st.rerun()

            st.divider()

        # ── Quick stats global ─────────────────────────────────────────────
        stats  = get_global_stats()
        unread = count_unread_alerts()
        mod_s  = stats.get("modules",{})

        _t = str(stats.get("total",0))
        _l = str(stats.get("links",0))
        _m = str(stats.get("monitors",0))
        _u = str(unread)
        _a = str(mod_s.get("person",0))
        _b = str(mod_s.get("threat",0))
        _c = str(mod_s.get("geo",0))
        _d = str(mod_s.get("media",0))
        st.markdown(
            '<div style="font-family:DM Mono,monospace;font-size:.62rem;'
            'color:rgba(155,89,182,.5);letter-spacing:.1em;'
            'text-transform:uppercase;margin-bottom:8px">STATS GLOBAL</div>'
            '<div style="background:#070d14;border:1px solid #1E3A5F;'
            'border-radius:8px;padding:.7rem .9rem">'
            '<table style="font-family:DM Mono,monospace;font-size:.68rem;'
            'color:rgba(255,255,255,.4);width:100%;border-collapse:collapse;line-height:1.9">'
            '<tr><td>ARTIKEL</td><td style="text-align:right">' + _t + '</td></tr>'
            '<tr><td>LINKS</td><td style="text-align:right">' + _l + '</td></tr>'
            '<tr><td>MONITOR</td><td style="text-align:right">' + _m + '</td></tr>'
            '<tr><td>ALERT</td><td style="text-align:right">'
            '<span style="color:#E74C3C">' + _u + '</span></td></tr>'
            '<tr><td colspan="2" style="padding-top:4px">'
            '<span style="color:#4FC3F7">A</span> ' + _a + '&nbsp;'
            '<span style="color:#E74C3C">B</span> ' + _b + '&nbsp;'
            '<span style="color:#2ECC71">C</span> ' + _c + '&nbsp;'
            '<span style="color:#F39C12">D</span> ' + _d
            + '</td></tr>'
            '</table></div>',
            unsafe_allow_html=True
        )

        st.divider()
        st.markdown("""
        <div style="font-family:'DM Mono',monospace;font-size:.6rem;
                    color:rgba(155,89,182,.2);line-height:2;letter-spacing:.06em">
            OSINT SUITE v1.0<br>
            A+B+C+D+LINKS<br>
            DATA: NewsAPI (Public)
        </div>
        """, unsafe_allow_html=True)

    return monitor_id, monitor_kw

