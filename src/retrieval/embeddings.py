from __future__ import annotations

from functools import lru_cache
import hashlib
import math
import os
import re

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


_MODEL_FAILURES: dict[str, str] = {}


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.dimension = int(os.getenv("FALLBACK_EMBEDDING_DIMENSION", "384"))
        self.model = None
        force_fallback = os.getenv("EMBEDDING_OFFLINE_FALLBACK", "").lower() in {"1", "true", "yes"}
        if not force_fallback and model_name not in _MODEL_FAILURES:
            try:
                self.model = _load_model(model_name)
            except Exception as exc:
                _MODEL_FAILURES[model_name] = f"{type(exc).__name__}: {exc}"
        if self.model is None:
            if os.getenv("REQUIRE_MINILM", "").lower() in {"1", "true", "yes"}:
                reason = _MODEL_FAILURES.get(model_name, "offline fallback was forced")
                raise RuntimeError(f"MiniLM is required but could not be loaded: {reason}")
            self.backend = "local_hashing_fallback"
            self.fallback_reason = _MODEL_FAILURES.get(model_name, "EMBEDDING_OFFLINE_FALLBACK enabled")
        else:
            self.backend = "sentence_transformers"
            self.fallback_reason = None

    def _hash_embed(self, text: str) -> list[float]:
        """Dependency-free signed feature hashing for reproducible offline runs."""
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[\w-]+", text.lower(), flags=re.UNICODE)
        features = tokens + [f"{left}_{right}" for left, right in zip(tokens, tokens[1:], strict=False)]
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.model is None:
            return [self._hash_embed(text) for text in texts]
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        if self.model is None:
            return self._hash_embed(text)
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()
