"""Mengelompokkan artikel yang membahas peristiwa yang sama.

Metode sederhana (greedy):
- embedding: tiap artikel dibandingkan dengan centroid cluster yang ada (cosine similarity).
- judul    : kemiripan kata (Jaccard) pada judul, fallback gratis tanpa API.
"""
import logging
import re
from collections import Counter

import numpy as np

log = logging.getLogger(__name__)

STOPWORDS = set(
    "yang dan di ke dari untuk dengan pada ini itu akan oleh dalam atau tak tidak "
    "ada juga sudah saat usai jadi kata soal the a an of to in on for and at is are "
    "as by with from after over new says say".split()
)


def _tokens(title):
    words = re.findall(r"[a-zA-Z0-9]+", title.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _cluster_by_title(articles, threshold):
    toks = [_tokens(a.title) for a in articles]
    clusters = []  # list of list of index
    for i, t in enumerate(toks):
        best, best_sim = None, 0.0
        for ci, members in enumerate(clusters):
            for j in members:
                union = t | toks[j]
                sim = len(t & toks[j]) / len(union) if union else 0.0
                if sim > best_sim:
                    best, best_sim = ci, sim
        if best is not None and best_sim >= threshold:
            clusters[best].append(i)
        else:
            clusters.append([i])
    return clusters


def _cluster_by_embedding(vectors, threshold):
    vecs = np.array(vectors, dtype=float)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
    clusters, centroids = [], []
    for i, v in enumerate(vecs):
        if centroids:
            sims = np.array(centroids) @ v
            best = int(np.argmax(sims))
            if sims[best] >= threshold:
                clusters[best].append(i)
                c = vecs[clusters[best]].mean(axis=0)
                centroids[best] = c / (np.linalg.norm(c) + 1e-12)
                continue
        clusters.append([i])
        centroids.append(v)
    return clusters


def cluster_articles(articles, llm, cfg):
    """Kembalikan list cluster; tiap cluster berisi artikel + metadata ringkas."""
    ccfg = cfg["clustering"]
    groups = None
    if ccfg["method"] == "embedding" and llm is not None:
        try:
            texts = [f"{a.title}. {a.snippet[:200]}" for a in articles]
            groups = _cluster_by_embedding(llm.embed(texts), ccfg["similarity_threshold"])
        except Exception as e:  # noqa: BLE001
            log.warning("Embedding gagal (%s); pakai metode judul", e)
    if groups is None:
        groups = _cluster_by_title(articles, ccfg["title_threshold"])

    clusters = []
    for idxs in groups:
        arts = [articles[i] for i in idxs]
        cat = Counter(a.category for a in arts).most_common(1)[0][0]
        tag_count = Counter(t for a in arts for t in a.tags)
        clusters.append(
            {
                "articles": arts,
                "category": cat,
                "tags": [t for t, _ in tag_count.most_common(4)],
                "scales": sorted({a.scale for a in arts}),
                "source_count": len({a.source for a in arts}),
                "latest": max(a.published for a in arts),
                "title": arts[0].title,   # diganti judul dari LLM bila ada
                "summary": "",
            }
        )
    # makin banyak media memberitakan = makin penting
    clusters.sort(
        key=lambda c: (c["source_count"], len(c["articles"]), c["latest"]), reverse=True
    )
    return clusters
