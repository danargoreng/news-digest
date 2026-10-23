"""Alur utama: ambil RSS -> klasifikasi -> cluster -> ringkas -> simpan."""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from . import db
from .classifier import classify_articles
from .clustering import cluster_articles
from .config import load_config
from .fetcher import fetch_all
from .llm import LLM
from .summarizer import summarize_clusters

log = logging.getLogger(__name__)


def run_pipeline(cfg=None):
    cfg = cfg or load_config()
    tz = ZoneInfo(cfg["pipeline"]["timezone"])
    run_date = datetime.now(tz).strftime("%Y-%m-%d")
    log.info("Mulai pipeline untuk tanggal %s", run_date)

    articles, report = fetch_all(cfg)
    log.info("Total %d artikel unik. Laporan sumber: %s", len(articles), report)
    if not articles:
        log.warning("Tidak ada artikel; pipeline dihentikan (arsip lama tidak diubah).")
        return {"date": run_date, "articles": 0, "clusters": 0, "sources": report}

    llm = LLM(cfg)
    classify_articles(articles, llm, cfg["llm"]["classify_batch_size"])
    clusters = cluster_articles(articles, llm, cfg)
    summarize_clusters(
        clusters,
        llm,
        cfg["llm"]["summary_batch_size"],
        cfg["pipeline"]["max_clusters_summarized"],
    )
    db.save_run(cfg["database"], run_date, clusters)
    log.info("Selesai: %d artikel -> %d cluster", len(articles), len(clusters))
    return {
        "date": run_date,
        "articles": len(articles),
        "clusters": len(clusters),
        "sources": report,
    }
