import json
from pathlib import Path
import sys

# Dans la nouvelle structure, les modules sont dans rag/ (ce dossier lui-même)
RAG_DIR = Path(__file__).parent
sys.path.insert(0, str(RAG_DIR))

from config import Config
from embedder import Embedder
from vector_store import VectorStore

def main():
    cfg = Config()
    embedder = Embedder(cfg.embedding_model, cfg.embedding_fp16, cfg.embedding_batch_size)
    store = VectorStore(cfg.chroma_dir, cfg.collection_name, embedder)

    if store.count() > 0:
        print(f"Index déjà peuplé ({store.count()} chunks). Supprimez data/chroma_db pour réingérer.")
        return

    all_chunks = []
    for json_file in sorted(cfg.input_dir.glob("*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        print(f"{json_file.name} : {len(chunks)} chunks")
        all_chunks.extend(chunks)

    store.ingest(all_chunks)

if __name__ == "__main__":
    main()