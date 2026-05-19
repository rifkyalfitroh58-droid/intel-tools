"""
OSINT Intelligence Suite — analyzer.py
Engine NLP terpadu untuk semua modul
"""
import re
import math
from collections import Counter
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    HOAX_KEYWORDS, HATE_KEYWORDS, PROVOKASI_KEYWORDS,
    ENTITY_COLORS, CITIES, PROVINCES, LOCATION_ALIASES,
    INCIDENT_KEYWORDS,
)

# ── Optional NLP ──────────────────────────────────────────────────────────────
try:
    from textblob import TextBlob
    TB_OK = True
except Exception:
    TB_OK = False

# ── Known entities ────────────────────────────────────────────────────────────
_KNOWN_PERSONS = {
    "Elon Musk","Sam Altman","Jeff Bezos","Sundar Pichai","Tim Cook",
    "Mark Zuckerberg","Satya Nadella",
    "Prabowo Subianto","Prabowo","Joko Widodo","Jokowi","Gibran",
    "Sri Mulyani","Anies Baswedan","Megawati","Airlangga","Luhut",
    "Nadiem Makarim","Mahfud","Yusril",
    "Donald Trump","Joe Biden","Kamala Harris","Barack Obama",
    "Vladimir Putin","Xi Jinping","Emmanuel Macron","Narendra Modi",
    "Volodymyr Zelensky","Benjamin Netanyahu","Keir Starmer",
}
_KNOWN_ORGS = {
    "Tesla","SpaceX","OpenAI","Google","Apple","Microsoft","Amazon","Meta",
    "DOGE","SEC","NASA","UN","WHO","NATO","EU","IMF","World Bank",
    "Pertamina","PLN","Telkom","BRI","BNI","Mandiri","Bulog","Garuda",
    "TNI","Polri","KPK","DPR","MPR","MK","BI","OJK",
    "Republican Party","Democrat","White House","Pentagon","Congress",
    "BBC","CNN","Reuters","Bloomberg","Al Jazeera",
}
_KNOWN_LOCS = {
    "United States","US","USA","Russia","China","Ukraine","Iran","Israel",
    "Europe","UK","Germany","France","Japan","India","Australia",
    "Indonesia","Singapore","Malaysia","Thailand","Philippines",
    "Middle East","Southeast Asia","Saudi Arabia","UAE","Turkey",
    "Washington","New York","London","Brussels","Beijing","Moscow","Tehran",
}
_FALSE_POSITIVES = {
    "former google","education ministry","the indonesian","in west",
    "the court","this week","he said","she said","the white","the senate",
}

_STOPWORDS = {
    "yang","di","ke","dan","dari","dengan","ini","itu","tidak","untuk",
    "ada","bisa","pada","juga","akan","sudah","karena","saat","oleh",
    "the","a","an","in","of","to","and","or","for","on","at","is","are",
    "was","were","with","this","that","it","as","be","has","have","had",
    "will","would","can","could","from","but","not","so","by","via",
    "after","before","while","since","through","without","about","amid",
}

_MANIPULATIVE = [
    r'\b(terbukti|faktanya|sebenarnya)\b',
    r'\b(segera sebarkan|jangan sampai terhapus)\b',
    r'\b(mereka tidak mau|disembunyikan|rahasia besar)\b',
    r'\b(viral|breaking)\s*!{2,}',
]
_SARA = [
    r'\b(suku|ras|agama|etnis)\b.{0,20}\b(rendah|hina|kotor|jahat)\b',
    r'\b(kafir|murtad)\b',
    r'\b(pribumi|pendatang)\b.{0,20}\b(usir|terusir)\b',
]

_POSITIVE = {"bagus","baik","benar","positif","mendukung","setuju",
             "sukses","aman","damai","sejahtera","bersatu"}
_NEGATIVE = {"buruk","jahat","salah","negatif","gagal","bahaya",
             "rusak","hancur","korup","curang","bohong","palsu",
             "tipu","fitnah","hasut","provokasi","sesat","ancaman"}

