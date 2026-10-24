"""
Hybrid RAG over parser-produced legal chunks.

This module uses:
- the validated legal_chunks.jsonl as the canonical chunk source;
- BAAI/bge-m3 through the existing Embedder wrapper;
- BM25 for exact legal wording, article numbers, law numbers, and annex names;
- pdf_links_mapped.jsonl to pull referenced chunks into the answer context;
- chunk metadata for hierarchy, page numbers, footnotes, and source citations.

CLI examples:
    python legal_chunk_rag.py index --force
    python legal_chunk_rag.py query "Quels sont les pouvoirs de l'AMMC ?"
"""

from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

RAG_DIR = Path(__file__).resolve().parent
AGENT_DIR = RAG_DIR.parent
PARSING_OUTPUT_DIR = AGENT_DIR / "parsing" / "notebooks" / "output"
DEFAULT_CHUNKS_PATH = PARSING_OUTPUT_DIR / "legal_chunks.jsonl"
DEFAULT_LINKS_PATH = PARSING_OUTPUT_DIR / "pdf_links_mapped.jsonl"
DEFAULT_INDEX_DIR = AGENT_DIR / "data" / "legal_rag_index"

if str(RAG_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_DIR))

from embedder import Embedder  # noqa: E402
from llm_client import LLMClient  # noqa: E402
from rag_config import RAGConfig  # noqa: E402


ARTICLE_REF_RE = re.compile(
    r"\barticles?\s+((?:premier|[0-9]+(?:\s*(?:bis|ter|quater))?|[IVXLCDM]+(?:\.[0-9]+)*)(?:\s*(?:,|et|a|a|-)\s*(?:premier|[0-9]+(?:\s*(?:bis|ter|quater))?|[IVXLCDM]+(?:\.[0-9]+)*))*)",
    re.IGNORECASE,
)
TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)


@dataclass
class LegalChunk:
    chunk_id: str
    chunk_type: str
    name: str
    text: str
    page_start: int | None
    page_end: int | None
    metadata: dict[str, Any]
    footnotes: list[Any] = field(default_factory=list)


@dataclass
class RetrievedChunk:
    chunk: LegalChunk
    score: float
    source: str
    referenced_by: str | None = None
    link_kind: str | None = None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "") if len(t) > 1]


def slug_article_name(name: str) -> str:
    value = normalize_space(name).lower()
    value = re.sub(r"^article\s+", "", value)
    value = re.sub(r"[^\w.]+", " ", value, flags=re.UNICODE).strip()
    return value


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if not na or not nb:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def minmax(scores: list[float]) -> list[float]:
    if not scores:
        return []
    lo = min(scores)
    hi = max(scores)
    if hi <= lo:
        return [1.0 if s > 0 else 0.0 for s in scores]
    return [(s - lo) / (hi - lo) for s in scores]


def hierarchy_path(meta: dict[str, Any]) -> str:
    parts = [
        meta.get("document"),
        meta.get("livre"),
        meta.get("titre"),
        meta.get("chapitre"),
        meta.get("section"),
        meta.get("annexe"),
        meta.get("article_id") if meta.get("chunk_type") == "article" else None,
    ]
    return " > ".join(str(p) for p in parts if p)


def page_label(chunk: LegalChunk) -> str:
    if chunk.page_start is None and chunk.page_end is None:
        return "page inconnue"
    if chunk.page_start == chunk.page_end or chunk.page_end is None:
        return f"page {chunk.page_start}"
    return f"pages {chunk.page_start}-{chunk.page_end}"


def chunk_display_name(row: dict[str, Any]) -> str:
    if row.get("chunk_type") == "article":
        return row.get("article_id") or row.get("chunk_id", "")
    if row.get("annexe"):
        return row.get("annexe")
    return row.get("article_id") or row.get("chunk_id", "")


