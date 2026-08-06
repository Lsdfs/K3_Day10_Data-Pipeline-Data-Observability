"""Retrieval components exposed without eagerly loading the LLM stack."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .embeddings import MiniLMEmbeddings
from .index import LocalEmbeddingIndex, SearchResult, TextForEmbeddingCheck, VectorIndexConfig
from .qa import AnswerResult, answer_question

if TYPE_CHECKING:
    from .agent import build_agent, build_agent_tools, run_agent_question
    from .llm import build_llm

__all__ = [
    "AnswerResult",
    "LocalEmbeddingIndex",
    "MiniLMEmbeddings",
    "SearchResult",
    "TextForEmbeddingCheck",
    "VectorIndexConfig",
    "answer_question",
    "build_agent",
    "build_agent_tools",
    "build_llm",
    "run_agent_question",
]


def __getattr__(name: str):
    if name in {"build_agent", "build_agent_tools", "run_agent_question"}:
        from .agent import build_agent, build_agent_tools, run_agent_question

        return {
            "build_agent": build_agent,
            "build_agent_tools": build_agent_tools,
            "run_agent_question": run_agent_question,
        }[name]
    if name == "build_llm":
        from .llm import build_llm

        return build_llm
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
