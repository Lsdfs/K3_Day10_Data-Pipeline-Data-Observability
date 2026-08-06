from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

# Keep downloaded model files inside the project-local, ignored downloads
# directory when the caller has not configured a shared Hugging Face cache.
# This makes the retrieval smoke checks work on Windows profiles where the
# default user cache is not writable.
os.environ.setdefault(
    "HF_HOME",
    str(Path(__file__).resolve().parents[2] / ".downloads" / "huggingface"),
)

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = _load_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()
