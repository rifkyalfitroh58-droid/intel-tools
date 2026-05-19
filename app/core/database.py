"""OSINT Intelligence Suite — database.py — Unified database untuk semua modul"""
import sqlite3, os, json
import pandas as pd
from datetime import datetime, timezone
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def ensure_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword     TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            module      TEXT DEFAULT 'person',
            total_hits  INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS articles (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER NOT NULL,
            title           TEXT,
            description     TEXT,
            content         TEXT,
            source          TEXT,
            url             TEXT,
            published_at    TEXT,
            sentiment       REAL DEFAULT 0.0,
            hoax_score      REAL DEFAULT 0.0,
            hate_score      REAL DEFAULT 0.0,
            provok_score    REAL DEFAULT 0.0,
            threat_score    REAL DEFAULT 0.0,
            threat_dominant TEXT DEFAULT 'NORMAL',
            risk_score      REAL DEFAULT 0.0,
            location        TEXT,
            province        TEXT,
            lat             REAL,
            lon             REAL,
            inc_type        TEXT DEFAULT 'LAINNYA',
            severity        REAL DEFAULT 0.0,
            entities        TEXT DEFAULT '[]',
            linked_modules  TEXT DEFAULT '[]',
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );
        CREATE TABLE IF NOT EXISTS article_links (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            module     TEXT NOT NULL,
            score      REAL DEFAULT 0.0,
            label      TEXT,
            detail     TEXT,
            FOREIGN KEY(article_id) REFERENCES articles(id)
        );
        CREATE TABLE IF NOT EXISTS entities (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            text       TEXT,
            label      TEXT,
            count      INTEGER DEFAULT 1,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );
        CREATE TABLE IF NOT EXISTS relations (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            entity_a   TEXT,
            entity_b   TEXT,
            weight     INTEGER DEFAULT 1,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER,
            article_id  INTEGER,
            alert_type  TEXT,
            threat_score REAL,
            message     TEXT,
            created_at  TEXT,
            is_read     INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS narratives (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER NOT NULL,
            label       TEXT,
            keywords    TEXT,
            count       INTEGER DEFAULT 0,
            created_at  TEXT
        );
        CREATE TABLE IF NOT EXISTS monitors (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            module     TEXT NOT NULL,
            keyword    TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS province_stats (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            province   TEXT,
            count      INTEGER DEFAULT 0,
            avg_risk   REAL DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS cross_article_links (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id  INTEGER NOT NULL,
            linked_id   INTEGER NOT NULL,
            link_type   TEXT,
            score       REAL DEFAULT 0.0,
            modules     TEXT DEFAULT '',
            UNIQUE(article_id, linked_id) ON CONFLICT REPLACE,
            FOREIGN KEY(article_id) REFERENCES articles(id),
            FOREIGN KEY(linked_id)  REFERENCES articles(id)
        );
        CREATE TABLE IF NOT EXISTS article_links_cross (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            module     TEXT NOT NULL,
            score      REAL DEFAULT 0.0,
            label      TEXT,
            detail     TEXT
        );
    """)
    conn.commit()
    conn.close()

# ── Session CRUD ──────────────────────────────────────────────────────────────
def create_session(keyword: str, module: str = "person") -> int:
    conn = get_conn()
    now  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cur  = conn.execute(
        "INSERT INTO sessions (keyword, created_at, module) VALUES (?,?,?)",
        (keyword.strip(), now, module)
    )
    sid = cur.lastrowid
    conn.commit(); conn.close()
    return sid

def get_sessions() -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("SELECT * FROM sessions ORDER BY created_at DESC", conn)
        conn.close(); return df
    except Exception: return pd.DataFrame()

def get_session_by_id(sid: int) -> dict:
    try:
        conn = get_conn()
        row  = conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        conn.close()
        if row:
            return {"id":row[0],"keyword":row[1],"created_at":row[2],"module":row[3],"total_hits":row[4]}
        return {}
    except Exception: return {}

def delete_session(sid: int):
    conn = get_conn()
    # Delete cross_article_links for articles in this session
    conn.execute("""
        DELETE FROM cross_article_links WHERE article_id IN
        (SELECT id FROM articles WHERE session_id=?)
    """, (sid,))
    conn.execute("""
        DELETE FROM cross_article_links WHERE linked_id IN
        (SELECT id FROM articles WHERE session_id=?)
    """, (sid,))
    for tbl in ["article_links","alerts","narratives","relations","entities","articles"]:
        conn.execute(f"DELETE FROM {tbl} WHERE {'article_id' if tbl == 'article_links' else 'session_id'}=?",
                     (sid,))
    conn.execute("DELETE FROM sessions WHERE id=?", (sid,))
    conn.commit(); conn.close()

def update_session_hits(sid: int, n: int):
    conn = get_conn()
    conn.execute("UPDATE sessions SET total_hits=total_hits+? WHERE id=?", (n, sid))
    conn.commit(); conn.close()

# ── Article CRUD ──────────────────────────────────────────────────────────────
def save_articles(session_id: int, module_or_articles, articles=None) -> list:
    """Accept both (session_id, articles) and (session_id, module, articles).
    Returns list of saved article IDs."""
    art_list = articles if articles is not None else module_or_articles
    conn = get_conn(); cur = conn.cursor(); saved_ids = []
    for art in art_list:
        try:
            cur.execute("""
                INSERT INTO articles
                (session_id,title,description,content,source,url,published_at,
                 sentiment,hoax_score,hate_score,provok_score,threat_score,
                 threat_dominant,risk_score,location,province,lat,lon,
                 inc_type,severity,entities,linked_modules)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                session_id,
                art.get("title",""),art.get("description",""),art.get("content",""),
                art.get("source",""),art.get("url",""),art.get("published_at",""),
                art.get("sentiment",0.0),art.get("hoax_score",0.0),
                art.get("hate_score",0.0),art.get("provok_score",0.0),
                art.get("threat_score",0.0),art.get("threat_dominant","NORMAL"),
                art.get("risk_score",0.0),art.get("location",""),
                art.get("province",""),art.get("lat",0.0),art.get("lon",0.0),
                art.get("inc_type","LAINNYA"),art.get("severity",0.0),
                json.dumps(art.get("entities",[])),
                json.dumps(art.get("linked_modules",[])),
            ))
            saved_ids.append(cur.lastrowid)
        except Exception: continue
    conn.commit(); conn.close()
    update_session_hits(session_id, len(saved_ids))
    return saved_ids

def load_articles(session_id: int) -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql(
            "SELECT * FROM articles WHERE session_id=? ORDER BY published_at DESC",
            conn, params=(session_id,))
        conn.close()
        df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
        return df
    except Exception: return pd.DataFrame()

def load_articles_by_keyword(keyword: str) -> pd.DataFrame:
    """Load semua artikel dari semua session yang keyword-nya cocok."""
    try:
        conn = get_conn()
        df   = pd.read_sql("""
            SELECT a.*, s.keyword as session_keyword, s.module as session_module
            FROM articles a
            JOIN sessions s ON a.session_id = s.id
            WHERE s.keyword LIKE ?
            ORDER BY a.published_at DESC
        """, conn, params=(f"%{keyword}%",))
        conn.close()
        df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
        return df
    except Exception: return pd.DataFrame()

def load_all_articles() -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("""
            SELECT a.*, s.keyword as session_keyword, s.module as session_module,
                   s.module as module
            FROM articles a JOIN sessions s ON a.session_id=s.id
            ORDER BY a.published_at DESC
        """, conn)
        conn.close()
        df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce")
        return df
    except Exception: return pd.DataFrame()

def update_article_links(article_id: int, linked_modules: list):
    conn = get_conn()
    conn.execute("UPDATE articles SET linked_modules=? WHERE id=?",
                 (json.dumps(linked_modules), article_id))
    conn.commit(); conn.close()

# ── Article Links ─────────────────────────────────────────────────────────────
def save_article_link(article_id, linked_id_or_module, link_type_or_score=None,
                      score_or_label=None, modules_or_detail=None):
    """Two call signatures:
    • Legacy:  save_article_link(article_id, module_str, score, label, detail)
    • Linker:  save_article_link(article_id, linked_id, link_type, score, modules_list)
    """
    conn = get_conn()
    # Detect which signature: linker passes linked_id (int) as 2nd arg
    if isinstance(linked_id_or_module, int):
        linked_id = linked_id_or_module
        link_type = link_type_or_score
        score     = float(score_or_label or 0)
        modules   = modules_or_detail or []
        mod_str   = ",".join(modules) if isinstance(modules, list) else str(modules)
        conn.execute("""
            INSERT INTO cross_article_links
                (article_id, linked_id, link_type, score, modules)
            VALUES (?,?,?,?,?)
        """, (article_id, linked_id, link_type, score, mod_str))
    else:
        # Legacy: (article_id, module, score, label, detail)
        module = linked_id_or_module
        score  = link_type_or_score
        label  = score_or_label
        detail = modules_or_detail
        conn.execute("""
            INSERT OR REPLACE INTO article_links (article_id, module, score, label, detail)
            VALUES (?,?,?,?,?)
        """, (article_id, module, score, label, detail))
    conn.commit(); conn.close()

def load_article_links(article_id: int) -> list:
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT * FROM article_links WHERE article_id=?", (article_id,)
        ).fetchall()
        conn.close()
        return [{"module":r[2],"score":r[3],"label":r[4],"detail":r[5]} for r in rows]
    except Exception: return []

