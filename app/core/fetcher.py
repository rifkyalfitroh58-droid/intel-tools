"""
OSINT Intelligence Suite — fetcher.py
Multi-source fetcher: NewsAPI + GDELT + RSS Indonesia + BMKG
"""
import requests
import sys, os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import NEWS_API_KEY
from analyzer import (analyze_article, extract_entities_rule_based,
                      cluster_narratives)
from database import (save_articles, save_entities, save_relations,
                      save_narratives, save_alert, update_province_stats,
                      load_articles)
import pandas as pd


# ── RSS feeds media Indonesia ─────────────────────────────────────────────────
RSS_FEEDS = {
    "Kompas":       "https://rss.kompas.com/rss/xml/nasional",
    "Kompas Bisnis":"https://rss.kompas.com/rss/xml/money",
    "Detik":        "https://www.detik.com/rss",
    "Detik News":   "https://feed.detik.com/feed/detikcom/ns:detikcom/category:News",
    "Tempo":        "https://rss.tempo.co/nasional",
    "Tempo Bisnis": "https://rss.tempo.co/bisnis",
    "CNN Indonesia":"https://www.cnnindonesia.com/rss",
    "Republika":    "https://www.republika.co.id/rss",
    "Antara":       "https://www.antaranews.com/rss/terkini.xml",
    "Antara Politik":"https://www.antaranews.com/rss/politik.xml",
    "Antara Hukum": "https://www.antaranews.com/rss/hukum.xml",
    "Tribun":       "https://www.tribunnews.com/rss",
    "Okezone":      "https://sindikasi.okezone.com/index.php/rss/0/XML",
    "Liputan6":     "https://www.liputan6.com/rss",
    "Medcom":       "https://www.medcom.id/rss",
}

