from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Paths:
    project_dir: Path
    workspace_dir: Path
    raw_api_response: Path
    raw_records_json: Path
    ingestion_summary: Path
    clean_csv: Path
    clean_json: Path
    chroma_dir: Path
    embeddings_json: Path
    corrupted_clean_csv: Path
    corrupted_clean_json: Path
    corrupted_embeddings_json: Path
    repaired_clean_csv: Path
    repaired_clean_json: Path
    repaired_embeddings_json: Path
    eval_testset: Path
    baseline_metrics: Path
    baseline_answers: Path
    demo_answers: Path
    quality_dir: Path
    gx_dir: Path
    freshness_report: Path
    corrupted_freshness_report: Path
    repaired_freshness_report: Path
    baseline_report: Path
    corruption_log: Path
    corrupted_metrics: Path
    corrupted_answers: Path
    repaired_metrics: Path
    repaired_answers: Path
    comparison_report: Path
    comparison_metrics: Path
    comparison_csv: Path
    comparison_chart: Path
    audit_report: Path


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    model_name: str
    google_api_key: str | None = field(repr=False)
    openai_api_key: str | None = field(repr=False)
    anthropic_api_key: str | None = field(repr=False)
    openrouter_api_key: str | None = field(repr=False)
    openrouter_base_url: str
    ollama_base_url: str
    custom_llm_api_key: str | None = field(repr=False)
    custom_llm_base_url: str | None
    embedding_model: str
    baseline_collection_name: str
    corrupted_collection_name: str
    repaired_collection_name: str
    source_api: str
    source_url: str
    source_query: str
    source_filter: str
    max_results: int
    request_timeout_seconds: float
    request_max_attempts: int
    request_backoff_seconds: float
    top_k: int
    freshness_threshold_days: int
    allow_embedding_fallback: bool
    embedding_backend_preference: str
    fallback_embedding_dimension: int
    corruption_seed: int
    refresh_source: bool
    refresh_test_set: bool
    paths: Paths