def get_article_links(article_id: int) -> pd.DataFrame:
    """Return cross-article links for one article as a DataFrame.
    Columns: linked_id, linked_module, link_type, score,
             linked_title, linked_source, linked_url,
             hoax_score, hate_score, threat_score, severity, location.
    """
    try:
        conn = get_conn()
        # Cross-article links (from linker)
        try:
            rows = pd.read_sql("""
                SELECT
                    cl.linked_id,
                    cl.link_type,
                    cl.score,
                    cl.modules                      AS modules_str,
                    a.title                         AS linked_title,
                    a.source                        AS linked_source,
                    a.url                           AS linked_url,
                    a.hoax_score,
                    a.hate_score,
                    a.threat_score,
                    a.severity,
                    a.location,
                    s.module                        AS linked_module
                FROM cross_article_links cl
                JOIN articles a  ON cl.linked_id = a.id
                JOIN sessions s  ON a.session_id  = s.id
                WHERE cl.article_id = ?
                ORDER BY cl.score DESC
            """, conn, params=(article_id,))
        except Exception:
            rows = pd.DataFrame()
        conn.close()
        return rows
    except Exception:
        return pd.DataFrame()

def get_article_by_id(article_id: int) -> dict:
    """Return a single article row as a dict, or {} if not found."""
    try:
        conn = get_conn()
        row  = conn.execute(
            "SELECT * FROM articles WHERE id=?", (article_id,)
        ).fetchone()
        conn.close()
        if row is None:
            return {}
        cols = ["id","session_id","title","description","content","source","url",
                "published_at","sentiment","hoax_score","hate_score","provok_score",
                "threat_score","threat_dominant","risk_score","location","province",
                "lat","lon","inc_type","severity","entities","linked_modules"]
        return dict(zip(cols, row))
    except Exception:
        return {}

