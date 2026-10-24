"""
Ask the unified regulatory RAG.

Examples:
    python ask_reglementaire.py "Quels sont les pouvoirs de l'AMMC ?" --context-only
    python ask_reglementaire.py "Quels sont les pouvoirs de l'AMMC ?"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

RAG_DIR = Path(__file__).resolve().parent
if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from agent import Agent
from embedder import Embedder
from llm_client import LLMClient
from rag_config import RAGConfig
from retriever import Retriever
from vector_store import VectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the unified regulatory RAG.")
    parser.add_argument("question")
    parser.add_argument("--context-only", action="store_true", help="Print retrieved context without calling the LLM.")
    parser.add_argument("--sources-json", action="store_true", help="Print sources as JSON.")
    parser.add_argument("--top-k", type=int, default=None, help="Override vector/BM25 result count.")
    args = parser.parse_args()

    cfg = RAGConfig()
    embedder = Embedder(cfg.embedding_model, cfg.embedding_fp16, cfg.embedding_batch_size)
    store = VectorStore(cfg.chroma_dir, cfg.collection_name, embedder)
    retriever = Retriever(store, embedder, args.top_k or cfg.n_results)

    chunks = retriever.retrieve(args.question)
    if args.context_only:
        print(retriever.format_context(chunks))
        if args.sources_json:
            print("\nSOURCES_JSON:")
            print(json.dumps(retriever.format_sources(chunks), ensure_ascii=False, indent=2))
        return

    api_key = cfg.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("OPENROUTER_API_KEY manquant. Relance avec --context-only ou configure la cle LLM.")
        print("\nContexte recupere:")
        print(retriever.format_context(chunks))
        return

    llm = LLMClient(
        api_key=api_key,
        model=cfg.llm_model,
        max_tokens=cfg.llm_max_tokens,
        temperature=cfg.llm_temperature,
    )
    agent = Agent(retriever, llm)
    result = agent.chat_with_sources(args.question)
    print(result["answer"])
    print("\nSources:")
    for source in result["sources"]:
        page = ""
        if source.get("page_start"):
            page = f" p.{source['page_start']}"
            if source.get("page_end") and source["page_end"] != source["page_start"]:
                page = f" pp.{source['page_start']}-{source['page_end']}"
        print(f"- [{source['label']}] {source['source_label']} | {source.get('reference_id') or ''}{page}")
        print(f"  {source.get('hierarchy') or source.get('document')}")


if __name__ == "__main__":
    main()
