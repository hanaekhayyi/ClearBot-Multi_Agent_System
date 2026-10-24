"""
Build one clean regulatory vector DB from the two retained corpora.

Retained sources:
- Actualite historique: data/input/jsons/chunks_output.json
- Recueil AMMC Docling: parsing/notebooks/output/legal_chunks.jsonl

Enrichment:
- Recueil AMMC PDF links: parsing/notebooks/output/pdf_links_mapped.jsonl

The two corpora keep their own metadata shape, but are converted to one
Chroma-compatible schema with corpus/chunking_strategy markers.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb

RAG_DIR = Path(__file__).resolve().parent
AGENT_DIR = RAG_DIR.parent
DATA_DIR = AGENT_DIR / "data"

HISTORIQUE_JSON = DATA_DIR / "input" / "jsons" / "chunks_output.json"
AMMC_CHUNKS_JSONL = AGENT_DIR / "parsing" / "notebooks" / "output" / "legal_chunks.jsonl"
AMMC_LINKS_JSONL = AGENT_DIR / "parsing" / "notebooks" / "output" / "pdf_links_mapped.jsonl"

if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from rag_config import RAGConfig  # noqa: E402
from embedder import Embedder  # noqa: E402


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def scalar_metadata(meta: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Chroma accepts only scalar metadata values."""
    clean: dict[str, str | int | float | bool] = {}
    for key, value in meta.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            clean[key] = value
        else:
            clean[key] = json.dumps(value, ensure_ascii=False)
    return clean


def chroma_dir(cfg: RAGConfig) -> Path:
    path = Path(cfg.chroma_dir)
    if not path.is_absolute():
        path = (AGENT_DIR / path).resolve()
    return path


def backup_vectordb(cfg: RAGConfig) -> Path | None:
    src = chroma_dir(cfg)
    if not src.exists():
        return None
    backup_root = DATA_DIR / "_backup_cleanup"
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = backup_root / f"vectordb.before_unified_index.{stamp}"
    shutil.copytree(src, dst)
    return dst


def reset_collection(cfg: RAGConfig) -> None:
    path = chroma_dir(cfg)
    path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(path))
    try:
        client.delete_collection(cfg.collection_name)
    except Exception:
        pass
    client.get_or_create_collection(cfg.collection_name)


def get_collection(cfg: RAGConfig):
    path = chroma_dir(cfg)
    path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(path))
    return client.get_or_create_collection(cfg.collection_name)


