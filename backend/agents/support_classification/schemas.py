"""
Schémas input/output du ClassificationAgent
"""
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ClassificationType(str, Enum):
    INCIDENT = "INCIDENT"
    DEMANDE = "DEMANDE"
    RECLAMATION = "RECLAMATION"


class Priorite(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"
    NA = "N/A"


class ClassificationInput(BaseModel):
    message: str
    conversation_history: list = []


class ClassificationOutput(BaseModel):
    response: str
    classification: Optional[ClassificationType] = None
    priorite: Optional[Priorite] = None
    statut: Optional[str] = ""        # Fondé / Non fondé / A vérifier
    service: Optional[str] = ""
    systeme: Optional[str] = ""
    needs_rag: bool = False
    needs_glpi: bool = False
