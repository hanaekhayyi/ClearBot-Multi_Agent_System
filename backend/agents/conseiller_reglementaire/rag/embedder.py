import builtins
from typing import Optional

# Workaround for some FlagEmbedding builds that reference Optional during import
# without importing it in their trainer module.
builtins.Optional = Optional

from FlagEmbedding import BGEM3FlagModel

class Embedder:
    def __init__(self, model_name: str = "BAAI/bge-m3", use_fp16: bool = True, batch_size: int = 12):
        self.model = BGEM3FlagModel(model_name, use_fp16=use_fp16)
        self.batch_size = batch_size

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self.model.encode(texts, batch_size=self.batch_size, max_length=8192)
        return result["dense_vecs"].tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]
