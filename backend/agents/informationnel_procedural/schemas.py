"""
Schémas input/output du RAGAgent (Informationnel & Procédural)
"""
from pydantic import BaseModel
from typing import List, Optional


class RAGInput(BaseModel):
    message: str


class RAGOutput(BaseModel):
    response: str
    retrieved_docs_count: int = 0
    sources: List[str] = []
    agent_used: str = "RAGAgent"
