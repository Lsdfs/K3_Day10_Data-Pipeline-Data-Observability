from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import chromadb
import pandas as pd

from core.config import Settings
from core.utils import read_json, safe_slug, write_json
from retrieval.embeddings import MiniLMEmbeddings


@dataclass(frozen=True)
class SearchResult:
    paper_id: str
    title: str
    score: float
    content: str
    metadata: dict[str, Any]


class LocalEmbeddingIndex:
    def __init__(
        self,
        settings: Settings,
        collection_name: str,
        documents: list[dict[str, Any]],
        persist_path: Path,
        embedding_model: MiniLMEmbeddings | None = None,
        backend_preference: str | None = None,
    ):
        self.settings = settings
        self.collection_name = collection_name
        self.documents = documents
        self.persist_path = persist_path
        self.embedding_model = embedding_model or MiniLMEmbeddings(
            settings.embedding_model,
            allow_fallback=settings.allow_embedding_fallback,
            fallback_dimension=settings.fallback_embedding_dimension,
            backend_preference=backend_preference or settings.embedding_backend_preference,
        )
        self.embedding_backend = self.embedding_model.backend
        self.client = chromadb.PersistentClient(path=str(persist_path))
        self.collection = self.client.get_collection(name=collection_name)
        self.documents_by_paper_id = {str(doc["paper_id"]).lower(): doc for doc in documents}
        self.documents_by_title = {str(doc["title"]).lower(): doc for doc in documents}

    @staticmethod
    def _build_documents(df: pd.DataFrame) -> list[dict[str, Any]]:
        required = {
            "paper_id", "title", "text_for_embedding", "published", "authors_joined",
            "categories_joined", "summary", "abs_url", "pdf_url",
        }
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Index dataframe misses columns: {sorted(missing)}")
        if df.empty:
            raise ValueError("Cannot build an embedding index from an empty dataframe.")
        documents = []
        for position, row in enumerate(df.to_dict(orient="records")):
            content = str(row["text_for_embedding"] or "").strip()
            paper_id = str(row["paper_id"] or "").strip()
            title = str(row["title"] or "").strip()
            if not paper_id or not title or not content:
                raise ValueError(f"Index row {position} has empty ID, title or content.")
            metadata = {
                key: str(row.get(key, "") or "")
                for key in [
                    "paper_id", "title", "published", "authors_joined", "categories_joined",
                    "summary", "abs_url", "pdf_url",
                ]
            }
            documents.append({
                "record_id": f"{paper_id}::{position}",
                "paper_id": paper_id,
                "title": title,
                "content": content,
                "metadata": metadata,
            })
        return documents

    @staticmethod
    def _derive_collection_name(settings: Settings, output_path: Path | None) -> str:
        if output_path is None:
            return settings.baseline_collection_name
        mapping = {
            settings.paths.embeddings_json.resolve(): settings.baseline_collection_name,
            settings.paths.corrupted_embeddings_json.resolve(): settings.corrupted_collection_name,
            settings.paths.repaired_embeddings_json.resolve(): settings.repaired_collection_name,
        }
        return mapping.get(output_path.resolve(), safe_slug(output_path.stem))

    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        settings: Settings,
        embeddings_output_path: Path | None = None,
    ) -> "LocalEmbeddingIndex":
        documents = cls._build_documents(df)
        collection_name = cls._derive_collection_name(settings, embeddings_output_path)
        persist_path = settings.paths.chroma_dir
        persist_path.mkdir(parents=True, exist_ok=True)
        model = MiniLMEmbeddings(
            settings.embedding_model,
            allow_fallback=settings.allow_embedding_fallback,
            fallback_dimension=settings.fallback_embedding_dimension,
            backend_preference=settings.embedding_backend_preference,
        )
        embeddings = model.embed_documents([doc["content"] for doc in documents])
        if len(embeddings) != len(documents) or not embeddings or not embeddings[0]:
            raise RuntimeError("Embedding backend returned an invalid matrix.")
        dimension = len(embeddings[0])
        if any(len(vector) != dimension for vector in embeddings):
            raise RuntimeError("Embedding vectors have inconsistent dimensions.")

        client = chromadb.PersistentClient(path=str(persist_path))
        existing_names = {collection.name for collection in client.list_collections()}
        if collection_name in existing_names:
            client.delete_collection(name=collection_name)
        collection = client.create_collection(
            name=collection_name,
            configuration={"hnsw": {"space": "cosine"}},
        )
        collection.add(
            ids=[doc["record_id"] for doc in documents],
            embeddings=embeddings,
            documents=[doc["content"] for doc in documents],
            metadatas=[doc["metadata"] for doc in documents],
        )
        manifest_path = embeddings_output_path or settings.paths.embeddings_json
        write_json(manifest_path, {
            "vector_store": "chroma",
            "embedding_model": settings.embedding_model if model.model is not None else None,
            "embedding_backend": model.backend,
            "embedding_fallback_reason": model.fallback_reason,
            "embedding_dimension": dimension,
            "persist_path": str(persist_path.relative_to(settings.paths.project_dir)),
            "collection_name": collection_name,
            "document_count": len(documents),
            "generated_at": datetime.now(UTC).isoformat(),
            "documents": documents,
        })
        return cls(settings, collection_name, documents, persist_path, embedding_model=model)

    @classmethod
    def load(cls, settings: Settings, embeddings_path: Path | None = None) -> "LocalEmbeddingIndex":
        payload = read_json(embeddings_path or settings.paths.embeddings_json)
        persist_path = Path(payload["persist_path"])
        if not persist_path.is_absolute():
            persist_path = settings.paths.project_dir / persist_path
        backend = payload.get("embedding_backend", "sentence_transformers_minilm")
        preference = "hashing" if backend == "local_hashing_fallback" else "minilm"
        return cls(
            settings,
            payload["collection_name"],
            payload["documents"],
            persist_path,
            backend_preference=preference,
        )

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        query = str(query).strip()
        if not query:
            raise ValueError("Search query cannot be empty.")
        requested = self.settings.top_k if top_k is None else int(top_k)
        if requested <= 0:
            raise ValueError("top_k must be positive.")
        count = self.collection.count()
        if count == 0:
            return []
        query_embedding = self.embedding_model.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(requested, count),
            include=["documents", "metadatas", "distances"],
        )
        scored = []
        for record_id, content, metadata, distance in zip(
            results.get("ids", [[]])[0], results.get("documents", [[]])[0],
            results.get("metadatas", [[]])[0], results.get("distances", [[]])[0], strict=False,
        ):
            if not record_id or metadata is None or content is None:
                continue
            score = max(0.0, min(1.0, 1.0 - float(distance or 0.0)))
            scored.append(SearchResult(
                paper_id=str(metadata["paper_id"]), title=str(metadata["title"]),
                score=score, content=str(content), metadata=dict(metadata),
            ))
        return scored

    def lookup(self, value: str) -> dict[str, Any] | None:
        needle = str(value).strip().lower()
        return self.documents_by_paper_id.get(needle) or self.documents_by_title.get(needle)