def load_settings(project_dir: Path | None = None) -> Settings:
    root = (project_dir or Path(__file__).resolve().parents[2]).resolve()
    workspace = root.parent
    load_dotenv(root / ".env", override=False)

    freshness_threshold_days = int(os.getenv("FRESHNESS_THRESHOLD_DAYS", "180"))
    source_from_date = (datetime.now(UTC).date() - timedelta(days=freshness_threshold_days)).isoformat()
    source_until_date = datetime.now(UTC).date().isoformat()

    data_dir = root / "data"
    paths = Paths(
        project_dir=root,
        workspace_dir=workspace,
        raw_api_response=data_dir / "raw" / "crossref_response.json",
        raw_records_json=data_dir / "raw" / "crossref_records.json",
        ingestion_summary=data_dir / "raw" / "ingestion_summary.json",
        clean_csv=data_dir / "clean" / "papers_clean.csv",
        clean_json=data_dir / "clean" / "papers_clean.json",
        chroma_dir=data_dir / "chroma",
        embeddings_json=data_dir / "embeddings" / "papers_embeddings.json",
        corrupted_clean_csv=data_dir / "clean" / "papers_clean_corrupted.csv",
        corrupted_clean_json=data_dir / "clean" / "papers_clean_corrupted.json",
        corrupted_embeddings_json=data_dir / "embeddings" / "papers_embeddings_corrupted.json",
        repaired_clean_csv=data_dir / "clean" / "papers_clean_repaired.csv",
        repaired_clean_json=data_dir / "clean" / "papers_clean_repaired.json",
        repaired_embeddings_json=data_dir / "embeddings" / "papers_embeddings_repaired.json",
        eval_testset=data_dir / "eval" / "test_set.json",
        baseline_metrics=data_dir / "results" / "baseline_metrics.json",
        baseline_answers=data_dir / "results" / "baseline_answers.json",
        demo_answers=data_dir / "results" / "agent_demo_answers.json",
        quality_dir=data_dir / "quality",
        gx_dir=data_dir / "quality" / "gx",
        freshness_report=data_dir / "quality" / "freshness_report.json",
        corrupted_freshness_report=data_dir / "quality" / "corrupted_freshness.json",
        repaired_freshness_report=data_dir / "quality" / "repaired_freshness.json",
        baseline_report=data_dir / "reports" / "phase1_report.md",
        corruption_log=data_dir / "results" / "corruption_log.json",
        corrupted_metrics=data_dir / "results" / "corrupted_metrics.json",
        corrupted_answers=data_dir / "results" / "corrupted_answers.json",
        repaired_metrics=data_dir / "results" / "repaired_metrics.json",
        repaired_answers=data_dir / "results" / "repaired_answers.json",
        comparison_report=data_dir / "reports" / "corruption_report.md",
        comparison_metrics=data_dir / "results" / "comparison_metrics.json",
        comparison_csv=data_dir / "reports" / "metrics_comparison.csv",
        comparison_chart=data_dir / "reports" / "metrics_comparison.svg",
        audit_report=data_dir / "reports" / "audit_report.json",
    )

    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "gemini"),
        model_name=os.getenv("LLM_MODEL", "gemini-2.5-flash"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        custom_llm_api_key=os.getenv("CUSTOM_LLM_API_KEY"),
        custom_llm_base_url=os.getenv("CUSTOM_LLM_BASE_URL"),
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        baseline_collection_name="papers-baseline",
        corrupted_collection_name="papers-corrupted",
        repaired_collection_name="papers-repaired",
        source_api="Crossref REST API",
        source_url=os.getenv("CROSSREF_API_URL", "https://api.crossref.org/works"),
        source_query=os.getenv("SOURCE_QUERY", "agentic retrieval augmented generation large language model"),
        source_filter=os.getenv(
            "SOURCE_FILTER",
            f"from-pub-date:{source_from_date},until-pub-date:{source_until_date},has-abstract:true",
        ),
        max_results=int(os.getenv("MAX_RESULTS", "24")),
        request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20")),
        request_max_attempts=int(os.getenv("REQUEST_MAX_ATTEMPTS", "4")),
        request_backoff_seconds=float(os.getenv("REQUEST_BACKOFF_SECONDS", "1")),
        top_k=int(os.getenv("TOP_K", "4")),
        freshness_threshold_days=freshness_threshold_days,
        allow_embedding_fallback=os.getenv("ALLOW_EMBEDDING_FALLBACK", "").lower() in {"1", "true", "yes"},
        embedding_backend_preference=os.getenv("EMBEDDING_BACKEND", "minilm").strip().lower(),
        fallback_embedding_dimension=int(os.getenv("FALLBACK_EMBEDDING_DIMENSION", "384")),
        corruption_seed=int(os.getenv("CORRUPTION_SEED", "2026")),
        refresh_source=os.getenv("REFRESH_SOURCE", "").lower() in {"1", "true", "yes"},
        refresh_test_set=os.getenv("REFRESH_TEST_SET", "").lower() in {"1", "true", "yes"},
        paths=paths,
    )


def normalized_provider(settings: Settings) -> str:
    provider = settings.llm_provider.strip().lower().replace(" ", "").replace("-", "")
    if provider == "anthorpic":
        return "anthropic"
    if provider == "customllm":
        return "custom"
    return provider


def require_llm_credentials(settings: Settings) -> None:
    provider = normalized_provider(settings)
    if provider == "gemini":
        if settings.google_api_key:
            return
        raise RuntimeError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini.")
    if provider == "openai":
        if settings.openai_api_key:
            return
        raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
    if provider == "anthropic":
        if settings.anthropic_api_key:
            return
        raise RuntimeError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic.")
    if provider == "openrouter":
        if settings.openrouter_api_key:
            return
        raise RuntimeError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter.")
    if provider == "ollama":
        return
    if provider == "custom":
        if settings.custom_llm_base_url:
            return
        raise RuntimeError("CUSTOM_LLM_BASE_URL is required when LLM_PROVIDER=custom.")
    raise RuntimeError(
        "Unsupported LLM_PROVIDER. Expected one of: openai, gemini, anthropic, openrouter, ollama, custom."
    )
