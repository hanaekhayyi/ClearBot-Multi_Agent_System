import os
import yaml
from pathlib import Path

class RAGConfig:
    def __init__(self, path: str = None):
        # Par défaut : data/settings.yaml relatif au dossier rag/
        if path is None:
            path = str(Path(__file__).parent.parent / "data" / "settings.yaml")
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        self.embedding_model  = raw["embedding"]["model"]
        self.embedding_fp16   = raw["embedding"]["use_fp16"]
        self.embedding_batch_size = raw["embedding"]["batch_size"]

        self.chroma_dir       = raw["vector_store"]["persist_dir"]
        self.collection_name  = raw["vector_store"]["collection_name"]
        self.n_results        = raw["vector_store"]["n_results"]

        self.llm_model        = raw["llm"]["model"]
        self.llm_max_tokens   = raw["llm"]["max_tokens"]
        self.llm_temperature  = raw["llm"].get("temperature", 0.1)
        self.openrouter_api_key = (
            raw["llm"].get("api_key") 
            or os.environ.get("OPENROUTER_API_KEY", "")
        )

        self.input_dir        = Path(raw["data"]["input_dir"])