# ── BMKG endpoint ─────────────────────────────────────────────────────────────
BMKG_ENDPOINTS = {
    "gempa_terkini":  "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json",
    "gempa_m5plus":   "https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json",
    "gempa_dirasakan":"https://data.bmkg.go.id/DataMKG/TEWS/gempadirasakan.json",
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/xml, application/xml, */*",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}


# ── Source 1: NewsAPI ─────────────────────────────────────────────────────────
def _fetch_newsapi(keyword: str, module: str, page_size: int = 30) -> list:
    """Fetch dari NewsAPI. Return list artikel raw."""
    if not NEWS_API_KEY or NEWS_API_KEY == "isi_api_key_kamu_di_sini":
        return []

    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    queries   = [f"{keyword} Indonesia", keyword, f"Indonesia {keyword}"]
    if module == "geo":
        queries.insert(0, f"{keyword} bencana Indonesia")
    elif module == "threat":
        queries.insert(0, f"{keyword} hoax disinformasi")
    elif module == "media":
        queries.insert(0, f"{keyword} media berita")

    raw, seen = [], set()
    for q in queries[:2]:
        for lang in ["id", "en"]:
            try:
                r = requests.get(
                    "https://newsapi.org/v2/everything",
                    params={"q": q, "pageSize": min(page_size, 100),
                            "sortBy": "relevancy", "language": lang,
                            "from": date_from, "apiKey": NEWS_API_KEY},
                    timeout=12,
                )
                for art in r.json().get("articles", []):
                    url = art.get("url", "")
                    title = art.get("title", "") or ""
                    if url and url not in seen and title and title != "[Removed]":
                        seen.add(url)
                        raw.append(_normalize_newsapi(art))
            except Exception:
                continue
        if len(raw) >= 20:
            break
    return raw


def _normalize_newsapi(art: dict) -> dict:
    src = art.get("source") or {}
    return {
        "title":       art.get("title", ""),
        "description": art.get("description", "") or "",
        "content":     art.get("content", "") or "",
        "source":      src.get("name", "NewsAPI") if isinstance(src, dict) else str(src),
        "url":         art.get("url", ""),
        "published_at":art.get("publishedAt", ""),
        "_src_type":   "newsapi",
    }


# ── Source 2: GDELT ───────────────────────────────────────────────────────────
def _fetch_gdelt(keyword: str, module: str, max_records: int = 50) -> list:
    """
    Fetch dari GDELT Project v2 DOC API.
    Tidak perlu API key. Coverage global + Indonesia sangat luas.
    """
    # Buat query GDELT
    geo_filter = " sourcelang:Indonesian OR sourcecountry:IN"
    q = keyword + geo_filter

    timespan_map = {"geo": "7d", "threat": "3d", "person": "14d", "media": "7d"}
    timespan = timespan_map.get(module, "7d")

    params = {
        "query":      q,
        "mode":       "artlist",
        "maxrecords": max_records,
        "format":     "json",
        "timespan":   timespan,
        "sort":       "datedesc",
    }
    try:
        r = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params=params, headers=_HEADERS, timeout=15,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        articles = data.get("articles", [])
        return [_normalize_gdelt(a) for a in articles if a.get("title")]
    except Exception:
        return []


def _normalize_gdelt(art: dict) -> dict:
    """Normalisasi artikel GDELT ke format internal."""
    # GDELT punya secore tone (-100 s/d +100) dan domain
    tone = float(art.get("tone", 0) or 0)
    # Konversi tone GDELT ke sentiment -1..+1
    sentiment_hint = max(-1.0, min(1.0, tone / 100))
    return {
        "title":          art.get("title", ""),
        "description":    art.get("seendate", ""),
        "content":        "",
        "source":         art.get("domain", "GDELT"),
        "url":            art.get("url", ""),
        "published_at":   _parse_gdelt_date(art.get("seendate", "")),
        "_src_type":      "gdelt",
        "_sentiment_hint":sentiment_hint,
        "_tone":          tone,
        "_language":      art.get("language", ""),
        "_country":       art.get("sourcecountry", ""),
    }


def _parse_gdelt_date(d: str) -> str:
    """Parse GDELT date format YYYYMMDDHHMMSS ke ISO."""
    try:
        if len(d) >= 14:
            return datetime.strptime(d[:14], "%Y%m%d%H%M%S").isoformat()
        elif len(d) >= 8:
            return datetime.strptime(d[:8], "%Y%m%d").isoformat()
    except Exception:
        pass
    return datetime.now().isoformat()


# ── Source 3: RSS Indonesia ───────────────────────────────────────────────────
def _fetch_rss(keyword: str, module: str, max_per_feed: int = 10) -> list:
    """
    Fetch dari RSS feeds media Indonesia.
    Filter artikel yang mengandung keyword.
    """
    kw_lower = keyword.lower()
    results  = []
    seen     = set()

    # Pilih feed berdasarkan modul
    if module == "geo":
        priority = ["Antara", "Antara Politik", "Antara Hukum",
                    "Kompas", "Detik News"]
    elif module == "threat":
        priority = ["Tempo", "Kompas", "Detik", "CNN Indonesia", "Republika"]
    elif module == "media":
        priority = ["Detik", "Kompas", "CNN Indonesia", "Tribun",
                    "Okezone", "Liputan6", "Medcom"]
    else:
        priority = list(RSS_FEEDS.keys())

    feeds_to_try = {k: v for k, v in RSS_FEEDS.items() if k in priority}
    feeds_to_try.update({k: v for k, v in RSS_FEEDS.items() if k not in priority})

    for source_name, feed_url in feeds_to_try.items():
        if len(results) >= 40:
            break
        try:
            r = requests.get(feed_url, headers=_HEADERS, timeout=8)
            if r.status_code != 200:
                continue
            root = ET.fromstring(r.content)
            # Support RSS 2.0 dan Atom
            items = root.findall(".//item") or root.findall(
                ".//{http://www.w3.org/2005/Atom}entry"
            )
            count = 0
            for item in items:
                if count >= max_per_feed:
                    break
                title = _get_xml_text(item, ["title"])
                desc  = _get_xml_text(item, ["description", "summary",
                                              "{http://www.w3.org/2005/Atom}summary"])
                link  = _get_xml_text(item, ["link",
                                              "{http://www.w3.org/2005/Atom}link"])
                pubdate = _get_xml_text(item, ["pubDate", "published",
                                               "{http://www.w3.org/2005/Atom}published"])

                if not title or link in seen:
                    continue

                # Filter by keyword (loose match)
                text_check = (title + " " + desc).lower()
                if kw_lower and not any(
                    part.strip() in text_check
                    for part in kw_lower.split()
                    if len(part.strip()) > 3
                ):
                    continue

                seen.add(link)
                results.append({
                    "title":       title,
                    "description": desc,
                    "content":     "",
                    "source":      source_name,
                    "url":         link,
                    "published_at":_parse_rss_date(pubdate),
                    "_src_type":   "rss",
                })
                count += 1
        except Exception:
            continue

    return results


def _get_xml_text(elem, tags: list) -> str:
    for tag in tags:
        node = elem.find(tag)
        if node is not None:
            if tag == "{http://www.w3.org/2005/Atom}link":
                return node.get("href", node.text or "")
            return (node.text or "").strip()
    return ""


def _parse_rss_date(d: str) -> str:
    """Parse berbagai format tanggal RSS."""
    if not d:
        return datetime.now().isoformat()
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(d.strip(), fmt).isoformat()
        except Exception:
            continue
    return datetime.now().isoformat()


# ── Source 4: BMKG (khusus Geo Intel) ────────────────────────────────────────
def _fetch_bmkg(keyword: str) -> list:
    """
    Fetch data gempa dari BMKG.
    Hanya aktif untuk modul Geo.
    Konversi ke format artikel untuk di-analisis.
    """
    results = []
    kw_lower = keyword.lower()

    for ep_name, ep_url in BMKG_ENDPOINTS.items():
        try:
            r = requests.get(ep_url, headers=_HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()

            # BMKG response bisa bervariasi per endpoint
            quakes = []
            if "Infogempa" in data:
                info = data["Infogempa"]
                if "gempa" in info:
                    g = info["gempa"]
                    if isinstance(g, list):
                        quakes = g
                    elif isinstance(g, dict):
                        quakes = [g]

            for q in quakes[:10]:
                mag    = q.get("Magnitude", q.get("magnitude", "?"))
                loc    = q.get("Wilayah",   q.get("wilayah", q.get("Keterangan", "")))
                depth  = q.get("Kedalaman", q.get("kedalaman", ""))
                time_q = q.get("Tanggal",   "") + " " + q.get("Jam", "")
                lat    = q.get("Lintang",   q.get("lat", ""))
                lon    = q.get("Bujur",     q.get("lon", ""))

                if not loc:
                    continue

                # Filter by keyword jika ada (opsional)
                title = f"Gempa M{mag} — {loc}"
                desc  = (
                    f"Gempa bumi berkekuatan M{mag} terjadi di {loc}. "
                    f"Kedalaman {depth}. Waktu: {time_q.strip()}."
                )

                results.append({
                    "title":       title,
                    "description": desc,
                    "content":     desc,
                    "source":      "BMKG",
                    "url":         "https://www.bmkg.go.id/gempabumi/",
                    "published_at":_parse_bmkg_date(time_q),
                    "_src_type":   "bmkg",
                    "_lat_hint":   _parse_coord(lat),
                    "_lon_hint":   _parse_coord(lon),
                    "_mag":        float(str(mag).replace(",", ".") or 0),
                })
        except Exception:
            continue

    return results


def _parse_bmkg_date(d: str) -> str:
    d = d.strip()
    formats = [
        "%d-%b-%Y %H:%M:%S WIB",
        "%d %b %Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(d, fmt).isoformat()
        except Exception:
            continue
    return datetime.now().isoformat()


def _parse_coord(c: str) -> float:
    try:
        c = str(c).replace("LS", "").replace("LU", "").replace("BT", "").strip()
        val = float(c.replace(",", "."))
        return -val if "LS" in str(c) else val
    except Exception:
        return 0.0


# ── Main fetch function ───────────────────────────────────────────────────────
def fetch_articles(monitor_id: int, module: str, keyword: str,
                   page_size: int = 50) -> tuple:
    """
    Ambil artikel dari SEMUA sumber (NewsAPI + GDELT + RSS + BMKG),
    analisis, simpan ke DB.
    Return: (n_saved, error_msg)
    """
    raw_all  = []
    seen_urls = set()
    sources_used = []

    def _add(articles: list, src_label: str):
        n_before = len(raw_all)
        for art in articles:
            url = art.get("url", "")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            raw_all.append(art)
        added = len(raw_all) - n_before
        if added > 0:
            sources_used.append(f"{src_label}:{added}")

    # 1. NewsAPI (jika ada key)
    if NEWS_API_KEY and NEWS_API_KEY != "isi_api_key_kamu_di_sini":
        _add(_fetch_newsapi(keyword, module, page_size // 2), "NewsAPI")

    # 2. GDELT — selalu coba
    _add(_fetch_gdelt(keyword, module, max_records=50), "GDELT")

    # 3. RSS Indonesia — selalu aktif
    _add(_fetch_rss(keyword, module, max_per_feed=8), "RSS-ID")

    # 4. BMKG — khusus modul geo
    if module == "geo":
        _add(_fetch_bmkg(keyword), "BMKG")

    if not raw_all:
        return 0, (
            "Tidak ada artikel ditemukan dari semua sumber "
            "(NewsAPI, GDELT, RSS Indonesia, BMKG). "
            "Coba keyword yang berbeda."
        )

    # ── Analisis setiap artikel ───────────────────────────────────────────────
    processed = []
    for art in raw_all:
        result = analyze_article(art, module)

        # Override sentiment jika ada hint dari GDELT
        if art.get("_sentiment_hint") is not None:
            result["sentiment"] = (result["sentiment"] + art["_sentiment_hint"]) / 2

        # Override koordinat jika ada hint dari BMKG
        if art.get("_lat_hint") and art.get("_lon_hint"):
            if result.get("lat", 0) == 0:
                result["lat"] = art["_lat_hint"]
                result["lon"] = art["_lon_hint"]
                if not result.get("location"):
                    result["location"] = "Indonesia"
                    result["province"] = "Nasional"

        # Tambah severity ekstra untuk gempa BMKG berdasarkan magnitudo
        if art.get("_src_type") == "bmkg":
            mag = art.get("_mag", 0)
            if mag >= 7.0:
                result["severity"]   = max(result.get("severity", 0), 90)
                result["inc_type"]   = "BENCANA"
            elif mag >= 6.0:
                result["severity"]   = max(result.get("severity", 0), 75)
                result["inc_type"]   = "BENCANA"
            elif mag >= 5.0:
                result["severity"]   = max(result.get("severity", 0), 55)
                result["inc_type"]   = "BENCANA"

        # Tag sumber
        result["_src_type"] = art.get("_src_type", "unknown")
        processed.append(result)

    # ── Simpan artikel ────────────────────────────────────────────────────────
    art_ids = save_articles(monitor_id, module, processed)
    n_saved = len(art_ids)

    # ── Alert jika threat tinggi ──────────────────────────────────────────────
    for i, art in enumerate(processed):
        if art.get("threat_score", 0) >= 60 and i < len(art_ids):
            save_alert(
                monitor_id   = monitor_id,
                article_id   = art_ids[i],
                alert_type   = art.get("threat_dominant", "HOAX"),
                threat_score = art.get("threat_score", 0),
                message      = "[" + art["source"] + "] " + art["title"][:80],
            )

    # ── Entity extraction ─────────────────────────────────────────────────────
    entity_counter: Counter = Counter()
    co_occur:       Counter = Counter()
    for art in processed:
        text = (art.get("title", "") + " " + art.get("description", "")).strip()
        if not text:
            continue
        ents_in_doc = []
        for ent_text, ent_label in extract_entities_rule_based(text):
            entity_counter[(ent_text, ent_label)] += 1
            ents_in_doc.append(ent_text)
        unique_ents = list(dict.fromkeys(ents_in_doc))
        for i, ea in enumerate(unique_ents):
            for eb in unique_ents[i+1:]:
                if ea != eb:
                    co_occur[tuple(sorted([ea, eb]))] += 1

    entities = [{"text": t, "label": l, "count": c}
                for (t, l), c in entity_counter.most_common(100)]
    save_entities(monitor_id, entities)

    relations = [{"entity_a": ea, "entity_b": eb, "weight": w}
                 for (ea, eb), w in co_occur.most_common(50) if ea != eb]
    save_relations(monitor_id, relations)

    # ── Narrative clustering ──────────────────────────────────────────────────
    clusters = cluster_narratives(processed, n_clusters=6)
    if clusters:
        save_narratives(monitor_id, clusters)

    # ── Province stats (geo) ──────────────────────────────────────────────────
    if module == "geo":
        df_inc = pd.DataFrame(processed)
        if not df_inc.empty and "province" in df_inc.columns:
            df_inc["id"] = range(len(df_inc))
            df_inc_geo = df_inc[df_inc["location"] != ""]
            if not df_inc_geo.empty:
                update_province_stats(monitor_id, df_inc_geo)

    src_summary = ", ".join(sources_used) if sources_used else "none"
    return n_saved, None
