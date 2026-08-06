from __future__ import annotations

import argparse
from pathlib import Path

from core.config import load_settings, normalized_provider
from retrieval.agent import build_agent, build_agent_tools, run_agent_question
from retrieval.index import LocalEmbeddingIndex


def _console_text(value: str) -> str:
    return value.encode("ascii", errors="backslashreplace").decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test semantic search, exact lookup, and optional RAG agent.")
    parser.add_argument(
        "--query",
        default="agentic retrieval augmented generation diagnostic support",
        help="Semantic search query to run against the local vector index.",
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--embeddings-path", type=Path, default=None)
    parser.add_argument("--agent", action="store_true", help="Also run a live LLM-backed agent question.")
    parser.add_argument(
        "--agent-question",
        default="Which indexed paper discusses diagnostic support for jawbone lesions?",
    )
    args = parser.parse_args()

    settings = load_settings()
    print("Retrieval smoke")
    print(f"- provider: {normalized_provider(settings)}")
    print(f"- model: {settings.model_name}")
    embeddings_path = args.embeddings_path or settings.paths.embeddings_json
    print(f"- embeddings_manifest: {embeddings_path}")

    index = LocalEmbeddingIndex.load(settings, embeddings_path=embeddings_path)
    print(f"- collection_name: {index.collection_name}")
    print(f"- persist_path: {index.persist_path}")
    print(f"- document_count: {len(index.documents)}")

    results = index.search(args.query, top_k=args.top_k)
    print("")
    print("semantic search")
    print(f"- query: {_console_text(args.query)}")
    print(f"- result_count: {len(results)}")
    for rank, result in enumerate(results, start=1):
        print(f"{rank}. {result.paper_id} score={result.score:.4f}")
        print(f"   title={_console_text(result.title)}")

    if not results:
        raise SystemExit("Retrieval smoke failed: semantic search returned no results.")

    first = results[0]
    by_id = index.lookup(first.paper_id)
    by_title = index.lookup(first.title)
    print("")
    print("exact lookup")
    print(f"- by_paper_id: {bool(by_id)}")
    print(f"- by_exact_title: {bool(by_title)}")
    if not by_id or not by_title:
        raise SystemExit("Retrieval smoke failed: exact lookup did not find the top result.")

    tools = {tool.name: tool for tool in build_agent_tools(index)}
    semantic_tool_output = tools["semantic_search_papers"].invoke({"query": args.query, "top_k": 1})
    lookup_tool_output = tools["lookup_paper"].invoke({"paper_id_or_title": first.paper_id})
    print("")
    print("tool output")
    print(f"- semantic_search_papers_has_top_doc: {first.paper_id in semantic_tool_output}")
    print(f"- lookup_paper_has_top_doc: {first.paper_id in lookup_tool_output}")
    print(f"- lookup_paper_has_content: {'Title:' in lookup_tool_output or 'Summary:' in lookup_tool_output}")

    if args.agent:
        print("")
        print("agent")
        agent = build_agent(settings=settings, index=index)
        answer = run_agent_question(agent, args.agent_question)
        print(f"- question: {_console_text(args.agent_question)}")
        print(f"- answer: {_console_text(answer)}")


if __name__ == "__main__":
    main()
