"""
Schémas input/output du ReglementaireAgent
"""
from pydantic import BaseModel
from typing import List, Optional


class ReglementaireInput(BaseModel):
    message: str


class ReglementaireOutput(BaseModel):
    response: str
    agent_used: str = "ReglementaireAgent"
    sources: List[str] = []
    retrieved_docs_count: int = 0
