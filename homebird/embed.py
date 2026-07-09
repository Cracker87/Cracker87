"""Embeddings for semantic search.

Two backends:
  * OllamaEmbedder  — real embeddings from a local Ollama server (Mac).
  * HashEmbedder    — dependency-free signed feature hashing; always works.

Both produce L2-normalized float vectors so cosine similarity is a dot
product. The store records which backend produced each vector; mixing is
prevented by re-embedding on backend change.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
import urllib.request

DIM = 384

_TOKEN = re.compile(r"[a-z0-9]{2,}")


def _tokens(text: str) -> list[str]:
    toks = _TOKEN.findall(text.lower())
    # add bigrams for a little word-order signal
    return toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]


class HashEmbedder:
    name = "hash-v1"
    dim = DIM

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in _tokens(text):
            h = hashlib.blake2b(tok.encode(), digest_size=8).digest()
            idx = int.from_bytes(h[:4], "little") % self.dim
            sign = 1.0 if h[4] & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class OllamaEmbedder:
    def __init__(self, model: str = "nomic-embed-text",
                 base_url: str = "http://127.0.0.1:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.name = f"ollama:{model}"
        self.dim = None  # discovered on first call

    def embed(self, text: str) -> list[float]:
        req = urllib.request.Request(
            f"{self.base_url}/api/embeddings",
            data=json.dumps({"model": self.model, "prompt": text}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            vec = json.loads(resp.read())["embedding"]
        self.dim = len(vec)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def pack(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def unpack(blob: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(blob) // 4}f", blob))


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def ollama_available(base_url: str = "http://127.0.0.1:11434") -> bool:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/tags",
                                    timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def default_embedder():
    if ollama_available():
        return OllamaEmbedder()
    return HashEmbedder()
