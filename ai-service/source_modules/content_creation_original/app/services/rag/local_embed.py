"""Offline hashed embeddings (384-dim) — honest fallback used when the Gemini
embedding endpoint is unavailable. Deterministic, no network."""
from __future__ import annotations

import hashlib
import math
import re

DIM = 384
_TOKEN = re.compile(r"[a-z0-9\u0600-\u06FF_]+")


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def hash_embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    tokens = _TOKEN.findall(text.lower())
    grams = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    for gram in grams:
        digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "little") % DIM
        vec[index] += 1.0 if digest[4] & 1 else -1.0
    return _normalize(vec)


def hash_embed_many(texts: list[str]) -> list[list[float]]:
    return [hash_embed(t) for t in texts]