# ── Entities ──────────────────────────────────────────────────────────────────
def save_entities(session_id: int, entity_counter_or_list, co_occur: dict = None):
    """Accept both (session_id, entity_counter_dict, co_occur_dict)
    and (session_id, entities_list) where entities_list is [{text,label,count}]."""
    conn = get_conn(); cur = conn.cursor()
    conn.execute("DELETE FROM entities WHERE session_id=?", (session_id,))
    conn.execute("DELETE FROM relations WHERE session_id=?", (session_id,))
    if isinstance(entity_counter_or_list, list):
        for ent in entity_counter_or_list[:100]:
            cur.execute("INSERT INTO entities (session_id,text,label,count) VALUES (?,?,?,?)",
                        (session_id, ent.get("text",""), ent.get("label","MISC"), ent.get("count",1)))
    else:
        for (text, label), count in sorted(entity_counter_or_list.items(), key=lambda x: -x[1])[:100]:
            cur.execute("INSERT INTO entities (session_id,text,label,count) VALUES (?,?,?,?)",
                        (session_id, text, label, count))
        if co_occur:
            for (ea, eb), weight in sorted(co_occur.items(), key=lambda x: -x[1])[:50]:
                if ea != eb:
                    cur.execute("INSERT INTO relations (session_id,entity_a,entity_b,weight) VALUES (?,?,?,?)",
                                (session_id, ea, eb, weight))
    conn.commit(); conn.close()

