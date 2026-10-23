"""Penyimpanan SQLite. Arsip per tanggal lewat kolom run_date (YYYY-MM-DD, WIB)."""
import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    category TEXT,
    tags TEXT,              -- JSON list
    scales TEXT,            -- contoh: "nasional,internasional"
    source_count INTEGER,
    article_count INTEGER,
    rank INTEGER
);
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_id INTEGER NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    run_date TEXT NOT NULL,
    source TEXT,
    scale TEXT,
    title TEXT,
    link TEXT,
    published_at TEXT,
    category TEXT,
    tags TEXT               -- JSON list
);
CREATE INDEX IF NOT EXISTS idx_clusters_date ON clusters(run_date);
CREATE INDEX IF NOT EXISTS idx_articles_cluster ON articles(cluster_id);
"""


def connect(db_path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path):
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def save_run(db_path, run_date, clusters):
    """Simpan hasil satu hari. Jika tanggal sama dijalankan ulang, data lama diganti."""
    init_db(db_path)
    conn = connect(db_path)
    try:
        with conn:
            conn.execute("DELETE FROM articles WHERE run_date = ?", (run_date,))
            conn.execute("DELETE FROM clusters WHERE run_date = ?", (run_date,))
            for rank, c in enumerate(clusters, start=1):
                cur = conn.execute(
                    "INSERT INTO clusters (run_date, title, summary, category, tags,"
                    " scales, source_count, article_count, rank)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        run_date, c["title"], c["summary"], c["category"],
                        json.dumps(c["tags"], ensure_ascii=False),
                        ",".join(c["scales"]), c["source_count"],
                        len(c["articles"]), rank,
                    ),
                )
                cid = cur.lastrowid
                for a in c["articles"]:
                    conn.execute(
                        "INSERT INTO articles (cluster_id, run_date, source, scale,"
                        " title, link, published_at, category, tags)"
                        " VALUES (?,?,?,?,?,?,?,?,?)",
                        (
                            cid, run_date, a.source, a.scale, a.title, a.link,
                            a.published.isoformat(), a.category,
                            json.dumps(a.tags, ensure_ascii=False),
                        ),
                    )
    finally:
        conn.close()


def list_dates(db_path):
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT run_date FROM clusters ORDER BY run_date DESC"
        ).fetchall()
    return [r["run_date"] for r in rows]


def query_clusters(db_path, run_date, category=None, scale=None, q=None):
    """Ambil cluster (urut penting) beserta daftar artikelnya, dengan filter opsional."""
    init_db(db_path)
    sql = "SELECT * FROM clusters WHERE run_date = ?"
    params = [run_date]
    if category:
        sql += " AND category = ?"
        params.append(category)
    if scale:
        sql += " AND (',' || scales || ',') LIKE ?"
        params.append(f"%,{scale},%")
    if q:
        like = f"%{q}%"
        sql += (
            " AND (title LIKE ? OR summary LIKE ? OR tags LIKE ? OR EXISTS ("
            "SELECT 1 FROM articles a WHERE a.cluster_id = clusters.id"
            " AND a.title LIKE ?))"
        )
        params += [like, like, like, like]
    sql += " ORDER BY rank ASC"

    with connect(db_path) as conn:
        clusters = [dict(r) for r in conn.execute(sql, params).fetchall()]
        for c in clusters:
            c["tags"] = json.loads(c["tags"] or "[]")
            rows = conn.execute(
                "SELECT source, scale, title, link FROM articles"
                " WHERE cluster_id = ? ORDER BY source",
                (c["id"],),
            ).fetchall()
            c["articles"] = [dict(r) for r in rows]
    return clusters
