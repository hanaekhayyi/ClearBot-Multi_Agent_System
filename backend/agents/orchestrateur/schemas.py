"""
Schémas input/output de l'OrchestratorAgent
"""
from pydantic import BaseModel
from typing import Optional, List


class OrchestratorInput(BaseModel):
    message: str
    session_id: Optional[str] = None


class OrchestratorOutput(BaseModel):
    response: str
    agent_used: str
    route: str                        # reglementaire | classification | rag | classification+rag | none
    classification: Optional[str] = ""
    priorite: Optional[str] = ""
    statut: Optional[str] = ""
    service: Optional[str] = ""
    systeme: Optional[str] = ""
    needs_glpi: bool = False
    rag_sources: List[str] = []
    regl_sources: List[str] = []