class LegalChunkRAG:
    def __init__(
        self,
        chunks_path: Path = DEFAULT_CHUNKS_PATH,
        links_path: Path = DEFAULT_LINKS_PATH,
        index_dir: Path = DEFAULT_INDEX_DIR,
        vector_weight: float = 0.65,
        bm25_weight: float = 0.35,
    ):
        self.chunks_path = Path(chunks_path)
        self.links_path = Path(links_path)
        self.index_dir = Path(index_dir)
        self.index_path = self.index_dir / "index.pkl"
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight

        self.cfg = RAGConfig()
        self.embedder: Embedder | None = None

        self.chunks = self._load_chunks()
        self.chunk_by_id = {c.chunk_id: c for c in self.chunks}
        self.article_lookup = self._build_article_lookup()
        self.links_by_source, self.links_by_target = self._load_links()

        self.bm25: BM25Okapi | None = None
        self.embeddings: list[list[float]] = []
        self.search_texts: list[str] = []
        self.tokenized_corpus: list[list[str]] = []

    def _load_chunks(self) -> list[LegalChunk]:
        rows = read_jsonl(self.chunks_path)
        chunks: list[LegalChunk] = []
        for row in rows:
            chunk_id = row.get("chunk_id") or row.get("id")
            if not chunk_id:
                continue
            chunks.append(
                LegalChunk(
                    chunk_id=chunk_id,
                    chunk_type=row.get("chunk_type") or "unknown",
                    name=chunk_display_name(row),
                    text=row.get("text") or row.get("content") or "",
                    page_start=row.get("page_start"),
                    page_end=row.get("page_end"),
                    metadata=row,
                    footnotes=row.get("footnotes") or [],
                )
            )
        return chunks

    def _build_article_lookup(self) -> dict[tuple[str, str], list[str]]:
        lookup: dict[tuple[str, str], list[str]] = {}
        for chunk in self.chunks:
            if chunk.chunk_type != "article":
                continue
            doc = normalize_space(chunk.metadata.get("document") or "").lower()
            article = slug_article_name(chunk.name)
            if not doc or not article:
                continue
            lookup.setdefault((doc, article), []).append(chunk.chunk_id)
        return lookup

    def _load_links(self) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
        links = read_jsonl(self.links_path)
        by_source: dict[str, list[dict[str, Any]]] = {}
        by_target: dict[str, list[dict[str, Any]]] = {}
        for link in links:
            source_id = link.get("source_chunk_id")
            target_id = link.get("target_chunk_id")
            if source_id and target_id:
                by_source.setdefault(source_id, []).append(link)
                by_target.setdefault(target_id, []).append(link)
        return by_source, by_target

    def _ensure_embedder(self) -> Embedder:
        if self.embedder is None:
            self.embedder = Embedder(
                self.cfg.embedding_model,
                self.cfg.embedding_fp16,
                self.cfg.embedding_batch_size,
            )
        return self.embedder

    def _search_text(self, chunk: LegalChunk) -> str:
        meta = chunk.metadata
        fields = [
            chunk.name,
            meta.get("document"),
            meta.get("livre"),
            meta.get("titre"),
            meta.get("chapitre"),
            meta.get("section"),
            meta.get("annexe"),
            chunk.text,
        ]
        if chunk.footnotes:
            fields.append(" ".join(normalize_space(str(f)) for f in chunk.footnotes))
        return "\n".join(str(f) for f in fields if f)

    def build_index(self, force: bool = False) -> None:
        if self.index_path.exists() and not force:
            self.load_index()
            return
        if not self.chunks:
            raise RuntimeError(f"No chunks found in {self.chunks_path}")

        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.search_texts = [self._search_text(c) for c in self.chunks]
        self.tokenized_corpus = [tokenize(t) for t in self.search_texts]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        embedder = self._ensure_embedder()
        self.embeddings = embedder.embed(self.search_texts)

        payload = {
            "chunks_path": str(self.chunks_path),
            "links_path": str(self.links_path),
            "chunk_ids": [c.chunk_id for c in self.chunks],
            "search_texts": self.search_texts,
            "tokenized_corpus": self.tokenized_corpus,
            "embeddings": self.embeddings,
            "embedding_model": self.cfg.embedding_model,
        }
        with self.index_path.open("wb") as f:
            pickle.dump(payload, f)

    def load_index(self) -> None:
        if not self.index_path.exists():
            self.build_index(force=True)
            return
        try:
            with self.index_path.open("rb") as f:
                payload = pickle.load(f)
        except Exception:
            self.build_index(force=True)
            return

        indexed_ids = payload.get("chunk_ids") or []
        current_ids = [c.chunk_id for c in self.chunks]
        if indexed_ids != current_ids:
            self.build_index(force=True)
            return

        self.search_texts = payload["search_texts"]
        self.tokenized_corpus = payload["tokenized_corpus"]
        self.embeddings = payload["embeddings"]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def build_bm25_only(self) -> None:
        """Build an in-memory lexical index without loading BGE."""
        if self.bm25 is not None and self.search_texts:
            return
        self.search_texts = [self._search_text(c) for c in self.chunks]
        self.tokenized_corpus = [tokenize(t) for t in self.search_texts]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def retrieve_bm25_only(
        self,
        question: str,
        top_k: int = 8,
        linked_k: int = 8,
        include_inbound_links: bool = False,
    ) -> list[RetrievedChunk]:
        """Fast fallback useful for smoke tests and exact legal references."""
        self.build_bm25_only()
        if not self.chunks or not self.bm25:
            return []

        scores = [float(s) for s in self.bm25.get_scores(tokenize(question))]
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
        max_score = max(scores) if scores else 0.0

        selected: dict[str, RetrievedChunk] = {}
        for idx, score in ranked[:top_k]:
            if score <= 0:
                continue
            normalized = score / max_score if max_score else 0.0
            chunk = self.chunks[idx]
            selected[chunk.chunk_id] = RetrievedChunk(chunk=chunk, score=normalized, source="bm25")

        self._expand_exact_articles(question, selected)
        self._expand_linked_chunks(selected, linked_k=linked_k, include_inbound=include_inbound_links)
        return sorted(selected.values(), key=lambda r: (r.source != "bm25", -r.score))

    def retrieve(
        self,
        question: str,
        top_k: int = 8,
        candidate_k: int = 40,
        linked_k: int = 8,
        include_inbound_links: bool = False,
    ) -> list[RetrievedChunk]:
        self.load_index()
        if not self.chunks:
            return []

        query_tokens = tokenize(question)
        bm25_raw = self.bm25.get_scores(query_tokens).tolist() if self.bm25 else [0.0] * len(self.chunks)
        bm25_scores = minmax([float(s) for s in bm25_raw])

        query_embedding = self._ensure_embedder().embed_query(question)
        vector_raw = [cosine_similarity(query_embedding, emb) for emb in self.embeddings]
        vector_scores = minmax(vector_raw)

        fused: list[tuple[int, float]] = []
        for i in range(len(self.chunks)):
            score = self.vector_weight * vector_scores[i] + self.bm25_weight * bm25_scores[i]
            fused.append((i, score))
        fused.sort(key=lambda item: item[1], reverse=True)

        selected: dict[str, RetrievedChunk] = {}
        for idx, score in fused[:candidate_k]:
            if len([r for r in selected.values() if r.source == "hybrid"]) >= top_k:
                break
            chunk = self.chunks[idx]
            if score <= 0:
                continue
            selected[chunk.chunk_id] = RetrievedChunk(chunk=chunk, score=float(score), source="hybrid")

        self._expand_exact_articles(question, selected)
        self._expand_linked_chunks(selected, linked_k=linked_k, include_inbound=include_inbound_links)

        return sorted(selected.values(), key=lambda r: (r.source != "hybrid", -r.score))

    def _expand_exact_articles(self, question: str, selected: dict[str, RetrievedChunk]) -> None:
        doc_hints = {
            normalize_space(c.chunk.metadata.get("document") or "").lower()
            for c in selected.values()
            if c.chunk.metadata.get("document")
        }
        if not doc_hints:
            return

        refs = set()
        for match in ARTICLE_REF_RE.finditer(question):
            raw = match.group(1)
            for part in re.split(r"\s*(?:,|et|a|a|-)\s*", raw, flags=re.IGNORECASE):
                clean = slug_article_name(part)
                if clean:
                    refs.add(clean)

        for doc in doc_hints:
            for article in refs:
                for chunk_id in self.article_lookup.get((doc, article), [])[:2]:
                    if chunk_id not in selected and chunk_id in self.chunk_by_id:
                        selected[chunk_id] = RetrievedChunk(
                            chunk=self.chunk_by_id[chunk_id],
                            score=0.55,
                            source="exact_article",
                        )

    def _expand_linked_chunks(
        self,
        selected: dict[str, RetrievedChunk],
        linked_k: int,
        include_inbound: bool,
    ) -> None:
        primary_ids = [cid for cid, item in selected.items() if item.source in {"hybrid", "bm25", "exact_article"}]
        added = 0
        for source_id in primary_ids:
            if added >= linked_k:
                break
            for link in self.links_by_source.get(source_id, []):
                target_id = link.get("target_chunk_id")
                if not target_id or target_id in selected or target_id not in self.chunk_by_id:
                    continue
                selected[target_id] = RetrievedChunk(
                    chunk=self.chunk_by_id[target_id],
                    score=0.45,
                    source="pdf_link",
                    referenced_by=source_id,
                    link_kind=link.get("kind"),
                )
                added += 1
                if added >= linked_k:
                    break

        if not include_inbound:
            return
        for target_id in primary_ids:
            if added >= linked_k:
                break
            for link in self.links_by_target.get(target_id, []):
                source_id = link.get("source_chunk_id")
                if not source_id or source_id in selected or source_id not in self.chunk_by_id:
                    continue
                selected[source_id] = RetrievedChunk(
                    chunk=self.chunk_by_id[source_id],
                    score=0.30,
                    source="pdf_backlink",
                    referenced_by=target_id,
                    link_kind=link.get("kind"),
                )
                added += 1
                if added >= linked_k:
                    break

    def format_context(self, retrieved: list[RetrievedChunk], max_chars_per_chunk: int = 4500) -> str:
        parts: list[str] = []
        for i, item in enumerate(retrieved, start=1):
            chunk = item.chunk
            meta = chunk.metadata
            header = [
                f"[S{i}] {chunk.name}",
                f"type: {chunk.chunk_type}",
                f"source_retrieval: {item.source}",
                f"pages: {page_label(chunk)}",
                f"hierarchie: {hierarchy_path(meta)}",
                f"chunk_id: {chunk.chunk_id}",
            ]
            if item.referenced_by:
                header.append(f"reference_par_chunk_id: {item.referenced_by}")
            if item.link_kind:
                header.append(f"type_lien_pdf: {item.link_kind}")

            text = chunk.text[:max_chars_per_chunk]
            if len(chunk.text) > max_chars_per_chunk:
                text += "\n[Texte tronque pour le contexte LLM]"

            if chunk.footnotes:
                notes = "\n".join(f"- {normalize_space(str(note))}" for note in chunk.footnotes)
                text = f"{text}\n\nNotes de bas de page:\n{notes}"

            parts.append("\n".join(header) + "\n\n" + text)
        return "\n\n---\n\n".join(parts)

    def sources(self, retrieved: list[RetrievedChunk]) -> list[dict[str, Any]]:
        rows = []
        for item in retrieved:
            c = item.chunk
            rows.append(
                {
                    "chunk_id": c.chunk_id,
                    "name": c.name,
                    "chunk_type": c.chunk_type,
                    "document": c.metadata.get("document"),
                    "hierarchy": hierarchy_path(c.metadata),
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "retrieval_source": item.source,
                    "referenced_by": item.referenced_by,
                    "has_footnotes": bool(c.footnotes),
                }
            )
        return rows

    def build_messages(self, question: str, retrieved: list[RetrievedChunk]) -> list[dict[str, str]]:
        context = self.format_context(retrieved)
        system = (
            "Tu es un assistant juridique specialise dans la reglementation du marche financier marocain. "
            "Reponds exclusivement avec le contexte fourni. Quand un chunk reference un autre article via "
            "source_retrieval=pdf_link ou exact_article, utilise ce chunk reference pour completer l'analyse. "
            "Cite chaque affirmation juridique avec [Sx], le nom de l'article ou annexe, le chemin hierarchique "
            "et les pages. Si le contexte ne permet pas de repondre avec certitude, dis-le clairement."
        )
        user = f"Contexte:\n{context}\n\nQuestion:\n{question}"
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def answer(self, question: str, top_k: int = 8, linked_k: int = 8) -> dict[str, Any]:
        retrieved = self.retrieve(question, top_k=top_k, linked_k=linked_k)
        messages = self.build_messages(question, retrieved)

        api_key = self.cfg.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            return {
                "answer": None,
                "error": "OPENROUTER_API_KEY is missing; returning context and sources only.",
                "context": messages[-1]["content"],
                "sources": self.sources(retrieved),
            }

        llm = LLMClient(
            api_key=api_key,
            model=self.cfg.llm_model,
            max_tokens=self.cfg.llm_max_tokens,
            temperature=self.cfg.llm_temperature,
        )
        answer_text = llm.chat(messages)
        return {
            "answer": answer_text,
            "sources": self.sources(retrieved),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Legal chunk RAG over Docling parser output.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Build or refresh the local BGE/BM25 index.")
    p_index.add_argument("--force", action="store_true", help="Rebuild even if an index already exists.")
    p_index.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    p_index.add_argument("--links", type=Path, default=DEFAULT_LINKS_PATH)
    p_index.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)

    p_query = sub.add_parser("query", help="Retrieve and optionally answer a question.")
    p_query.add_argument("question")
    p_query.add_argument("--top-k", type=int, default=8)
    p_query.add_argument("--linked-k", type=int, default=8)
    p_query.add_argument("--no-llm", action="store_true", help="Only print retrieved context and sources.")
    p_query.add_argument("--bm25-only", action="store_true", help="Skip BGE and use only BM25.")
    p_query.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    p_query.add_argument("--links", type=Path, default=DEFAULT_LINKS_PATH)
    p_query.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)

    args = parser.parse_args()
    rag = LegalChunkRAG(chunks_path=args.chunks, links_path=args.links, index_dir=args.index_dir)

    if args.command == "index":
        rag.build_index(force=args.force)
        print(f"Index ready: {rag.index_path}")
        print(f"Chunks: {len(rag.chunks)}")
        print(f"PDF link sources: {len(rag.links_by_source)}")
        return

    if args.bm25_only:
        retrieved = rag.retrieve_bm25_only(args.question, top_k=args.top_k, linked_k=args.linked_k)
    else:
        retrieved = rag.retrieve(args.question, top_k=args.top_k, linked_k=args.linked_k)
    if args.no_llm:
        print(rag.format_context(retrieved))
        print("\nSOURCES_JSON:")
        print(json.dumps(rag.sources(retrieved), ensure_ascii=False, indent=2))
        return

    result = rag.answer(args.question, top_k=args.top_k, linked_k=args.linked_k)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
