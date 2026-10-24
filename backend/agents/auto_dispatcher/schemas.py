"""
Schémas input/output de l'AutoDispatcherAgent
"""
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class TicketType(str, Enum):
    INCIDENT = "INCIDENT"
    DEMANDE = "DEMANDE"
    RECLAMATION = "RECLAMATION"


class DispatcherInput(BaseModel):
    ticket_type: TicketType
    priorite: Optional[str] = None       # P1 / P2 / P3 / P4
    service: Optional[str] = None
    systeme: Optional[str] = None
    description: str
    reporter_name: Optional[str] = None
    reporter_email: Optional[str] = None
    institution: Optional[str] = None
    conversation_summary: Optional[str] = None


class DispatcherOutput(BaseModel):
    success: bool
    ticket_id: Optional[str] = None
    email_sent: bool = False
    form_prefilled: bool = False
    message: str = ""
