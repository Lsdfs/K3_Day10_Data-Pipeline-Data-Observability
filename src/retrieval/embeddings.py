from __future__ import annotations

from functools import lru_cache
import hashlib
import math
import re

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    """MiniLM embeddings with an explicit, opt-in deterministic offline fallback."""

    def __init__(
        self,
        model_name: str,
        allow_fallback: bool = False,
        fallback_dimension: int = 384,
        backend_preference: str = "minilm",
    ):
        if fallback_dimension <= 0:
            raise ValueError("fallback_dimension must be positive.")
        preference = backend_preference.strip().lower()
        if preference not in {"minilm", "hashing"}:
            raise ValueError("EMBEDDING_BACKEND must be 'minilm' or 'hashing'.")
        if preference == "hashing" and not allow_fallback:
            raise RuntimeError("Hashing embeddings require ALLOW_EMBEDDING_FALLBACK=true.")
        self.model_name = model_name
        self.dimension = fallback_dimension
        self.model: SentenceTransformer | None = None
        self.fallback_reason: str | None = None
        if preference == "hashing":
            self.backend = "local_hashing_fallback"
            self.fallback_reason = "Explicit EMBEDDING_BACKEND=hashing configuration."
            return
        try:
            self.model = _load_model(model_name)
            probe = self.model.get_sentence_embedding_dimension()
            self.dimension = int(probe) if probe else fallback_dimension
            self.backend = "sentence_transformers_minilm"
        except Exception as exc:
            if not allow_fallback:
                raise RuntimeError(
                    "MiniLM could not be loaded and offline fallback is disabled. "
                    "Provide model cache/Internet or set ALLOW_EMBEDDING_FALLBACK=true."
                ) from exc
            self.backend = "local_hashing_fallback"
            self.fallback_reason = f"MiniLM load failed: {type(exc).__name__}"

    def _hash_embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[\w-]+", str(text).lower(), flags=re.UNICODE)
        features = tokens + [f"{left}_{right}" for left, right in zip(tokens, tokens[1:], strict=False)]
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dimension
            vector[bucket] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.model is None:
            return [self._hash_embed(text) for text in texts]
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        if self.model is None:
            return self._hash_embed(text)
        return self.model.encode([text], normalize_embeddings=True)[0].tolist()
