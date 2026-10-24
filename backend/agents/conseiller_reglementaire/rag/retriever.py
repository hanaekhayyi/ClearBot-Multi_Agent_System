import json
import re
from typing import Any

from rank_bm25 import BM25Okapi

try:
    from sentence_transformers import CrossEncoder
    _RERANKER_AVAILABLE = True
except ImportError:
    _RERANKER_AVAILABLE = False

try:
    from vector_store import VectorStore
    from embedder import Embedder
except ImportError:
    from src.vector_store import VectorStore
    from src.embedder import Embedder


class Retriever:
    """
    Hybrid retriever for the unified regulatory Chroma collection.

    It supports both retained corpora:
    - actualite_historique chunks, with links_to;
    - ammc_recueil_docling chunks, with hierarchy/pages/footnotes/pdf links.
    """

    def __init__(self, vector_store: VectorStore, embedder: Embedder, n_results: int = 10,
                 reranker_model: str = None, reranker_top_k: int = 10):
        self.vs = vector_store
        self.embedder = embedder
        self.n_results = n_results
        self._reranker_top_k = reranker_top_k
        self._bm25 = None
        self._bm25_docs: list[tuple[str, str, dict[str, Any]]] = []
        self._build_bm25_index()

        # Initialiser le reranker si disponible
        self._reranker = None
        if reranker_model and _RERANKER_AVAILABLE:
            try:
                self._reranker = CrossEncoder(reranker_model)
                print(f"✅ Reranker chargé : {reranker_model}")
            except Exception as e:
                print(f"⚠️ Reranker non chargé : {e}")
        elif reranker_model and not _RERANKER_AVAILABLE:
            print("⚠️ sentence-transformers non installé — reranker désactivé")

    @staticmethod
    def _loads(value: Any, default: Any):
        if value in (None, ""):
            return default
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default
        return value

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"\w+", (text or "").lower())

    @staticmethod
    def _norm_ref(value: str) -> str:
        value = re.sub(r"\s+", " ", (value or "").lower()).strip()
        return value

    @staticmethod
    def _result_id(result: dict) -> str:
        meta = result.get("metadata") or {}
        return (
            result.get("id")
            or meta.get("original_chunk_id")
            or f"{meta.get('reference_id', '')}|{meta.get('source', '')}"
        )

    def _build_bm25_index(self):
        result = self.vs.col.get(include=["documents", "metadatas"])
        documents = result.get("documents") or []
        if not documents:
            return

        self._bm25_docs = list(zip(result["ids"], documents, result["metadatas"]))
        tokenized = [self._tokens(doc) for doc in documents]
        self._bm25 = BM25Okapi(tokenized)
        print(f"Index BM25 construit ({len(self._bm25_docs)} documents)")

    def _bm25_search(self, query: str, n: int) -> list[dict]:
        if not self._bm25:
            return []

        scores = self._bm25.get_scores(self._tokens(query))
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:n]

        results = []
        for idx, score in ranked:
            if score <= 0:
                continue
            chunk_id, content, metadata = self._bm25_docs[idx]
            results.append({
                "id": chunk_id,
                "content": content,
                "metadata": metadata,
                "score": float(score),
                "referenced_by": None,
                "source": "bm25",
            })
        return results

    def retrieve(self, query: str) -> list[dict]:
        emb = self.embedder.embed_query(query)
        vector_results = self.vs.query(emb, self.n_results)

        chunks: list[dict] = []
        seen_ids: set[str] = set()

        docs = vector_results.get("documents") or [[]]
        metas = vector_results.get("metadatas") or [[]]
        ids = vector_results.get("ids") or [[]]
        distances = vector_results.get("distances") or [[]]

        for i, doc in enumerate(docs[0]):
            chunk_id = ids[0][i]
            chunks.append({
                "id": chunk_id,
                "content": doc,
                "metadata": metas[0][i],
                "score": distances[0][i],
                "referenced_by": None,
                "source": "vector",
            })
            seen_ids.add(chunk_id)

        for result in self._bm25_search(query, self.n_results):
            result_id = self._result_id(result)
            if result_id not in seen_ids:
                chunks.append(result)
                seen_ids.add(result_id)

        self._expand_references(chunks, seen_ids)

        # ── Reranking cross-encoder ──
        if self._reranker and chunks:
            chunks = self._rerank(query, chunks)

        return chunks

    def _rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        """Reranke les chunks avec le cross-encoder et garde les top-K."""
        pairs = [(query, chunk.get("content", "")) for chunk in chunks]
        scores = self._reranker.predict(pairs)

        # Associer les scores aux chunks
        for i, chunk in enumerate(chunks):
            chunk["rerank_score"] = float(scores[i])

        # Trier par score décroissant et garder top-K
        chunks.sort(key=lambda c: c.get("rerank_score", 0), reverse=True)
        top_chunks = chunks[:self._reranker_top_k]

        print(f"[Reranker] {len(chunks)} → {len(top_chunks)} chunks (top-{self._reranker_top_k})")
        for i, c in enumerate(top_chunks[:5]):
            meta = c.get("metadata", {})
            print(f"  [{i+1}] score={c['rerank_score']:.3f} | {meta.get('reference_id', '?')} | {meta.get('source', '?')[:50]}")

        return top_chunks

    def _expand_references(self, chunks: list[dict], seen_ids: set[str]) -> None:
        seen_refs = {
            self._norm_ref((chunk.get("metadata") or {}).get("reference_id", ""))
            for chunk in chunks
        }

        for chunk in list(chunks):
            meta = chunk.get("metadata") or {}

            # Actualite historique explicit links: ["article 13", "article 14"]
            for link in self._loads(meta.get("links_to", "[]"), []):
                norm_link = self._norm_ref(str(link))
                if norm_link in seen_refs:
                    continue
                linked = self.vs.get_by_ref(str(link))
                if linked.get("documents"):
                    linked_id = linked.get("ids", [None])[0]
                    chunks.append({
                        "id": linked_id,
                        "content": linked["documents"][0],
                        "metadata": linked["metadatas"][0],
                        "score": None,
                        "referenced_by": meta.get("reference_id"),
                        "source": "link",
                    })
                    seen_refs.add(norm_link)
                    if linked_id:
                        seen_ids.add(linked_id)

            # AMMC Docling mapped PDF links.
            for link in self._loads(meta.get("pdf_outgoing_links", "[]"), []):
                if not isinstance(link, dict):
                    continue
                target_id = link.get("target_chunk_id")
                if not target_id or target_id in seen_ids:
                    continue
                linked = self.vs.get_by_original_chunk_id(target_id)
                if linked.get("documents"):
                    linked_id = linked.get("ids", [target_id])[0]
                    chunks.append({
                        "id": linked_id,
                        "content": linked["documents"][0],
                        "metadata": linked["metadatas"][0],
                        "score": None,
                        "referenced_by": meta.get("reference_id"),
                        "source": "pdf_link",
                    })
                    seen_ids.add(target_id)
                    seen_ids.add(linked_id)

    def _source_label(self, meta: dict) -> str:
        corpus = meta.get("corpus", "unknown")
        if corpus == "actualite_historique":
            return "Actualite historique"
        if corpus == "ammc_recueil_docling":
            return "Recueil AMMC"
        return str(corpus)

    def _page_label(self, meta: dict) -> str:
        start = meta.get("page_start")
        end = meta.get("page_end")
        if start in (None, ""):
            return ""
        if end in (None, "", start):
            return f"page {start}"
        return f"pages {start}-{end}"

    def _hierarchy(self, meta: dict) -> str:
        if meta.get("hierarchy"):
            return meta["hierarchy"]
        return " > ".join(filter(None, [
            meta.get("document") or meta.get("source"),
            meta.get("livre"),
            meta.get("title"),
            meta.get("chapter"),
            meta.get("section"),
            meta.get("annexe"),
            meta.get("reference_id"),
        ]))

    def format_sources(self, chunks: list[dict]) -> list[dict]:
        sources = []
        for idx, chunk in enumerate(chunks, start=1):
            meta = chunk.get("metadata") or {}
            sources.append({
                "label": f"S{idx}",
                "corpus": meta.get("corpus"),
                "source_label": self._source_label(meta),
                "document": meta.get("document") or meta.get("source"),
                "reference_id": meta.get("reference_id"),
                "hierarchy": self._hierarchy(meta),
                "page_start": meta.get("page_start"),
                "page_end": meta.get("page_end"),
                "retrieval_source": chunk.get("source"),
                "referenced_by": chunk.get("referenced_by"),
            })
        return sources

    def format_context(self, chunks: list[dict], max_chars_per_chunk: int = 2500) -> str:
        parts = []
        for idx, chunk in enumerate(chunks, start=1):
            meta = chunk.get("metadata") or {}
            header = "\n".join(filter(None, [
                f"[S{idx}] {self._source_label(meta)}",
                f"Document: {meta.get('document') or meta.get('source') or 'Source inconnue'}",
                f"Reference: {meta.get('reference_id', '')}",
                f"Chemin: {self._hierarchy(meta)}",
                f"Pages: {self._page_label(meta)}",
                f"Mode recuperation: {chunk.get('source')}",
            ]))
            if chunk.get("referenced_by"):
                header += f"\nReference par: {chunk['referenced_by']}"

            footnotes = self._loads(meta.get("footnotes", "[]"), [])
            notes = ""
            if footnotes:
                notes = "\n\nNotes de bas de page:\n" + "\n".join(f"- {note}" for note in footnotes)

            content = chunk.get("content", "")
            if max_chars_per_chunk and len(content) > max_chars_per_chunk:
                content = content[:max_chars_per_chunk].rstrip() + "\n[extrait tronqué]"

            parts.append(f"{header}\n\n{content}{notes}")

        return "\n\n---\n\n".join(parts)