_CITY_LOWER = {k.lower(): {"name":k,**v} for k,v in CITIES.items()}
_PROV_LOWER = {k.lower(): {"name":k,**v} for k,v in PROVINCES.items()}


# ── Sentiment ─────────────────────────────────────────────────────────────────
def analyze_sentiment(text: str) -> float:
    if not text.strip():
        return 0.0
    if TB_OK:
        try:
            s = TextBlob(text).sentiment.polarity
            if s != 0.0:
                return round(s, 4)
        except Exception:
            pass
    words = set(re.findall(r'[a-zA-Z]+', text.lower()))
    pos   = len(words & _POSITIVE)
    neg   = len(words & _NEGATIVE)
    total = pos + neg
    return round((pos - neg) / total, 4) if total > 0 else 0.0


# ── Hoax ─────────────────────────────────────────────────────────────────────
def compute_hoax_score(text: str, title: str = "") -> float:
    full  = (title + " " + text).lower()
    score = 0.0
    score += min(sum(1 for kw in HOAX_KEYWORDS if kw.lower() in full) * 8, 40)
    score += min(sum(1 for p in _MANIPULATIVE
                     if re.search(p, full, re.IGNORECASE)) * 10, 30)
    score += min(len(re.findall(r'!{2,}', full)) * 3 +
                 len(re.findall(r'[A-Z]{4,}', title)) * 2, 15)
    return round(min(score, 100), 1)


# ── Hate speech ───────────────────────────────────────────────────────────────
def compute_hate_score(text: str) -> float:
    tl    = text.lower()
    score = 0.0
    score += min(sum(1 for kw in HATE_KEYWORDS if kw in tl) * 15, 45)
    score += min(sum(1 for p in _SARA
                     if re.search(p, tl, re.IGNORECASE)) * 20, 35)
    return round(min(score, 100), 1)


# ── Provokasi ─────────────────────────────────────────────────────────────────
def compute_provok_score(text: str) -> float:
    tl   = text.lower()
    hits = sum(1 for kw in PROVOKASI_KEYWORDS if kw in tl)
    return round(min(hits * 12, 100), 1)


# ── Risk score (modul A) ──────────────────────────────────────────────────────
def compute_risk_score(df_art) -> dict:
    if df_art.empty:
        return {"total":0.0,"volume":0.0,"sentimen":0.0,
                "keragaman":0.0,"sensitif":0.0}
    n         = len(df_art)
    vol_raw   = min(math.log1p(n) / math.log1p(200) * 25, 25)
    neg_ratio = (df_art["sentiment"] < -0.05).sum() / max(n,1)
    sent_raw  = round(neg_ratio * 30, 2)
    div_raw   = min(df_art["source"].nunique() / 10 * 20, 20)
    SENS      = ["arrest","crime","fraud","corruption","scandal","lawsuit",
                 "penipuan","korupsi","ditangkap","tersangka","pidana","skandal"]
    sens_hits = df_art["title"].str.lower().fillna("").apply(
        lambda t: any(k in t for k in SENS)
    ).sum()
    sens_raw  = min(sens_hits / max(n,1) * 25 * 3, 25)
    total     = round(min(vol_raw+sent_raw+div_raw+sens_raw, 100), 1)
    return {"total":total,"volume":round(vol_raw,1),
            "sentimen":round(sent_raw,1),"keragaman":round(div_raw,1),
            "sensitif":round(sens_raw,1)}


# ── Threat score (modul B) ────────────────────────────────────────────────────
def compute_threat_score(hoax: float, hate: float,
                         provok: float, spread: float = 0) -> dict:
    total    = round(min(hoax*0.35+hate*0.30+provok*0.20+spread*0.15, 100), 1)
    scores   = {"HOAX":hoax,"HATE":hate,"PROVOKASI":provok}
    dominant = max(scores, key=scores.get) if total >= 20 else "NORMAL"
    return {"total":total,"dominant":dominant}


