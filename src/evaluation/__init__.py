"""Evaluation helpers with lightweight imports for test-set generation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .testset import build_test_set

if TYPE_CHECKING:
    from .metrics import EvaluationBundle, JudgeVerdict, evaluate_pipeline

__all__ = ["build_test_set", "EvaluationBundle", "JudgeVerdict", "evaluate_pipeline"]


def __getattr__(name: str):
    if name in {"EvaluationBundle", "JudgeVerdict", "evaluate_pipeline"}:
        from .metrics import EvaluationBundle, JudgeVerdict, evaluate_pipeline

        return {
            "EvaluationBundle": EvaluationBundle,
            "JudgeVerdict": JudgeVerdict,
            "evaluate_pipeline": evaluate_pipeline,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
