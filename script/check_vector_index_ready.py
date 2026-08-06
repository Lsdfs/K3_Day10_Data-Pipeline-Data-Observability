from __future__ import annotations

import argparse
from pathlib import Path

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex


def _console_text(value: str) -> str:
    return value.encode("ascii", errors="backslashreplace").decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate clean data before building the Chroma vector index.")
    parser.add_argument("--clean-path", type=Path, default=None)
    parser.add_argument("--preview-size", type=int, default=3)
    args = parser.parse_args()

    settings = load_settings()
    clean_path = args.clean_path or settings.paths.clean_csv
    try:
        config = LocalEmbeddingIndex.prepare_config(
            clean_path=clean_path,
            settings=settings,
            preview_size=args.preview_size,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"Vector index preflight failed: {exc}") from exc

    print("Vector index preflight")
    print(f"- clean_path: {config.clean_path}")
    print(f"- manifest_path: {config.manifest_path}")
    print(f"- persist_path: {config.persist_path}")
    print(f"- collection_name: {config.collection_name}")
    print(f"- embedding_model: {config.embedding_model}")
    print(f"- distance_metric: {config.distance_metric}")
    print(f"- document_count: {config.document_count}")
    print(f"- required_columns: {', '.join(config.required_columns)}")
    print(f"- metadata_columns: {', '.join(config.metadata_columns)}")
    print("")
    print("text_for_embedding samples")
    for check in config.text_checks:
        sample = _console_text(check.text_for_embedding[:320].replace("\n", " "))
        print(f"- paper_id={check.paper_id} ok={check.ok} repeated_token_ratio={check.repeated_token_ratio}")
        print(f"  title_present={check.has_title} summary_present={check.has_summary}")
        print(f"  sample={sample}")
    print("")
    print("document payload preview")
    for document in config.preview_documents:
        print(f"- record_id={document['record_id']}")
        print(f"  paper_id={_console_text(document['paper_id'])}")
        print(f"  title={_console_text(document['title'])}")
        print(f"  content_present={bool(document['content'])}")
        print(f"  metadata_keys={', '.join(document['metadata'].keys())}")


if __name__ == "__main__":
    main()