# ── Geo parser ────────────────────────────────────────────────────────────────
def extract_locations(text: str) -> list:
    if not text:
        return []
    tl    = text.lower()
    found = {}

    def _add(name, lat, lon, province, loc_type):
        key = name.lower().strip()
        if key and key not in _FALSE_POSITIVES and name not in found:
            found[name] = {"name":name,"lat":lat,"lon":lon,
                           "province":province,"type":loc_type}

    for alias, canonical in LOCATION_ALIASES.items():
        if re.search(r'\b'+re.escape(alias)+r'\b', tl):
            if canonical in CITIES:
                c = CITIES[canonical]
                _add(canonical, c["lat"], c["lon"],
                     c.get("province",canonical), "city")
            elif canonical in PROVINCES:
                p = PROVINCES[canonical]
                _add(canonical, p["lat"], p["lon"], canonical, "province")

    for city_l, info in _CITY_LOWER.items():
        if re.search(r'\b'+re.escape(city_l)+r'\b', tl):
            _add(info["name"], info["lat"], info["lon"],
                 info.get("province",""), "city")

    for prov_l, info in _PROV_LOWER.items():
        if re.search(r'\b'+re.escape(prov_l)+r'\b', tl):
            _add(info["name"], info["lat"], info["lon"],
                 info["name"], "province")

    return list(found.values())


def classify_incident(text: str) -> str:
    tl     = text.lower()
    scores = {}
    for inc_type, keywords in INCIDENT_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw.lower() in tl)
        if hits > 0:
            scores[inc_type] = hits
    return max(scores, key=scores.get) if scores else "LAINNYA"


def compute_severity(text: str, inc_type: str) -> float:
    tl    = text.lower()
    score = 20.0
    HIGH  = ["korban jiwa","meninggal","tewas","kritis","darurat",
             "dead","killed","emergency","critical","mass"]
    MED   = ["korban luka","terdampak","rusak","mengungsi",
             "injured","damaged","displaced"]
    score += min(sum(1 for kw in HIGH if kw in tl) * 15, 40)
    score += min(sum(1 for kw in MED  if kw in tl) * 8, 20)
    nums   = re.findall(r'(\d+)\s*(orang|korban|jiwa|warga|rumah)', tl)
    for ns, _ in nums:
        n = int(ns)
        score += 20 if n>=100 else 10 if n>=10 else 5
    W = {"BENCANA":1.1,"KONFLIK":1.0,"KRIMINAL":0.9,
         "POLITIK":0.7,"EKONOMI":0.8,"KESEHATAN":1.0,"LAINNYA":0.6}
    return round(min(score * W.get(inc_type, 0.8), 100), 1)


# ── Entity extraction ─────────────────────────────────────────────────────────
def extract_entities_rule_based(text: str) -> list:
    if not text:
        return []
    results, seen = [], set()

    def _add(ent, label):
        key = ent.lower().strip()
        if key and key not in seen and key not in _FALSE_POSITIVES:
            seen.add(key)
            results.append((ent, label))

    for ent in _KNOWN_PERSONS:
        if re.search(r'\b'+re.escape(ent)+r'\b', text, re.IGNORECASE):
            _add(ent, "PERSON")
    for ent in _KNOWN_ORGS:
        if re.search(r'\b'+re.escape(ent)+r'\b', text, re.IGNORECASE):
            _add(ent, "ORG")
    for ent in _KNOWN_LOCS:
        if re.search(r'\b'+re.escape(ent)+r'\b', text, re.IGNORECASE):
            _add(ent, "GPE")
    caps = re.findall(r'\b([A-Z][a-z]{1,}(?:\s+[A-Z][a-z]{1,}){1,3})\b', text)
    for cap in caps:
        if len(cap) > 5:
            _add(cap, "PERSON")
    return results


