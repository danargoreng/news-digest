"""Memberi kategori + tag pada artikel (batch, hanya judul + snippet)."""
import json
import logging

from .config import CATEGORIES

log = logging.getLogger(__name__)

SYSTEM = f"""Kamu adalah editor berita. Untuk setiap artikel, tentukan:
1. "kategori": TEPAT SATU dari daftar ini: {", ".join(CATEGORIES)}.
   Gunakan "Lainnya" hanya jika tidak ada yang cocok.
2. "tag": 2 sampai 4 tag singkat (1-3 kata), contoh: IHSG, demo, Prancis, Bitcoin.
   Tag berupa nama tokoh/organisasi/tempat/topik utama, bukan kalimat.
Balas HANYA dengan JSON array, satu objek per artikel:
[{{"i": 0, "kategori": "...", "tag": ["...", "..."]}}, ...]
"i" adalah nomor artikel pada input."""


def _clean_tags(tags):
    out = []
    for t in tags or []:
        t = str(t).strip().strip("#")
        if t and t.lower() not in [x.lower() for x in out]:
            out.append(t[:30])
    return out[:4]


def classify_articles(articles, llm, batch_size=25):
    for start in range(0, len(articles), batch_size):
        chunk = articles[start : start + batch_size]
        payload = [
            {"i": i, "judul": a.title, "snippet": a.snippet[:200]}
            for i, a in enumerate(chunk)
        ]
        result = llm.chat_json(SYSTEM, json.dumps(payload, ensure_ascii=False))
        if not isinstance(result, list):
            log.warning("Klasifikasi batch %d gagal; dipakai 'Lainnya'", start)
            continue
        for item in result:
            try:
                art = chunk[int(item["i"])]
            except (KeyError, ValueError, IndexError, TypeError):
                continue
            cat = item.get("kategori")
            art.category = cat if cat in CATEGORIES else "Lainnya"
            art.tags = _clean_tags(item.get("tag"))
    return articles
