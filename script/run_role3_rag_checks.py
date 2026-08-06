from __future__ import annotations

import argparse
from pathlib import Path

import chromadb

from core.config import load_settings
from core.utils import read_json
from retrieval.agent import build_agent, build_agent_tools, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def _console_text(value: str) -> str:
    return value.encode("ascii", errors="backslashreplace").decode("ascii")


def _variant_paths(settings):
    return {
        "baseline": (settings.paths.clean_csv, settings.paths.embeddings_json),
        "corrupted": (settings.paths.corrupted_clean_csv, settings.paths.corrupted_embeddings_json),
        "repaired": (settings.paths.repaired_clean_csv, settings.paths.repaired_embeddings_json),
    }


def _manifest_matches_dataset(clean_path: Path, manifest_path: Path) -> bool:
    df = LocalEmbeddingIndex.read_clean_dataframe(clean_path)
    manifest = read_json(manifest_path)
    manifest_ids = {document["paper_id"] for document in manifest["documents"]}
    clean_ids = set(df["paper_id"].map(LocalEmbeddingIndex._clean_text))
    return len(manifest["documents"]) == len(df) and manifest_ids == clean_ids


def _print_samples(settings, preview_size: int) -> None:
    config = LocalEmbeddingIndex.prepare_config(settings.paths.clean_csv, settings, preview_size=preview_size)
    print("1-3. Clean data and vector config")
    print(f"- clean_path: {config.clean_path}")
    print(f"- document_count: {config.document_count}")
    print(f"- collection_name: {config.collection_name}")
    print(f"- embedding_model: {config.embedding_model}")
    print(f"- required_columns: {', '.join(config.required_columns)}")
    print(f"- metadata_columns: {', '.join(config.metadata_columns)}")
    for check in config.text_checks:
        sample = _console_text(check.text_for_embedding[:260].replace("\n", " "))
        print(f"- sample paper_id={check.paper_id} ok={check.ok} repeated_token_ratio={check.repeated_token_ratio}")
        print(f"  title_present={check.has_title} summary_present={check.has_summary}")
        print(f"  text_for_embedding={sample}")


def _build_variant(name: str, clean_path: Path, manifest_path: Path, settings) -> LocalEmbeddingIndex:
    df = LocalEmbeddingIndex.read_clean_dataframe(clean_path)
    index = LocalEmbeddingIndex.build(df=df, settings=settings, embeddings_output_path=manifest_path)
    print(f"- built {name}: collection={index.collection_name} docs={len(index.documents)} manifest={manifest_path}")
    return index


def _search_summary(index: LocalEmbeddingIndex, query: str, top_k: int) -> list[str]:
    results = index.search(query, top_k=top_k)
    lines = []
    for rank, result in enumerate(results, start=1):
        lines.append(f"{rank}. {result.paper_id} score={result.score:.4f} title={_console_text(result.title)}")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Run role 3 RAG/vector index checks.")
    parser.add_argument(
        "--query",
        default="agentic retrieval augmented generation diagnostic support",
        help="Baseline semantic query reused across baseline/corrupted/repaired collections.",
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--preview-size", type=int, default=3)
    parser.add_argument("--agent", action="store_true", help="Run a live LLM agent answer after tool checks.")
    parser.add_argument(
        "--agent-question",
        default="Which indexed paper discusses diagnostic support for jawbone lesions?",
    )
    args = parser.parse_args()

    settings = load_settings()
    _print_samples(settings, args.preview_size)

    print("")
    print("4, 11, 14. Build separate Chroma collections")
    paths = _variant_paths(settings)
    indexes = {
        name: _build_variant(name, clean_path, manifest_path, settings)
        for name, (clean_path, manifest_path) in paths.items()
    }

    print("")
    print("5, 8, 12, 14. Semantic search comparison")
    print(f"- baseline_query: {_console_text(args.query)}")
    baseline_before = _search_summary(indexes["baseline"], args.query, args.top_k)
    for name in ["baseline", "corrupted", "repaired"]:
        print(f"{name}:")
        for line in _search_summary(indexes[name], args.query, args.top_k):
            print(f"  {line}")

    print("")
    print("5, 8. Exact lookup")
    first_baseline = indexes["baseline"].search(args.query, top_k=1)[0]
    for lookup_value in [first_baseline.paper_id, first_baseline.title]:
        record = indexes["baseline"].lookup(lookup_value)
        print(f"- lookup={_console_text(lookup_value[:100])} found={bool(record)}")
        if record:
            print(f"  paper_id={record['paper_id']}")
            print(f"  title={_console_text(record['title'])}")

    print("")
    print("6, 9, 15. Agent tools")
    for name in ["baseline", "repaired"]:
        tools = {tool.name: tool for tool in build_agent_tools(indexes[name])}
        semantic_output = tools["semantic_search_papers"].invoke({"query": args.query, "top_k": 1})
        lookup_output = tools["lookup_paper"].invoke({"paper_id_or_title": first_baseline.paper_id})
        print(f"- {name} semantic_search_papers_has_doc={first_baseline.paper_id in semantic_output}")
        print(f"- {name} lookup_paper_has_doc={first_baseline.paper_id in lookup_output}")
        print(f"- {name} lookup_paper_corpus_bound={'No exact paper match found.' not in lookup_output}")

    if args.agent:
        agent = build_agent(settings=settings, index=indexes["repaired"])
        answer = run_agent_question(agent, args.agent_question)
        print("- live_agent_answer:")
        print(_console_text(answer))

    print("")
    print("7, 13, 16. Manifests and paths")
    collections = chromadb.PersistentClient(path=str(settings.paths.chroma_dir)).list_collections()
    collection_names = [getattr(collection, "name", str(collection)) for collection in collections]
    print(f"- chroma_path: {settings.paths.chroma_dir}")
    print(f"- collections: {collection_names}")
    baseline_after = _search_summary(indexes["baseline"], args.query, args.top_k)
    print(f"- baseline_not_mutated_after_other_builds: {baseline_before == baseline_after}")
    for name, (clean_path, manifest_path) in paths.items():
        manifest = read_json(manifest_path)
        print(f"- {name}: clean={clean_path}")
        print(f"  manifest={manifest_path}")
        print(f"  collection={manifest['collection_name']}")
        print(f"  manifest_matches_clean={_manifest_matches_dataset(clean_path, manifest_path)}")
        print(f"  docs={len(manifest['documents'])}")


if __name__ == "__main__":
    main()
