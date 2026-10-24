import json
import chromadb
from pathlib import Path
import sys

# Ajouter le dossier rag/ au path pour les imports relatifs
_RAG_DIR = Path(__file__).parent
if str(_RAG_DIR) not in sys.path:
    sys.path.insert(0, str(_RAG_DIR))


class VectorStore:
    def __init__(self, persist_dir: str, collection_name: str, embedder):
        # Résoudre en absolu si chemin relatif (relatif au dossier parent = conseiller_reglementaire/)
        p = Path(persist_dir)
        if not p.is_absolute():
            p = (Path(__file__).parent.parent / persist_dir).resolve()
        self.client = chromadb.PersistentClient(path=str(p))
        self.col = self.client.get_or_create_collection(collection_name)
        self.embedder = embedder

    def _prepare(self, chunks: list[dict]):
        texts, ids, metadatas = [], [], []
        for c in chunks:
            ids.append(c["id"])
            meta = dict(c["metadata"])
            if "links_to" in meta and isinstance(meta["links_to"], list):
                meta["links_to"] = json.dumps(meta["links_to"])
            meta["ref_normalized"] = meta.get("reference_id", "").lower().strip()
            texts.append(c["content"])
            metadatas.append(meta)
        return texts, ids, metadatas

    def ingest(self, chunks: list[dict]):
        """Ingestion initiale depuis JSONs — skip les IDs déjà présents."""
        existing = set(self.col.get(include=[])["ids"])
        new_chunks = [c for c in chunks if c["id"] not in existing]
        if not new_chunks:
            print("Aucun nouveau chunk à indexer.")
            return
        texts, ids, metadatas = self._prepare(new_chunks)
        embeddings = self.embedder.embed(texts)
        self.col.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        print(f"{len(ids)} chunks indexés ({len(chunks) - len(new_chunks)} déjà présents, ignorés).")

    def upsert(self, chunks: list[dict]):
        """Ajout incrémental pour nouveaux documents — écrase si même ID."""
        texts, ids, metadatas = self._prepare(chunks)
        embeddings = self.embedder.embed(texts)
        self.col.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        print(f"{len(ids)} chunks upsertés.")

    def query(self, query_embedding: list[float], n_results: int = 6) -> dict:
        return self.col.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

    def get_by_ref(self, ref: str) -> dict:
        return self.col.get(
            where={"ref_normalized": ref.lower().strip()},
            include=["documents", "metadatas"]
        )

    def get_by_original_chunk_id(self, original_chunk_id: str) -> dict:
        return self.col.get(
            where={"original_chunk_id": original_chunk_id},
            include=["documents", "metadatas"]
        )

    def get_by_id(self, chunk_id: str) -> dict:
        return self.col.get(
            ids=[chunk_id],
            include=["documents", "metadatas"]
        )

    def count(self) -> int:
        return self.col.count()