# ── Narrative clustering ──────────────────────────────────────────────────────
def cluster_narratives(articles: list, n_clusters: int = 5) -> list:
    if not articles:
        return []
    texts = [(a.get("title","")+" "+a.get("description","")).lower()
             for a in articles]
    all_w = []
    for t in texts:
        words = re.findall(r'[a-zA-Z]{4,}', t)
        all_w.extend([w for w in words if w not in _STOPWORDS])
    freq      = Counter(all_w)
    top_seeds = [w for w,_ in freq.most_common(n_clusters*8)]
    clusters, used = [], set()
    for seed in top_seeds:
        if seed in used or len(clusters) >= n_clusters:
            continue
        mask = [i for i,t in enumerate(texts)
                if re.search(r'\b'+re.escape(seed)+r'\b', t)]
        if len(mask) < 2:
            continue
        co_w = re.findall(r'[a-zA-Z]{4,}',
                          " ".join(texts[i] for i in mask))
        co_w = [w for w in co_w if w not in _STOPWORDS and w != seed]
        top  = [w for w,_ in Counter(co_w).most_common(8)
                if w not in used][:5]
        used.update([seed]+top[:2])
        clusters.append({
            "id":len(clusters)+1,"label":seed.title(),
            "keywords":[seed]+top,"count":len(mask),
        })
    return clusters


# ── Full article analysis ─────────────────────────────────────────────────────
def analyze_article(article: dict, module: str) -> dict:
    title   = article.get("title","")       or ""
    desc    = article.get("description","") or ""
    content = article.get("content","")     or ""
    text    = " ".join([title, desc, content]).strip()
    source  = article.get("source") or {}
    if isinstance(source, dict):
        source = source.get("name","Unknown")

    hoax   = compute_hoax_score(text, title)
    hate   = compute_hate_score(text)
    provok = compute_provok_score(text)
    threat = compute_threat_score(hoax, hate, provok)
    sent   = analyze_sentiment(text)

    result = {
        "title":          title,
        "description":    desc,
        "content":        content,
        "source":         source,
        "url":            article.get("url","")         or "",
        "published_at":   article.get("publishedAt","") or article.get("published_at",""),
        "sentiment":      sent,
        "hoax_score":     hoax,
        "hate_score":     hate,
        "provok_score":   provok,
        "threat_score":   threat["total"],
        "threat_dominant":threat["dominant"],
        "risk_score":     0.0,
        "location":       "",
        "province":       "",
        "lat":            0.0,
        "lon":            0.0,
        "inc_type":       "LAINNYA",
        "severity":       0.0,
        "module":         module,
    }

    locs = extract_locations(text)
    if locs:
        loc      = locs[0]
        inc_type = classify_incident(text)
        severity = compute_severity(text, inc_type)
        result.update({
            "location": loc["name"], "province": loc["province"],
            "lat": loc["lat"], "lon": loc["lon"],
            "inc_type": inc_type, "severity": severity,
        })
    elif module == "geo":
        inc_type = classify_incident(text)
        severity = compute_severity(text, inc_type)
        if inc_type != "LAINNYA" and severity >= 20:
            result.update({
                "location":"Indonesia","province":"Nasional",
                "lat":-2.5,"lon":118.0,
                "inc_type":inc_type,"severity":severity,
            })
    return result


# ── Color/label helpers ───────────────────────────────────────────────────────
def get_risk_color(score: float) -> str:
    if score >= 70: return "#E74C3C"
    if score >= 40: return "#F39C12"
    return "#2ECC71"

def get_risk_label(score: float) -> str:
    if score >= 70: return "🔴 TINGGI"
    if score >= 40: return "🟡 SEDANG"
    return "🟢 RENDAH"

def get_threat_color(score: float) -> str:
    if score >= 80: return "#E74C3C"
    if score >= 60: return "#E67E22"
    if score >= 40: return "#F39C12"
    return "#2ECC71"

def get_threat_label(score: float) -> str:
    if score >= 80: return "🔴 KRITIS"
    if score >= 60: return "🟠 TINGGI"
    if score >= 40: return "🟡 SEDANG"
    return "🟢 RENDAH"

def get_sev_color(score: float) -> str:
    if score >= 75: return "#E74C3C"
    if score >= 50: return "#E67E22"
    if score >= 25: return "#F39C12"
    return "#2ECC71"