def load_entities(session_id: int) -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("SELECT * FROM entities WHERE session_id=? ORDER BY count DESC",
                           conn, params=(session_id,))
        conn.close(); return df
    except Exception: return pd.DataFrame()

def load_relations(session_id: int) -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql(
            "SELECT * FROM relations WHERE session_id=? AND entity_a!=entity_b ORDER BY weight DESC LIMIT 60",
            conn, params=(session_id,))
        conn.close(); return df
    except Exception: return pd.DataFrame()

# ── Alerts ────────────────────────────────────────────────────────────────────
def save_alert(session_id: int, article_id: int, alert_type: str, threat_score: float, message: str):
    conn = get_conn()
    now  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("INSERT INTO alerts (session_id,article_id,alert_type,threat_score,message,created_at) VALUES (?,?,?,?,?,?)",
                 (session_id, article_id, alert_type, threat_score, message, now))
    conn.commit(); conn.close()

def load_alerts(limit: int = 50) -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql(f"""
            SELECT a.*, s.keyword as session_keyword FROM alerts a
            JOIN sessions s ON a.session_id=s.id
            ORDER BY a.created_at DESC LIMIT {limit}
        """, conn)
        conn.close()
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        return df
    except Exception: return pd.DataFrame()

def count_unread_alerts() -> int:
    try:
        conn = get_conn()
        n    = conn.execute("SELECT COUNT(*) FROM alerts WHERE is_read=0").fetchone()[0]
        conn.close(); return n
    except Exception: return 0

def mark_alerts_read():
    conn = get_conn()
    conn.execute("UPDATE alerts SET is_read=1")
    conn.commit(); conn.close()

# ── Narratives ────────────────────────────────────────────────────────────────
def save_narratives(session_id: int, clusters: list):
    conn = get_conn()
    conn.execute("DELETE FROM narratives WHERE session_id=?", (session_id,))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    for c in clusters:
        conn.execute("INSERT INTO narratives (session_id,label,keywords,count,created_at) VALUES (?,?,?,?,?)",
                     (session_id, c["label"], json.dumps(c.get("keywords",[])), c.get("count",0), now))
    conn.commit(); conn.close()

def load_narratives(session_id: int) -> pd.DataFrame:
    try:
        conn = get_conn()
        df   = pd.read_sql("SELECT * FROM narratives WHERE session_id=? ORDER BY count DESC",
                           conn, params=(session_id,))
        conn.close(); return df
    except Exception: return pd.DataFrame()

