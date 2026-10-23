"""Membuat ringkasan netral 2-4 kalimat per cluster (Bahasa Indonesia)."""
import json
import logging
import re

log = logging.getLogger(__name__)

SYSTEM = """Kamu adalah editor berita yang netral. Untuk setiap kelompok berita (beberapa
media membahas peristiwa yang sama), tulis:
- "judul": judul singkat netral dalam Bahasa Indonesia (maks 12 kata).
- "ringkasan": 2 sampai 4 kalimat Bahasa Indonesia.
Aturan ketat:
- Hanya fakta dari judul/snippet yang diberikan. Tanpa opini, tanpa prediksi, tanpa spekulasi.
- Jangan menyebut angka pasar (IHSG, kurs, harga saham, harga komoditas, persentase pergerakan).
- Tulis dengan kalimat sendiri; jangan menyalin kalimat dari sumber.
- Jika sumber tidak sepakat atau informasi belum pasti, katakan secara netral.
- Bahasa baku, tanpa kata sensasional.
Balas HANYA dengan JSON array: [{"id": 0, "judul": "...", "ringkasan": "..."}, ...]"""

MARKET_WORDS = re.compile(
    r"\b(ihsg|rupiah|kurs|saham|indeks|dolar|dollar|emas|harga minyak|bursa|"
    r"stock|shares|nasdaq|dow jones|bitcoin)\b",
    re.IGNORECASE,
)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def sanitize(summary):
    """Buang kalimat yang memuat angka pasar (kata pasar + angka dalam satu kalimat)."""
    kept = []
    for s in SENTENCE_SPLIT.split(summary.strip()):
        if MARKET_WORDS.search(s) and re.search(r"\d", s):
            continue
        kept.append(s)
    return " ".join(kept).strip()


def summarize_clusters(clusters, llm, batch_size=8, max_clusters=120):
    targets = clusters[:max_clusters]
    for start in range(0, len(targets), batch_size):
        chunk = targets[start : start + batch_size]
        payload = []
        for i, c in enumerate(chunk):
            payload.append(
                {
                    "id": i,
                    "artikel": [
                        {"media": a.source, "judul": a.title, "snippet": a.snippet[:200]}
                        for a in c["articles"][:6]
                    ],
                }
            )
        result = llm.chat_json(SYSTEM, json.dumps(payload, ensure_ascii=False))
        if not isinstance(result, list):
            log.warning("Ringkasan batch %d gagal", start)
            continue
        for item in result:
            try:
                c = chunk[int(item["id"])]
            except (KeyError, ValueError, IndexError, TypeError):
                continue
            if item.get("judul"):
                c["title"] = str(item["judul"]).strip()
            summary = sanitize(str(item.get("ringkasan", "")))
            if summary:
                c["summary"] = summary

    for c in clusters:
        if not c["summary"]:
            c["summary"] = "(Ringkasan tidak tersedia. Lihat tautan sumber di bawah.)"
    return clusters
