from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class TextForEmbeddingCheck:
    paper_id: str
    title: str
    text_for_embedding: str
    has_title: bool
    has_summary: bool
    repeated_token_ratio: float
    ok: bool


@dataclass(frozen=True)
class VectorIndexConfig:
    clean_path: Path
    manifest_path: Path
    persist_path: Path
    collection_name: str
    embedding_backend: str
    embedding_model: str
    distance_metric: str
    top_k: int
    document_count: int
    required_columns: list[str]
    metadata_columns: list[str]
    preview_documents: list[dict[str, Any]]
    text_checks: list[TextForEmbeddingCheck]


class LocalEmbeddingIndex:
    REQUIRED_COLUMNS = [
        "paper_id",
        "title",
        "summary",
        "text_for_embedding",
        "published",
        "authors_joined",
        "categories_joined",
        "abs_url",
        "pdf_url",
    ]
    METADATA_COLUMNS = [
        "paper_id",
        "title",
        "published",
        "authors_joined",
        "categories_joined",
        "summary",
        "abs_url",
        "pdf_url",
    ]

    def __init__(
        self,
        settings: Settings,
        collection_name: str,
        documents: list[dict[str, Any]],
        persist_path: Path,
    ):
        self.settings = settings
        self.collection_name = collection_name
        self.documents = documents
        self.persist_path = persist_path
        self.embedding_backend = "chroma"
        self.embedding_model = MiniLMEmbeddings(settings.embedding_model)
        self.client = chromadb.PersistentClient(path=str(persist_path))
        self.collection = self.client.get_collection(name=collection_name)
        self.documents_by_paper_id = {document["paper_id"].lower(): document for document in documents}
        self.documents_by_title = {document["title"].lower(): document for document in documents}

    @staticmethod
    def _clean_text(value: Any) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip()

    @classmethod
    def validate_clean_dataframe(cls, df: pd.DataFrame) -> None:
        missing = [column for column in cls.REQUIRED_COLUMNS if column not in df.columns]
        if missing:
            raise ValueError(f"Clean dataframe is missing required columns: {missing}")
        if df.empty:
            raise ValueError("Clean dataframe is empty; cannot prepare a vector index.")

        blank_failures: dict[str, int] = {}
        for column in ["paper_id", "title", "text_for_embedding"]:
            blank_count = int(df[column].map(lambda value: cls._clean_text(value) == "").sum())
            if blank_count:
                blank_failures[column] = blank_count
        if blank_failures:
            raise ValueError(f"Clean dataframe has blank required text fields: {blank_failures}")

    @classmethod
    def read_clean_dataframe(cls, clean_path: Path) -> pd.DataFrame:
        if not clean_path.exists():
            raise FileNotFoundError(f"Clean data not found: {clean_path}")
        if clean_path.suffix.lower() == ".json":
            df = pd.read_json(clean_path)
        elif clean_path.suffix.lower() == ".csv":
            df = pd.read_csv(clean_path)
        else:
            raise ValueError(f"Unsupported clean data format: {clean_path.suffix}")
        cls.validate_clean_dataframe(df)
        return df

    @classmethod
    def _build_documents(cls, df: pd.DataFrame) -> list[dict[str, Any]]:
        cls.validate_clean_dataframe(df)
        records = df.to_dict(orient="records")
        documents: list[dict[str, Any]] = []
        for index, row in enumerate(records):
            metadata = {column: cls._clean_text(row[column]) for column in cls.METADATA_COLUMNS}
            documents.append(
                {
                    "record_id": f"{metadata['paper_id']}::{index}",
                    "paper_id": metadata["paper_id"],
                    "title": metadata["title"],
                    "content": cls._clean_text(row["text_for_embedding"]),
                    "metadata": metadata,
                }
            )
        return documents

    @staticmethod
    def _derive_collection_name(settings: Settings, embeddings_output_path: Path | None) -> str:
        if embeddings_output_path is None:
            return settings.baseline_collection_name

        name_map = {
            settings.paths.embeddings_json.resolve(): settings.baseline_collection_name,
            settings.paths.corrupted_embeddings_json.resolve(): settings.corrupted_collection_name,
            settings.paths.repaired_embeddings_json.resolve(): settings.repaired_collection_name,
        }
        resolved_path = embeddings_output_path.resolve()
        if resolved_path in name_map:
            return name_map[resolved_path]
        return safe_slug(embeddings_output_path.stem)

    @classmethod
    def inspect_text_for_embedding(cls, df: pd.DataFrame, sample_size: int = 5) -> list[TextForEmbeddingCheck]:
        cls.validate_clean_dataframe(df)
        checks: list[TextForEmbeddingCheck] = []
        for row in df.head(sample_size).to_dict(orient="records"):
            text = cls._clean_text(row["text_for_embedding"])
            title = cls._clean_text(row["title"])
            summary = cls._clean_text(row["summary"])
            tokens = text.lower().split()
            repeated_token_ratio = 0.0 if not tokens else 1.0 - (len(set(tokens)) / len(tokens))
            has_title = title.lower() in text.lower()
            has_summary = bool(summary) and summary[:80].lower() in text.lower()
            checks.append(
                TextForEmbeddingCheck(
                    paper_id=cls._clean_text(row["paper_id"]),
                    title=title,
                    text_for_embedding=text,
                    has_title=has_title,
                    has_summary=has_summary,
                    repeated_token_ratio=round(repeated_token_ratio, 4),
                    ok=has_title and has_summary and repeated_token_ratio < 0.65,
                )
            )
        return checks

    @classmethod
    def prepare_config(
        cls,
        clean_path: Path,
        settings: Settings,
        embeddings_output_path: Path | None = None,
        preview_size: int = 3,
    ) -> VectorIndexConfig:
        df = cls.read_clean_dataframe(clean_path)
        documents = cls._build_documents(df)
        manifest_path = embeddings_output_path or settings.paths.embeddings_json
        return VectorIndexConfig(
            clean_path=clean_path,
            manifest_path=manifest_path,
            persist_path=settings.paths.chroma_dir,
            collection_name=cls._derive_collection_name(settings, manifest_path),
            embedding_backend="chroma",
            embedding_model=settings.embedding_model,
            distance_metric="cosine",
            top_k=settings.top_k,
            document_count=len(documents),
            required_columns=list(cls.REQUIRED_COLUMNS),
            metadata_columns=list(cls.METADATA_COLUMNS),
            preview_documents=documents[:preview_size],
            text_checks=cls.inspect_text_for_embedding(df, sample_size=preview_size),
        )

    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        settings: Settings,
        embeddings_output_path: Path | None = None,
    ) -> "LocalEmbeddingIndex":
        collection_name = cls._derive_collection_name(settings, embeddings_output_path)
        documents = cls._build_documents(df)
        persist_path = settings.paths.chroma_dir
        persist_path.mkdir(parents=True, exist_ok=True)

        embedding_model = MiniLMEmbeddings(settings.embedding_model)
        client = chromadb.PersistentClient(path=str(persist_path))
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass
        collection = client.create_collection(
            name=collection_name,
            configuration={"hnsw": {"space": "cosine"}},
        )
        embeddings = embedding_model.embed_documents([document["content"] for document in documents])
        collection.add(
            ids=[document["record_id"] for document in documents],
            embeddings=embeddings,
            documents=[document["content"] for document in documents],
            metadatas=[document["metadata"] for document in documents],
        )

        manifest_path = embeddings_output_path or settings.paths.embeddings_json
        write_json(
            manifest_path,
            {
                "backend": "chroma",
                "embedding_model": settings.embedding_model,
                "persist_path": str(persist_path),
                "collection_name": collection_name,
                "documents": documents,
            },
        )
        return cls(
            settings=settings,
            collection_name=collection_name,
            documents=documents,
            persist_path=persist_path,
        )

    @classmethod
    def load(cls, settings: Settings, embeddings_path: Path | None = None) -> "LocalEmbeddingIndex":
        payload = read_json(embeddings_path or settings.paths.embeddings_json)
        collection_name = payload["collection_name"]
        candidate_paths = [Path(payload["persist_path"]), settings.paths.chroma_dir]
        last_error: Exception | None = None

        for persist_path in dict.fromkeys(candidate_paths):
            try:
                return cls(
                    settings=settings,
                    collection_name=collection_name,
                    documents=payload["documents"],
                    persist_path=persist_path,
                )
            except Exception as exc:
                last_error = exc

        raise RuntimeError(
            f"Could not load Chroma collection '{collection_name}' from manifest path "
            f"or settings path '{settings.paths.chroma_dir}'."
        ) from last_error

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        query_embedding = self.embedding_model.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k or self.settings.top_k,
            include=["documents", "metadatas", "distances"],
        )
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        scored: list[SearchResult] = []
        for record_id, content, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            if not record_id or not metadata or not content:
                continue
            scored.append(
                SearchResult(
                    paper_id=str(metadata["paper_id"]),
                    title=str(metadata["title"]),
                    score=max(0.0, 1.0 - float(distance or 0.0)),
                    content=str(content),
                    metadata=dict(metadata),
                )
            )
        return scored

    def lookup(self, value: str) -> dict[str, Any] | None:
        needle = value.strip().lower()
        if needle in self.documents_by_paper_id:
            return self.documents_by_paper_id[needle]
        if needle in self.documents_by_title:
            return self.documents_by_title[needle]
        return None