# ── Global stats ──────────────────────────────────────────────────────────────
def get_global_stats() -> dict:
    try:
        conn  = get_conn()
        total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        highs = conn.execute("SELECT COUNT(*) FROM articles WHERE threat_score>=60").fetchone()[0]
        hoaxs = conn.execute("SELECT COUNT(*) FROM articles WHERE hoax_score>=50").fetchone()[0]
        locs  = conn.execute("SELECT COUNT(DISTINCT location) FROM articles WHERE location!=''").fetchone()[0]
        sess  = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        unread= conn.execute("SELECT COUNT(*) FROM alerts WHERE is_read=0").fetchone()[0]
        try:
            mon = conn.execute("SELECT COUNT(*) FROM monitors").fetchone()[0]
        except Exception:
            mon = sess
        try:
            links = conn.execute("SELECT COUNT(*) FROM cross_article_links").fetchone()[0]
        except Exception:
            links = 0
        # Per-module stats
        mod_rows = conn.execute(
            "SELECT module, COUNT(*) FROM sessions GROUP BY module"
        ).fetchall()
        mod_s = {r[0]: r[1] for r in mod_rows}
        conn.close()
        return {"total":total,"high_threat":highs,"hoax_count":hoaxs,
                "locations":locs,"sessions":sess,"unread_alerts":unread,
                "monitors":mon,"links":links,"modules":mod_s}
    except Exception:
        return {"total":0,"high_threat":0,"hoax_count":0,"locations":0,
                "sessions":0,"unread_alerts":0,"monitors":0,"links":0,"modules":{}}

# ── Monitor CRUD (alias to sessions with module filter) ───────────────────────
def add_monitor(module: str, keyword: str) -> int:
    """Create a new monitor (= session) for a given module+keyword. Returns monitor ID."""
    conn = get_conn()
    now  = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    cur  = conn.execute(
        "INSERT INTO sessions (keyword, created_at, module) VALUES (?,?,?)",
        (keyword.strip(), now, module)
    )
    mid = cur.lastrowid
    # Also track in monitors table
    conn.execute(
        "INSERT INTO monitors (module, keyword, created_at) VALUES (?,?,?)",
        (module, keyword.strip(), now)
    )
    conn.commit(); conn.close()
    return mid

def get_monitors(module: str) -> "pd.DataFrame":
    """Return all monitors (sessions) for a given module as a DataFrame."""
    try:
        conn = get_conn()
        df   = pd.read_sql(
            "SELECT id, keyword, created_at, total_hits FROM sessions "
            "WHERE module=? ORDER BY created_at DESC",
            conn, params=(module,)
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def delete_monitor(monitor_id: int):
    """Delete a monitor and all its associated data."""
    delete_session(monitor_id)

# ── Relations ─────────────────────────────────────────────────────────────────
def save_relations(session_id: int, relations: list):
    """Save entity relations from a list of {entity_a, entity_b, weight} dicts."""
    conn = get_conn(); cur = conn.cursor()
    conn.execute("DELETE FROM relations WHERE session_id=?", (session_id,))
    for rel in relations[:50]:
        ea = rel.get("entity_a", "")
        eb = rel.get("entity_b", "")
        w  = rel.get("weight", 1)
        if ea and eb and ea != eb:
            cur.execute(
                "INSERT INTO relations (session_id,entity_a,entity_b,weight) VALUES (?,?,?,?)",
                (session_id, ea, eb, w)
            )
    conn.commit(); conn.close()

# ── Province stats (Geo Intel) ────────────────────────────────────────────────
def update_province_stats(session_id: int, df_geo: "pd.DataFrame"):
    """Aggregate and store province-level incident stats for a geo session."""
    if df_geo is None or df_geo.empty:
        return
    try:
        conn = get_conn()
        conn.execute("DELETE FROM province_stats WHERE session_id=?", (session_id,))
        if "province" in df_geo.columns:
            grp = df_geo.groupby("province").agg(
                count=("province", "count"),
                avg_risk=("risk_score", "mean") if "risk_score" in df_geo.columns else ("province", "count")
            ).reset_index()
            for _, row in grp.iterrows():
                conn.execute(
                    "INSERT INTO province_stats (session_id,province,count,avg_risk) VALUES (?,?,?,?)",
                    (session_id, row["province"], int(row["count"]),
                     float(row.get("avg_risk", 0.0)))
                )
        conn.commit(); conn.close()
    except Exception:
        pass

def load_province_stats(session_id: int) -> "pd.DataFrame":
    """Load province stats for a geo session."""
    try:
        conn = get_conn()
        df   = pd.read_sql(
            "SELECT * FROM province_stats WHERE session_id=? ORDER BY count DESC",
            conn, params=(session_id,)
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()
