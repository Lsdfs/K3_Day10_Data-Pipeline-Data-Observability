from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import hashlib
from pathlib import Path
from statistics import mean
import os
import sys
import types
from typing import Any

from pydantic import BaseModel, Field

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json
from retrieval.embeddings import MiniLMEmbeddings
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm
from retrieval.qa import answer_question


class JudgeVerdict(BaseModel):
    score: int = Field(ge=1, le=5)
    correct: bool
    reasoning: str


@dataclass(frozen=True)
class EvaluationBundle:
    summary: dict[str, Any]
    answers: list[dict[str, Any]]


def _token_f1(reference: str, prediction: str) -> float:
    ref_tokens = normalize_whitespace(reference).lower().split()
    pred_tokens = normalize_whitespace(prediction).lower().split()
    if not ref_tokens or not pred_tokens:
        return 0.0
    ref_counts = Counter(ref_tokens)
    pred_counts = Counter(pred_tokens)
    overlap = sum((ref_counts & pred_counts).values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    return 2 * precision * recall / (precision + recall)


def _heuristic_verdict(reference: str, prediction: str, reason: str) -> JudgeVerdict:
    f1 = _token_f1(reference, prediction)
    score = 5 if f1 >= 0.95 else 3 if f1 >= 0.5 else 1
    return JudgeVerdict(score=score, correct=score >= 3, reasoning=reason)


def _judge_answer(
    settings: Settings, question: str, reference: str, prediction: str
) -> tuple[JudgeVerdict, str]:
    prompt = f"""
Evaluate the model answer against the reference answer.

Question: {question}
Reference answer: {reference}
Model answer: {prediction}

Return:
- score from 1 to 5
- correct = true only when the answer is materially correct
- short reasoning
""".strip()
    if os.getenv("ENABLE_LLM_JUDGE", "").lower() not in {"1", "true", "yes"}:
        return _heuristic_verdict(
            reference, prediction, "Deterministic heuristic judge; ENABLE_LLM_JUDGE is disabled."
        ), "heuristic"
    try:
        llm = build_llm(settings=settings, temperature=0.0).with_structured_output(JudgeVerdict)
        return llm.invoke(prompt), "llm"
    except Exception as exc:
        return _heuristic_verdict(
            reference, prediction,
            f"Heuristic fallback because LLM judge was unavailable ({type(exc).__name__}).",
        ), "heuristic_fallback"


def _run_ragas(settings: Settings, answers: list[dict[str, Any]]) -> dict[str, Any]:
    if os.getenv("RUN_RAGAS", "").lower() not in {"1", "true", "yes"}:
        return {"skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."}
    try:
        from datasets import Dataset
        if "langchain_community.chat_models.vertexai" not in sys.modules:
            shim = types.ModuleType("langchain_community.chat_models.vertexai")
            shim.ChatVertexAI = type("ChatVertexAI", (), {})
            sys.modules["langchain_community.chat_models.vertexai"] = shim
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

        dataset = Dataset.from_dict(
            {
                "question": [item["question"] for item in answers],
                "answer": [item["answer"] for item in answers],
                "ground_truth": [item["ground_truth"] for item in answers],
                "contexts": [item["retrieved_contexts"] for item in answers],
            }
        )
        result = evaluate(
            dataset,
            metrics=[answer_relevancy, context_precision, context_recall, faithfulness],
            llm=build_llm(settings=settings, temperature=0.0),
            embeddings=MiniLMEmbeddings(
                settings.embedding_model,
                allow_fallback=settings.allow_embedding_fallback,
                fallback_dimension=settings.fallback_embedding_dimension,
                backend_preference=settings.embedding_backend_preference,
            ),
        )
        return dict(result)
    except Exception as exc:  # pragma: no cover
        return {"error": f"Ragas evaluation failed: {exc}"}


def evaluate_pipeline(
    settings: Settings,
    index: LocalEmbeddingIndex,
    test_set_path,
    metrics_output_path,
    answers_output_path,
) -> EvaluationBundle:
    test_set = read_json(test_set_path)
    if not isinstance(test_set, list) or not test_set:
        raise ValueError("Evaluation test set must be a non-empty JSON list.")
    required = {"id", "question_type", "question", "ground_truth", "ground_truth_doc_ids"}
    ids: set[str] = set()
    for position, item in enumerate(test_set):
        if not isinstance(item, dict) or required - set(item):
            raise ValueError(f"Invalid evaluation item at position {position}.")
        if item["id"] in ids:
            raise ValueError(f"Duplicate evaluation ID: {item['id']}")
        ids.add(item["id"])
    answers: list[dict[str, Any]] = []

    for item in test_set:
        result = answer_question(item["question"], settings=settings, index=index)
        judge, judge_mode = _judge_answer(
            settings, item["question"], item["ground_truth"], result.answer
        )
        retrieval_hit = any(doc_id in item["ground_truth_doc_ids"] for doc_id in result.retrieved_doc_ids)
        answers.append(
            {
                "id": item["id"],
                "question_type": item["question_type"],
                "question": item["question"],
                "ground_truth": item["ground_truth"],
                "ground_truth_doc_ids": item["ground_truth_doc_ids"],
                "answer": result.answer,
                "retrieved_doc_ids": result.retrieved_doc_ids,
                "retrieved_contexts": result.retrieved_contexts,
                "retrieval_hit": retrieval_hit,
                "token_f1": _token_f1(item["ground_truth"], result.answer),
                "judge": judge.model_dump(),
                "judge_mode": judge_mode,
            }
        )

    summary = {
        "samples": len(answers),
        "retrieval_hit_rate": mean(1.0 if item["retrieval_hit"] else 0.0 for item in answers),
        "mean_token_f1": mean(item["token_f1"] for item in answers),
        "judge_accuracy": mean(1.0 if item["judge"]["correct"] else 0.0 for item in answers),
        "mean_judge_score": mean(item["judge"]["score"] for item in answers),
        "judge_mode": sorted({item["judge_mode"] for item in answers}),
        "test_set_sha256": hashlib.sha256(
            Path(test_set_path).read_bytes()
        ).hexdigest(),
    }
    summary["ragas"] = _run_ragas(settings, answers)

    bundle = EvaluationBundle(summary=summary, answers=answers)
    write_json(metrics_output_path, summary)
    write_json(answers_output_path, answers)
    return bundle
