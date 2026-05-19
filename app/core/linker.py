"""
OSINT Intelligence Suite — linker.py
Engine keterhubungan artikel lintas modul
"""
import re
import sys, os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import (load_all_articles, save_article_link,
                      get_article_links, load_entities)
from config import MODULE_COLORS, MODULE_LABELS


def _normalize(text: str) -> str:
    """Normalisasi teks untuk perbandingan."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def _title_similarity(t1: str, t2: str) -> float:
    """Hitung kemiripan judul 0.0–1.0 berdasarkan word overlap."""
    w1 = set(_normalize(t1).split())
    w2 = set(_normalize(t2).split())
    if not w1 or not w2:
        return 0.0
    intersection = w1 & w2
    union        = w1 | w2
    return len(intersection) / len(union)


def _extract_entities_simple(text: str) -> set:
    """Ekstrak proper noun sederhana dari teks."""
    words = re.findall(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b', text or "")
    return {w for w in words if len(w) > 3}


def build_links(monitor_id: int = None):
    """
    Bangun keterhubungan antar artikel di DB.
    Deteksi berdasarkan:
    1. URL identik → link type 'same_article'
    2. Title similarity >= 0.5 → link type 'similar_title'
    3. Entity overlap >= 2 → link type 'shared_entity'
    4. Keyword/topik serupa → link type 'same_topic'
    """
    df = load_all_articles()
    if df.empty or len(df) < 2:
        return 0

    n_links = 0
    articles = df.to_dict("records")
    n        = len(articles)

    # Batasi untuk performa: max 200 artikel
    articles = articles[:200]
    n        = len(articles)

    for i in range(n):
        a = articles[i]
        a_id    = a.get("id")
        a_url   = a.get("url","")
        a_title = a.get("title","")
        a_ents  = _extract_entities_simple(a_title + " " + (a.get("description","") or ""))
        a_mod   = a.get("module","")

        for j in range(i+1, n):
            b = articles[j]
            b_id    = b.get("id")
            b_url   = b.get("url","")
            b_title = b.get("title","")
            b_ents  = _extract_entities_simple(b_title + " " + (b.get("description","") or ""))
            b_mod   = b.get("module","")

            # Jangan link artikel dari modul yang sama
            if a_mod == b_mod:
                continue

            score     = 0.0
            link_type = None
            modules   = sorted(list({a_mod, b_mod}))

            # 1. URL identik
            if a_url and b_url and a_url == b_url:
                score     = 1.0
                link_type = "same_article"

            # 2. Title similarity
            elif a_title and b_title:
                sim = _title_similarity(a_title, b_title)
                if sim >= 0.5:
                    score     = sim
                    link_type = "similar_title"

            # 3. Entity overlap
            if not link_type:
                shared = a_ents & b_ents
                if len(shared) >= 2:
                    score     = min(len(shared) / 5, 1.0)
                    link_type = "shared_entity"

            if link_type and score > 0 and a_id and b_id:
                save_article_link(a_id, b_id, link_type, round(score,3), modules)
                save_article_link(b_id, a_id, link_type, round(score,3), modules)
                n_links += 1

    return n_links


def get_link_badges(article_id: int) -> list:
    """
    Return list badge untuk satu artikel — modul mana saja yang terhubung.
    Format: [{"module": "threat", "label": "Threat Intel",
               "color": "#E74C3C", "score": 0.8, "linked_id": 12}]
    """
    df_links = get_article_links(article_id)
    if df_links.empty:
        return []

    badges = []
    seen_modules = set()

    for _, row in df_links.iterrows():
        mod = row.get("linked_module","")
        if mod and mod not in seen_modules:
            seen_modules.add(mod)
            badges.append({
                "module":     mod,
                "label":      MODULE_LABELS.get(mod, mod),
                "color":      MODULE_COLORS.get(mod, "#888"),
                "score":      row.get("score", 0.0),
                "linked_id":  int(row.get("linked_id", 0)),
                "link_type":  row.get("link_type",""),
            })

    return sorted(badges, key=lambda x: x["score"], reverse=True)


def get_panel_data(article_id: int) -> dict:
    """
    Return data lengkap untuk panel keterhubungan satu artikel.
    """
    from database import get_article_by_id
    df_links = get_article_links(article_id)
    article  = get_article_by_id(article_id)

    if df_links.empty:
        return {"article": article, "links": [], "summary": {}}

    links_by_module = {}
    for _, row in df_links.iterrows():
        mod = row.get("linked_module","")
        if mod not in links_by_module:
            links_by_module[mod] = []
        links_by_module[mod].append({
            "id":          int(row.get("linked_id", 0)),
            "title":       row.get("linked_title",""),
            "source":      row.get("linked_source",""),
            "url":         row.get("linked_url",""),
            "link_type":   row.get("link_type",""),
            "score":       float(row.get("score",0)),
            "hoax_score":  float(row.get("hoax_score",0)),
            "hate_score":  float(row.get("hate_score",0)),
            "threat_score":float(row.get("threat_score",0)),
            "severity":    float(row.get("severity",0)),
            "location":    row.get("location",""),
        })

    summary = {
        mod: {
            "count":       len(items),
            "avg_threat":  round(sum(i["threat_score"] for i in items)/len(items),1),
            "max_threat":  max(i["threat_score"] for i in items),
        }
        for mod, items in links_by_module.items()
    }

    return {
        "article":         article,
        "links_by_module": links_by_module,
        "summary":         summary,
        "total_links":     len(df_links),
    }


def get_cross_module_stats() -> dict:
    """Statistik keterhubungan lintas modul secara global."""
    df = load_all_articles()
    if df.empty:
        return {}

    stats = {}
    for mod in ["person","threat","geo","media"]:
        mod_df = df[df["module"] == mod]
        stats[mod] = {
            "total":       len(mod_df),
            "avg_threat":  round(float(mod_df["threat_score"].mean()),1) if not mod_df.empty else 0,
            "high_threat": int((mod_df["threat_score"] >= 60).sum()) if not mod_df.empty else 0,
        }
    return stats