def load_historique(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        rows = json.load(f)

    chunks: list[dict[str, Any]] = []
    for row in rows:
        meta = dict(row.get("metadata") or {})
        original_id = row.get("id", "")
        reference_id = meta.get("reference_id", "")
        source = meta.get("source", "")
        hierarchy = " > ".join(
            str(v)
            for v in [source, meta.get("title"), meta.get("chapter"), meta.get("section"), reference_id]
            if v
        )
        meta.update(
            {
                "corpus": "actualite_historique",
                "chunking_strategy": "historique_article_chunking",
                "original_chunk_id": original_id,
                "document": source,
                "hierarchy": hierarchy,
            }
        )
        chunks.append(
            {
                "id": f"historique::{original_id}",
                "content": row.get("content") or "",
                "metadata": scalar_metadata(meta),
            }
        )
    return chunks


def build_ammc_link_indexes(path: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for link in read_jsonl(path):
        source_id = link.get("source_chunk_id")
        target_id = link.get("target_chunk_id")
        compact = {
            "kind": link.get("kind"),
            "source_chunk_id": source_id,
            "target_chunk_id": target_id,
            "target_chunk_name": link.get("target_chunk_name"),
            "source_page": link.get("source_page"),
            "target_page": link.get("target_page"),
            "source_block_ref": link.get("source_block_ref"),
            "target_block_ref": link.get("target_block_ref"),
        }
        if source_id and target_id:
            outgoing[source_id].append(compact)
            incoming[target_id].append(compact)
    return outgoing, incoming


def ammc_reference(row: dict[str, Any]) -> str:
    if row.get("chunk_type") == "article":
        return row.get("article_id") or row.get("chunk_id", "")
    return row.get("annexe") or row.get("section") or row.get("titre") or row.get("chunk_id", "")


def load_ammc_docling(chunks_path: Path, links_path: Path) -> list[dict[str, Any]]:
    rows = read_jsonl(chunks_path)
    outgoing, incoming = build_ammc_link_indexes(links_path)

    chunks: list[dict[str, Any]] = []
    for row in rows:
        chunk_id = row.get("chunk_id")
        if not chunk_id:
            continue

        hierarchy = " > ".join(
            str(v)
            for v in [
                row.get("document"),
                row.get("livre"),
                row.get("titre"),
                row.get("chapitre"),
                row.get("section"),
                row.get("annexe"),
                row.get("article_id") if row.get("chunk_type") == "article" else None,
            ]
            if v
        )

        meta = {
            "corpus": "ammc_recueil_docling",
            "chunking_strategy": "docling_layout_legal_structure",
            "original_chunk_id": chunk_id,
            "source": row.get("document"),
            "document": row.get("document"),
            "reference_id": ammc_reference(row),
            "chunk_type": row.get("chunk_type"),
            "livre": row.get("livre"),
            "title": row.get("titre"),
            "chapter": row.get("chapitre"),
            "section": row.get("section"),
            "annexe": row.get("annexe"),
            "page_start": row.get("page_start"),
            "page_end": row.get("page_end"),
            "hierarchy": hierarchy,
            "footnotes": row.get("footnotes") or [],
            "block_refs": row.get("block_refs") or [],
            "pdf_outgoing_links": outgoing.get(chunk_id, []),
            "pdf_incoming_links": incoming.get(chunk_id, []),
        }

        chunks.append(
            {
                "id": f"ammc::{chunk_id}",
                "content": row.get("text") or "",
                "metadata": scalar_metadata(meta),
            }
        )
    return chunks


def summarize(chunks: list[dict[str, Any]]) -> None:
    counts: dict[str, int] = defaultdict(int)
    for chunk in chunks:
        counts[str(chunk["metadata"].get("corpus", "unknown"))] += 1
    print("Final corpus:")
    for corpus, count in sorted(counts.items()):
        print(f"- {corpus}: {count}")
    print(f"- total: {len(chunks)}")


def index_incrementally(cfg: RAGConfig, chunks: list[dict[str, Any]], batch_size: int) -> None:
    col = get_collection(cfg)
    existing = set(col.get(include=[])["ids"])
    pending = [chunk for chunk in chunks if chunk["id"] not in existing]

    print(f"Existing in Chroma: {len(existing)}")
    print(f"Pending to index: {len(pending)}")
    if not pending:
        print(f"Done. Chroma collection count: {col.count()}")
        return

    embedder = Embedder(cfg.embedding_model, cfg.embedding_fp16, cfg.embedding_batch_size)
    total = len(pending)
    for start in range(0, total, batch_size):
        batch = pending[start : start + batch_size]
        texts = [chunk["content"] for chunk in batch]
        ids = [chunk["id"] for chunk in batch]
        metas = [chunk["metadata"] for chunk in batch]
        embeddings = embedder.embed(texts)
        col.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metas)
        print(f"Indexed {min(start + batch_size, total)}/{total} pending; collection={col.count()}", flush=True)

    print(f"Done. Chroma collection count: {col.count()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build unified Conseiller Reglementaire vector DB.")
    parser.add_argument("--historique-json", type=Path, default=HISTORIQUE_JSON)
    parser.add_argument("--ammc-chunks", type=Path, default=AMMC_CHUNKS_JSONL)
    parser.add_argument("--ammc-links", type=Path, default=AMMC_LINKS_JSONL)
    parser.add_argument("--reset", action="store_true", help="Backup and recreate the Chroma collection.")
    parser.add_argument("--dry-run", action="store_true", help="Print counts without indexing.")
    parser.add_argument("--batch-size", type=int, default=16, help="Embedding/Add batch size.")
    args = parser.parse_args()

    cfg = RAGConfig()
    historique = load_historique(args.historique_json)
    ammc = load_ammc_docling(args.ammc_chunks, args.ammc_links)
    all_chunks = historique + ammc

    summarize(all_chunks)
    print(f"Chroma dir: {chroma_dir(cfg)}")
    print(f"Collection: {cfg.collection_name}")

    if args.dry_run:
        return

    if args.reset:
        backup = backup_vectordb(cfg)
        if backup:
            print(f"Backup created: {backup}")
        reset_collection(cfg)

    index_incrementally(cfg, all_chunks, max(1, args.batch_size))


if __name__ == "__main__":
    main()
