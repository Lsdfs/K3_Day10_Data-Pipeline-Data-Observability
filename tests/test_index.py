from __future__ import annotations

import hashlib

from retrieval.index import LocalEmbeddingIndex


class FakeEmbeddings:
    def __init__(self, model_name):
        self.model_name = model_name

    @staticmethod
    def _embed(text):
        digest = hashlib.sha256(text.lower().encode()).digest()
        return [byte / 255 for byte in digest[:16]]

    def embed_documents(self, texts):
        return [self._embed(text) for text in texts]

    def embed_query(self, text):
        return self._embed(text)


def test_chroma_index_build_load_search_and_lookup(monkeypatch, clean_df, settings):
    monkeypatch.setattr("retrieval.index.MiniLMEmbeddings", FakeEmbeddings)
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    assert index.lookup(clean_df.iloc[0]["paper_id"])["title"] == clean_df.iloc[0]["title"]
    assert len(index.search("retrieval", top_k=3)) == 3
    loaded = LocalEmbeddingIndex.load(settings)
    assert loaded.collection_name == settings.baseline_collection_name
