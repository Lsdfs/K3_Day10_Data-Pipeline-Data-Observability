from __future__ import annotations

from dataclasses import dataclass
import re

from core.config import Settings
from core.utils import first_sentence
from retrieval.index import LocalEmbeddingIndex, SearchResult


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    retrieved_doc_ids: list[str]
    retrieved_contexts: list[str]
    retrieved_titles: list[str]


def _extract_answer(question: str, top_result: SearchResult) -> str:
    lowered = question.lower()
    metadata = top_result.metadata
    if "who authored" in lowered or "list the authors" in lowered:
        return str(metadata.get("authors_joined") or "Unknown")
    if "when was" in lowered or "publication date" in lowered or "published on" in lowered:
        return str(metadata.get("published") or "Unknown")
    if "what categories" in lowered:
        return str(metadata.get("categories_joined") or "Unknown")
    summary = str(metadata.get("summary") or "")
    return first_sentence(summary) if summary.strip() else "I don't know from the indexed corpus."


def answer_question(question: str, settings: Settings, index: LocalEmbeddingIndex, top_k: int | None = None) -> AnswerResult:
    title_match = re.search(r"'([^']+)'", question)
    doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", question, flags=re.IGNORECASE)
    lookup_value = title_match.group(1) if title_match else doi_match.group(0) if doi_match else None
    exact = index.lookup(lookup_value) if lookup_value else None
    retrieved = index.search(question, top_k=top_k)
    if exact:
        exact_result = SearchResult(
            paper_id=exact["paper_id"],
            title=exact["title"],
            score=1.0,
            content=exact["content"],
            metadata=exact["metadata"],
        )
        deduped = [exact_result] + [item for item in retrieved if item.paper_id != exact_result.paper_id]
        retrieved = deduped[: (top_k or settings.top_k)]
    if not retrieved:
        answer = "I don't know from the indexed corpus."
    else:
        answer = _extract_answer(question, retrieved[0])
    return AnswerResult(
        question=question,
        answer=answer,
        retrieved_doc_ids=[item.paper_id for item in retrieved],
        retrieved_contexts=[item.content for item in retrieved],
        retrieved_titles=[item.title for item in retrieved],
    )
