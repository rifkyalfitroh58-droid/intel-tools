"""
OSINT Intelligence Suite — fetcher.py
Satu fungsi fetch untuk semua modul + auto-analisis
"""
import requests
import sys, os
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


def _build_queries(keyword: str, module: str) -> list:
    """Buat kombinasi query untuk maksimalkan hasil NewsAPI."""
    base = [
        f"{keyword} Indonesia",
        keyword,
        f"Indonesia {keyword}",
    ]
    if module == "geo":
        base.insert(0, f"{keyword} Indonesia disaster")
    elif module == "threat":
        base.insert(0, f"{keyword} hoax disinformation")
    elif module == "media":
        base.insert(0, f"{keyword} media news")
    return base


def fetch_articles(monitor_id: int, module: str, keyword: str,
                   page_size: int = 50) -> tuple:
    """
    Ambil artikel dari NewsAPI, analisis, simpan ke DB.
    Return: (n_saved, error_msg)
    """
    if not NEWS_API_KEY or NEWS_API_KEY == "isi_api_key_kamu_di_sini":
        return 0, "NEWS_API_KEY belum diisi di config.py atau Streamlit Secrets"

    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    queries   = _build_queries(keyword, module)
    raw_all   = []
    seen_urls  = set()

    for q in queries:
        for lang in ["en", "id"]:
            for use_date in [True, False]:
                try:
                    params = {
                        "q":        q,
                        "pageSize": min(page_size, 100),
                        "sortBy":   "relevancy",
                        "language": lang,
                        "apiKey":   NEWS_API_KEY,
                    }
                    if use_date:
                        params["from"] = date_from

                    resp = requests.get(
                        "https://newsapi.org/v2/everything",
                        params=params, timeout=15,
                    )
                    data = resp.json()

                    if data.get("status") == "ok":
                        for art in data.get("articles", []):
                            url   = art.get("url","")
                            title = art.get("title","") or ""
                            if (url and url not in seen_urls
                                    and title and title != "[Removed]"):
                                seen_urls.add(url)
                                raw_all.append(art)
                        if len(raw_all) >= 10:
                            break
                except Exception:
                    continue
            if len(raw_all) >= 10:
                break
        if len(raw_all) >= 10:
            break

    if not raw_all:
        return 0, "Tidak ada artikel ditemukan. Coba keyword lain."

    # Analisis setiap artikel
    processed = []
    for art in raw_all:
        result = analyze_article(art, module)
        processed.append(result)

    # Simpan artikel
    art_ids = save_articles(monitor_id, module, processed)
    n_saved = len(art_ids)

    # Simpan alert jika threat tinggi
    for i, art in enumerate(processed):
        if art.get("threat_score", 0) >= 60 and i < len(art_ids):
            save_alert(
                monitor_id   = monitor_id,
                article_id   = art_ids[i],
                alert_type   = art.get("threat_dominant","HOAX"),
                threat_score = art.get("threat_score", 0),
                message      = f"[{art['source']}] {art['title'][:80]}",
            )

    # Entity extraction
    entity_counter: Counter = Counter()
    co_occur:       Counter = Counter()
    for art in processed:
        text = (art.get("title","") + " " + art.get("description","")).strip()
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

    entities = [{"text":t,"label":l,"count":c}
                for (t,l),c in entity_counter.most_common(100)]
    save_entities(monitor_id, entities)

    relations = [{"entity_a":ea,"entity_b":eb,"weight":w}
                 for (ea,eb),w in co_occur.most_common(50)
                 if ea != eb]
    save_relations(monitor_id, relations)

    # Narrative clustering
    clusters = cluster_narratives(processed, n_clusters=5)
    if clusters:
        save_narratives(monitor_id, clusters)

    # Province stats (modul geo)
    if module == "geo":
        df_inc = pd.DataFrame(processed)
        if not df_inc.empty and "province" in df_inc.columns:
            df_inc["id"] = range(len(df_inc))
            df_inc_geo = df_inc[df_inc["location"] != ""]
            if not df_inc_geo.empty:
                update_province_stats(monitor_id, df_inc_geo)

    return n_saved, None
