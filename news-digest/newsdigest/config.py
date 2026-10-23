"""Memuat config.yaml dan .env."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
CATEGORIES = [
    "Ekonomi & Bisnis",
    "Politik & Pemerintahan",
    "Konflik & Keamanan",
    "Hukum & Kriminal",
    "Bencana & Lingkungan",
    "Teknologi",
    "Kesehatan",
    "Olahraga",
    "Hiburan",
    "Lainnya",
]
SCALES = ("nasional", "internasional")


def load_config(path=None):
    load_dotenv(BASE_DIR / ".env")
    path = Path(path) if path else BASE_DIR / "config.yaml"
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    for src in cfg.get("sources", []):
        if not src.get("name") or not src.get("url"):
            raise ValueError(f"Sumber tidak valid (butuh name & url): {src}")
        if src.get("scale") not in SCALES:
            raise ValueError(
                f"Sumber '{src['name']}': scale harus 'nasional' atau 'internasional'"
            )

    db = Path(cfg.get("database", "data/news.db"))
    cfg["database"] = str(db if db.is_absolute() else BASE_DIR / db)
    return cfg
