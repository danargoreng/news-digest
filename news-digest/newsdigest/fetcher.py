"""Mengambil artikel dari RSS (hanya judul + link + snippet pendek)."""
import calendar
import html
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import feedparser
import requests

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (compatible; NewsDigestPrototype/1.0)"
TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Article:
    source: str
    scale: str
    title: str
    link: str
    snippet: str          # hanya dipakai di memori untuk LLM, TIDAK disimpan ke DB
    published: datetime
    category: str = "Lainnya"
    tags: list = field(default_factory=list)


def clean_text(text, limit=300):
    text = html.unescape(TAG_RE.sub(" ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _entry_time(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
    return None


def fetch_source(src, cutoff, max_items, timeout):
    resp = requests.get(src["url"], timeout=timeout, headers={"User-Agent": UA})
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)

    articles = []
    suffix = f" - {src['name']}"
    for entry in feed.entries:
        title = clean_text(entry.get("title"), 300)
        link = entry.get("link", "").strip()
        if not title or not link:
            continue
        if title.endswith(suffix):  # Google News menambahkan " - Reuters"
            title = title[: -len(suffix)]
        published = _entry_time(entry) or datetime.now(timezone.utc)
        if published < cutoff:
            continue
        snippet = clean_text(entry.get("summary") or entry.get("description"), 300)
        if snippet.lower().startswith(title.lower()[:40]) and len(snippet) < len(title) + 40:
            snippet = ""  # snippet cuma mengulang judul (umum di Google News)
        articles.append(
            Article(src["name"], src["scale"], title, link, snippet, published)
        )
    articles.sort(key=lambda a: a.published, reverse=True)
    return articles[:max_items]


def fetch_all(cfg):
    """Ambil semua sumber. Error di satu sumber tidak menghentikan yang lain."""
    pcfg = cfg["pipeline"]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=pcfg["hours_back"])
    all_articles, report = [], {}
    for src in cfg["sources"]:
        try:
            items = fetch_source(
                src, cutoff, pcfg["max_articles_per_source"], pcfg["request_timeout"]
            )
            all_articles.extend(items)
            report[src["name"]] = len(items)
            log.info("%s: %d artikel", src["name"], len(items))
        except Exception as e:  # noqa: BLE001 - sengaja menangkap semua
            report[src["name"]] = f"GAGAL ({type(e).__name__}: {e})"
            log.warning("Sumber %s gagal: %s", src["name"], e)

    # buang duplikat (link sama atau judul sama persis)
    seen, unique = set(), []
    for a in all_articles:
        keys = (a.link, (a.source, a.title.lower()))
        if any(k in seen for k in keys):
            continue
        seen.update(keys)
        unique.append(a)
    return unique, report
