from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, TypeVar

import pandas as pd

from core.config import Paths


LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


class PipelineStageError(RuntimeError):
    pass


def run_stage(name: str, function: Callable[..., T], *args, **kwargs) -> T:
    LOGGER.info("Starting stage: %s", name)
    try:
        result = function(*args, **kwargs)
    except Exception as exc:
        raise PipelineStageError(f"Pipeline stage '{name}' failed: {exc}") from exc
    LOGGER.info("Completed stage: %s", name)
    return result


def ensure_output_directories(paths: Paths) -> None:
    directories = {
        path if path.suffix == "" else path.parent
        for path in paths.__dict__.values()
        if isinstance(path, Path) and path != paths.project_dir and path != paths.workspace_dir
    }
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def dataframe_records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", force_ascii=False))
