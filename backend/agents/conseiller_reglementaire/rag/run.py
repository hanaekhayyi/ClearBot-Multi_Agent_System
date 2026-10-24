"""
Point d'entrée unique : chunking + sauvegarde JSON + indexation Chroma.
Usage : python run.py  (depuis le dossier rag/)
"""
import sys
import json
import shutil
from pathlib import Path

# Dans la nouvelle structure, tous les modules sont dans ce dossier (rag/)
RAG_DIR = Path(__file__).parent
sys.path.insert(0, str(RAG_DIR))

from config import Config as ChunkConfig
from chunking_pipeline import RAGChunkingPipeline
from rag_config import RAGConfig
from embedder import Embedder
from vector_store import VectorStore


def main():
    # ── 1. Chunking ───────────────────────────────────────────────
    chunk_cfg = ChunkConfig()
    pdf_files = list(chunk_cfg.INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"Aucun PDF trouvé dans {chunk_cfg.INPUT_DIR}")
        sys.exit(1)

    print(f"{len(pdf_files)} PDF(s) trouvé(s). Chunking en cours...")
    pipeline = RAGChunkingPipeline(chunk_cfg)
    all_docs = []
    for pdf in pdf_files:
        docs = pipeline.process_pdf(str(pdf))
        all_docs.extend(docs)
        print(f"  {pdf.name} → {len(docs)} chunks")

    if not all_docs:
        print("Aucun chunk produit. Vérifier Poppler.")
        sys.exit(1)

    # ── 2. Sauvegarde JSON ────────────────────────────────────────
    from chunking_pipeline import ImprovedTokenizer
    tokenizer = ImprovedTokenizer(chunk_cfg.ENCODING_NAME)

    source_counters = {}
    chunks_data = []
    import re
    for doc in all_docs:
        raw_source = doc.metadata.get("source", "unknown")
        key = re.sub(r"[^a-zA-Z0-9]", "_", raw_source[:40]).strip("_").lower()
        source_counters[key] = source_counters.get(key, 0)
        chunk_id = f"chunk_{key}_{source_counters[key]:06d}"
        source_counters[key] += 1
        chunks_data.append({
            "id":          chunk_id,
            "content":     doc.page_content,
            "metadata":    doc.metadata,
            "token_count": tokenizer.count_tokens(doc.page_content)
        })

    json_dir = chunk_cfg.INPUT_DIR / "jsons"
    json_dir.mkdir(parents=True, exist_ok=True)
    json_out = json_dir / "chunks_output.json"

    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)
    print(f"\nJSON sauvegardé : {json_out} ({len(chunks_data)} chunks)")

    # ── 3. Indexation Chroma ──────────────────────────────────────
    rag_cfg  = RAGConfig()
    embedder = Embedder(rag_cfg.embedding_model, rag_cfg.embedding_fp16, rag_cfg.embedding_batch_size)
    store    = VectorStore(rag_cfg.chroma_dir, rag_cfg.collection_name, embedder)

    print("\nIndexation dans Chroma...")
    store.ingest(chunks_data)
    print(f"Total chunks dans l'index : {store.count()}")
    print("\nPrêt. Lance : python chat.py")


if __name__ == "__main__":
    main()