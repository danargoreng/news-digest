"""Jalankan pipeline sekali (manual atau lewat cron):  python run_pipeline.py"""
import logging

from newsdigest.pipeline import run_pipeline

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    result = run_pipeline()
    print("\nRingkasan proses:")
    print(f"  Tanggal : {result['date']}")
    print(f"  Artikel : {result['articles']}")
    print(f"  Cluster : {result['clusters']}")
    for name, status in result["sources"].items():
        print(f"  - {name}: {status}")
