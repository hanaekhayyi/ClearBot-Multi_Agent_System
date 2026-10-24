"""
core/models.py — Modèles de données Maroclear v7
Typage strict, validation Pydantic, immutabilité.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ── Énumérations ──────────────────────────────────────────────────────────────

class TicketClass(str, Enum):
    INCIDENT    = "INCIDENT"
    DEMANDE     = "DEMANDE"
    RECLAMATION = "RÉCLAMATION"
    AMBIGU      = "AMBIGU"

    @classmethod
    def from_str(cls, value: str) -> "TicketClass":
        """Parse flexible : gère accents manquants et casse.
        Lève ValueError si la valeur est inconnue (pas de fallback silencieux).
        """
        mapping = {
            "INCIDENT":    cls.INCIDENT,
            "DEMANDE":     cls.DEMANDE,
            "RÉCLAMATION": cls.RECLAMATION,
            "RECLAMATION": cls.RECLAMATION,
            "AMBIGU":      cls.AMBIGU,
        }
        key = value.strip().upper()
        if key not in mapping:
            raise ValueError(
                f"Classe de ticket inconnue : '{value}'. "
                f"Valeurs acceptées : {list(mapping.keys())}"
            )
        return mapping[key]


class GlpiPriority(str, Enum):
    P1 = "P1 Majeur"
    P2 = "P2 Tres haute"
    P3 = "P3 Moyenne"
    P4 = "P4 Basse"
    DISPATCHER = "Qualifiee par dispatcher"


# ── Modèles de données ────────────────────────────────────────────────────────

@dataclass
class GlpiInfo:
    urgence:          str
    impact:           str
    priorite:         GlpiPriority | str
    gravite_detectee: str
    confidence:       float = 1.0  # 1.0 = détecté par règle, <1 = fallback

    def to_dict(self) -> dict:
        return {
            "urgence":          self.urgence,
            "impact":           self.impact,
            "priorite":         str(self.priorite),
            "gravite_detectee": self.gravite_detectee,
            "confidence":       self.confidence,
        }


@dataclass
class ServiceInfo:
    code:        str
    label:       str
    system:      str
    description: str
    auto_detected: bool = False

    def to_dict(self) -> dict:
        return {
            "code":         self.code,
            "label":        self.label,
            "system":       self.system,
            "auto_detected": self.auto_detected,
        }


@dataclass
class ClassificationResult:
    """Résultat brut d'une passe de classification LLM."""
    classe:        TicketClass
    confiance:     float
    justification: str
    ambiguite:     Optional[str]       = None
    noeud_question: Optional[str]      = None

    def is_certain(self, threshold: float) -> bool:
        return self.confiance >= threshold and not self.ambiguite

    @classmethod
    def from_dict(cls, data: dict) -> "ClassificationResult":
        classe_raw = data.get("classe", "INCIDENT")
        try:
            classe = TicketClass.from_str(classe_raw)
        except ValueError:
            # Fallback explicite uniquement ici, après validation externe
            classe = TicketClass.INCIDENT
        return cls(
            classe=classe,
            confiance=float(data.get("confiance", 0.0)),
            justification=str(data.get("justification", "")),
            ambiguite=data.get("ambiguite") or None,
            noeud_question=data.get("noeud_question") or None,
        )


@dataclass
class TicketFiche:
    """Fiche de collecte complète d'un ticket."""
    service:              Optional[ServiceInfo]  = None
    date_occurrence:      Optional[str]          = None
    frequence_occurrence: Optional[str]          = None
    description:          Optional[str]          = None
    solution_proposee:    Optional[str]          = None
    documents_joints:     list[str]              = field(default_factory=list)
    glpi:                 Optional[GlpiInfo]     = None

    # Champs auto-injectés (contexte utilisateur)
    rapporteur: Optional[str] = None
    activite:   Optional[str] = None
    nom_prenom: Optional[str] = None
    telephone:  Optional[str] = None

    @property
    def required_fields_complete(self) -> bool:
        return all([
            self.service is not None,
            self.date_occurrence,
            self.frequence_occurrence,
            self.description,
        ])

    @property
    def missing_required(self) -> list[str]:
        missing = []
        if not self.service:             missing.append("service_concerne")
        if not self.date_occurrence:     missing.append("date_occurrence")
        if not self.frequence_occurrence: missing.append("frequence_occurrence")
        if not self.description:         missing.append("description")
        return missing

    def to_dict(self) -> dict:
        return {
            "service":              self.service.to_dict() if self.service else None,
            "date_occurrence":      self.date_occurrence,
            "frequence_occurrence": self.frequence_occurrence,
            "description":          self.description,
            "solution_proposee":    self.solution_proposee,
            "documents_joints":     self.documents_joints,
            "glpi":                 self.glpi.to_dict() if self.glpi else None,
            "rapporteur":           self.rapporteur,
            "activite":             self.activite,
            "nom_prenom":           self.nom_prenom,
            "telephone":            self.telephone,
        }


@dataclass
class DeclarationResult:
    """Résultat final — interface vers l'orchestrateur."""
    ticket_id:            str
    classe:               TicketClass
    confiance:            float
    justification:        str
    fiche:                TicketFiche
    texte_original:       str
    corrige_manuellement: bool       = False
    nb_q_classif:         int        = 0
    nb_q_collecte:        int        = 0
    timestamp:            datetime   = field(default_factory=datetime.now)

    @property
    def is_complete(self) -> bool:
        return self.fiche.required_fields_complete

    def to_dict(self) -> dict:
        return {
            "ticket_id":             self.ticket_id,
            "classe":                self.classe.value,
            "confiance":             round(self.confiance, 3),
            "justification":         self.justification,
            "fiche":                 self.fiche.to_dict(),
            "texte_original":        self.texte_original[:500],
            "corrige_manuellement":  self.corrige_manuellement,
            "nb_q_classif":          self.nb_q_classif,
            "nb_q_collecte":         self.nb_q_collecte,
            "is_complete":           self.is_complete,
            "missing_fields":        self.fiche.missing_required,
            "timestamp":             self.timestamp.isoformat(),
        }

    @classmethod
    def new_id(cls) -> str:
        return str(uuid.uuid4())[:8]


# ── Exceptions ────────────────────────────────────────────────────────────────

class ClassifierError(Exception):
    """Erreur générique de classification."""

class LLMError(ClassifierError):
    """Erreur côté appel LLM."""
    def __init__(self, message: str, status_code: Optional[int] = None, retryable: bool = True):
        super().__init__(message)
        self.status_code = status_code
        self.retryable   = retryable

class ConfigError(ClassifierError):
    """Erreur de configuration (YAML manquant, champ absent…)."""

class ValidationError(ClassifierError):
    """Réponse LLM invalide ou incohérente."""
