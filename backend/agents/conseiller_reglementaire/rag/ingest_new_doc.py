"""
Ajoute un nouveau PDF dans l'index Chroma sans tout réingérer.
Usage:
    python ingest_new_doc.py chemin/vers/document.pdf
"""
import sys
import json
from pathlib import Path

# Dans la nouvelle structure, les modules sont dans rag/ (ce dossier lui-même)
RAG_DIR = Path(__file__).parent
sys.path.insert(0, str(RAG_DIR))

from rag_config import RAGConfig
from embedder import Embedder
from vector_store import VectorStore

# Config chunking (src/config.py existant)
from config import Config as ChunkConfig
from chunking_pipeline import RAGChunkingPipeline

def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest_new_doc.py <chemin_pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        print(f"Fichier PDF introuvable : {pdf_path}")
        sys.exit(1)

    # 1. Chunking du nouveau PDF avec ton pipeline existant
    print(f"Chunking de {pdf_path.name}...")
    chunk_cfg = ChunkConfig()
    pipeline  = RAGChunkingPipeline(chunk_cfg)
    docs      = pipeline.process_pdf(str(pdf_path))   # ← méthode correcte

    # Conversion Document → dict (même format que save_chunks)
    from chunking_pipeline import ImprovedTokenizer
    tokenizer = ImprovedTokenizer(chunk_cfg.ENCODING_NAME)
    chunks = [
        {
            "id":          f"chunk_{pdf_path.stem}_{i:06d}",
            "content":     doc.page_content,
            "metadata":    doc.metadata,
            "token_count": tokenizer.count_tokens(doc.page_content)
        }
        for i, doc in enumerate(docs)
    ]

    # Sauvegarde JSON pour archivage
    json_out = Path("data/input/jsons") / f"{pdf_path.stem}.json"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"JSON sauvegardé : {json_out}")

    # 2. Embedding + upsert incrémental dans Chroma
    cfg      = RAGConfig()
    embedder = Embedder(cfg.embedding_model, cfg.embedding_fp16, cfg.embedding_batch_size)
    store    = VectorStore(cfg.chroma_dir, cfg.collection_name, embedder)
    store.upsert(chunks)

    print(f"Total chunks dans l'index : {store.count()}")

if __name__ == "__main__":
    main()