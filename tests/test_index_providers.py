from __future__ import annotations

from dataclasses import replace

import pytest

from core.config import require_llm_credentials
from retrieval.index import LocalEmbeddingIndex


def test_chroma_build_load_search_and_top_k_bound(clean_df, settings):
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    assert index.embedding_backend == "local_hashing_fallback"
    assert index.lookup(clean_df.iloc[0].paper_id)["title"] == clean_df.iloc[0].title
    assert len(index.search("retrieval", top_k=999)) == len(clean_df)
    loaded = LocalEmbeddingIndex.load(settings)
    assert loaded.collection_name == settings.baseline_collection_name
    with pytest.raises(ValueError):
        index.search("", top_k=1)


@pytest.mark.parametrize(
    ("provider", "field", "value"),
    [
        ("gemini", "google_api_key", "test"), ("openai", "openai_api_key", "test"),
        ("anthropic", "anthropic_api_key", "test"), ("openrouter", "openrouter_api_key", "test"),
        ("custom", "custom_llm_base_url", "http://localhost:9000/v1"),
    ],
)
def test_provider_validation_offline(settings, provider, field, value):
    require_llm_credentials(replace(settings, llm_provider=provider, **{field: value}))
    with pytest.raises(RuntimeError):
        require_llm_credentials(replace(settings, llm_provider=provider, **{field: None}))
    require_llm_credentials(replace(settings, llm_provider="ollama"))
