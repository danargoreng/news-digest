"""Web Flask + penjadwal harian (APScheduler).  Jalankan:  python app.py"""
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, render_template, request

from newsdigest import db
from newsdigest.config import CATEGORIES, SCALES, load_config
from newsdigest.pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("app")

cfg = load_config()
app = Flask(__name__)
db.init_db(cfg["database"])


@app.route("/")
def index():
    dates = db.list_dates(cfg["database"])
    date = request.args.get("tanggal") or (dates[0] if dates else None)
    category = request.args.get("kategori") or None
    scale = request.args.get("skala") or None
    q = (request.args.get("q") or "").strip() or None

    clusters = []
    if date:
        clusters = db.query_clusters(cfg["database"], date, category, scale, q)
    return render_template(
        "index.html",
        clusters=clusters,
        dates=dates,
        date=date,
        categories=CATEGORIES,
        scales=SCALES,
        sel_category=category,
        sel_scale=scale,
        q=q or "",
    )


def scheduled_job():
    try:
        run_pipeline(cfg)
    except Exception:  # noqa: BLE001 - jangan sampai scheduler mati
        log.exception("Pipeline terjadwal gagal")


def start_scheduler():
    p = cfg["pipeline"]
    sched = BackgroundScheduler(timezone=p["timezone"])
    sched.add_job(
        scheduled_job,
        CronTrigger(hour=p["schedule_hour"], minute=p["schedule_minute"],
                    timezone=p["timezone"]),
        id="daily_digest",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    sched.start()
    log.info("Penjadwal aktif: setiap hari %02d:%02d %s",
             p["schedule_hour"], p["schedule_minute"], p["timezone"])
    return sched


if __name__ == "__main__":
    if os.getenv("DISABLE_SCHEDULER") != "1":
        start_scheduler()
    # use_reloader=False agar penjadwal tidak berjalan dobel
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
