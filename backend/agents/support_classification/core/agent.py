"""
core/agent.py — Agent principal Maroclear v7.

Améliorations vs v6 :
  - UI complètement séparée de la logique métier
  - L'agent accepte des callables pour poser les questions (testable, extensible)
  - Interface orchestrateur propre : agent.run() retourne DeclarationResult
  - Mode batch sans modification de l'agent (même code, comportement différent)
  - Logging structuré à la place des print() dans la logique métier
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional, Callable

from core.models import DeclarationResult, TicketClass, TicketFiche, ServiceInfo
from core.utils import strip_html
from services.classifier import (
    extract_fields_from_text,
    run_classification,
    build_fiche,
)
from services.glpi_service import (
    detect_service,
    compute_glpi,
    get_service_by_code,
)

logger = logging.getLogger(__name__)


class ClassificationAgent:
    """
    Agent de classification Maroclear v7.

    Interface orchestrateur :
        agent = ClassificationAgent()
        result = agent.run(
            ticket_text,
            contexte_utilisateur={"rapporteur": "…", "activite": "…"},
        )
        payload = result.to_dict()

    En mode interactif, l'agent pose des questions via les callables par défaut (CLI).
    Pour l'intégrer dans une UI web/API, injecter des callables custom.
    """

    def run(
        self,
        ticket_text:          str,
        ticket_id:            Optional[str]  = None,
        contexte_utilisateur: Optional[dict] = None,
        # Callables injectables pour découpler UI et logique
        ask_question_fn:  Optional[Callable[[str], Optional[str]]] = None,
        ask_service_fn:   Optional[Callable[[], ServiceInfo]]      = None,
        ask_field_fn:     Optional[Callable[..., Optional[str]]]   = None,
        on_classification: Optional[Callable[[str, float, str], None]] = None,
        on_phase:          Optional[Callable[[str], None]]          = None,
    ) -> DeclarationResult:
        """
        Orchestre les 3 phases.

        Args:
            ticket_text:          Texte brut du ticket (HTML supporté)
            ticket_id:            Identifiant optionnel (auto-généré sinon)
            contexte_utilisateur: Dict {rapporteur, activite, nom_prenom, telephone}
            ask_question_fn:      fn(question: str) -> réponse | None
            ask_service_fn:       fn() -> ServiceInfo
            ask_field_fn:         fn(label, key, question, required) -> réponse | None
            on_classification:    callback(classe, confiance, justification)
            on_phase:             callback(phase_name: str)
        """
        ticket_id            = ticket_id or str(uuid.uuid4())[:8]
        clean_text           = strip_html(ticket_text)
        contexte_utilisateur = contexte_utilisateur or {}

        logger.info("Ticket [%s] — %d caractères", ticket_id, len(clean_text))

        # ── Phase 1 — Classification ──────────────────────────────────────────
        if on_phase:
            on_phase("classification")

        classif_result, nb_q_classif = run_classification(
            clean_text=clean_text,
            ask_question=ask_question_fn or (lambda q: None),
        )

        logger.info(
            "Classification : %s (%.0f%%)",
            classif_result.classe.value, classif_result.confiance * 100
        )

        if on_classification:
            on_classification(
                classif_result.classe.value,
                classif_result.confiance,
                classif_result.justification,
            )

        # ── Phase 2 — Extraction + Collecte ──────────────────────────────────
        if on_phase:
            on_phase("extraction")

        extracted = extract_fields_from_text(clean_text, classif_result.classe)
        logger.debug("Champs extraits : %s", list(k for k, v in extracted.items() if v))

        if on_phase:
            on_phase("collecte")

        fiche, nb_q_collecte = build_fiche(
            extracted=extracted,
            classe=classif_result.classe,
            clean_text=clean_text,
            contexte_utilisateur=contexte_utilisateur,
            ask_service=ask_service_fn or (lambda: get_service_by_code("10")),
            ask_field=ask_field_fn or (lambda *a, **kw: None),
        )

        result = DeclarationResult(
            ticket_id=ticket_id,
            classe=classif_result.classe,
            confiance=classif_result.confiance,
            justification=classif_result.justification,
            fiche=fiche,
            texte_original=clean_text,
            nb_q_classif=nb_q_classif,
            nb_q_collecte=nb_q_collecte,
        )

        logger.info(
            "Ticket [%s] terminé. Complet=%s. Total questions=%d",
            ticket_id, result.is_complete, nb_q_classif + nb_q_collecte
        )
        return result

    def run_batch(
        self,
        ticket_text:          str,
        ticket_id:            Optional[str]  = None,
        contexte_utilisateur: Optional[dict] = None,
    ) -> DeclarationResult:
        """
        Mode batch : aucune interaction, auto-détection maximale.
        Utilise le même agent.run() avec des callables silencieux.
        """
        from services.glpi_service import list_services

        # Service auto-détecté ou "Autre" en fallback
        def silent_ask_service() -> ServiceInfo:
            svc = detect_service(strip_html(ticket_text))
            return svc or get_service_by_code("10")

        return self.run(
            ticket_text=ticket_text,
            ticket_id=ticket_id,
            contexte_utilisateur=contexte_utilisateur,
            ask_question_fn=lambda q: None,   # skip toutes les questions
            ask_service_fn=silent_ask_service,
            ask_field_fn=lambda *a, **kw: None,
        )
