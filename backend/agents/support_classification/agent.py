"""
support_classification/agent.py
================================
Agent de classification conversationnel Maroclear — version mergée v9.

Flux type-aware :
  - INCIDENT  → service + système + objet + description (skip date/freq/solution)
  - DEMANDE   → service + date + fréquence + description + solution
  - RECLAMATION → service + date + fréquence + description + solution

Fonctionnalités :
  - Classification LLM + règles déterministes prioritaires
  - Questions de clarification avec quick replies (boutons)
  - Demande de screenshots quand pertinent (erreurs visuelles, accès)
  - Détection automatique du service par type de ticket
  - Calcul priorité GLPI (matrice service × gravité) pour INCIDENT
  - Reformulation objet/description pour le formulaire
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Charger le .env local (OPENROUTER_API_KEY)
_AGENT_DIR = Path(__file__).parent
load_dotenv(_AGENT_DIR / ".env")

# Ajouter le dossier de l'agent au path
sys.path.insert(0, str(_AGENT_DIR))
sys.path.insert(0, str(_AGENT_DIR.parent.parent))

from shared.base.base_agent import BaseAgent
from shared.core.message import AgentMessage
from shared.core.agent_context import AgentContext
from shared.security import minimize_text_for_llm

from core.config import get_config
from core.models import TicketClass, ClassificationResult
from core.utils import strip_html
from services.classifier import (
    run_classification,
    extract_fields_from_text,
    reformulate_ticket_summary,
    get_next_question_key,
)
from services.glpi_service import detect_service, get_service_by_code, normalize

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# QUICK REPLIES (boutons cliquables côté frontend)
# ══════════════════════════════════════════════════════════════════════════════

QUICK_REPLIES_CLASSIFICATION = {
    "Q1_collectif": [
        "Dysfonctionnement technique / blocage",
        "Fichier metier inexploitable (vide, corrompu, errone)",
        "Erreur sur une facture ou donnee de facturation",
        "Demande d'action ou d'information",
    ],
    "Q2_contenu_type": [
        "Flux metier (AOE, RSM, RCQ, REQ, CFT)",
        "Facture / donnee de facturation",
    ],
    "Q3_token_cause": [
        "Panne de mon poste (token perdu)",
        "Nouveau materiel (changement de poste)",
    ],
    "Q4_action_ou_constat": [
        "Je souhaite une retransmission",
        "Je constate qu'il est manquant ou errone",
    ],
    "Q5_retransmission": [
        "Suite a une non-reception",
        "Demande generique",
    ],
    "Q6_suspens_actif": [
        "Suspens toujours en cours",
        "Prejudice deja subi",
    ],
    "Q7_screenshot": [
        "Oui, je vais joindre une capture",
        "Non, pas de message d'erreur visible",
    ],
}

QUICK_REPLIES_DATE = ["Aujourd'hui", "Hier", "Avant-hier"]
QUICK_REPLIES_FREQ = ["1 fois", "Recurrent", "Chaque jour"]
QUICK_REPLIES_SOLUTION = ["Passer"]


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _is_vague_problem_statement(text: str) -> bool:
    """Détecte les entrées trop génériques (< 5 mots + marqueurs vagues)."""
    text_norm = normalize(text)
    words = [w for w in text_norm.split() if w]
    vague_markers = {
        "probleme", "problem", "souci", "incident", "bug", "panne",
        "aide", "assistance",
    }
    return len(words) <= 5 and any(marker in text_norm for marker in vague_markers)


def _is_expected_document_not_received(text: str) -> bool:
    """Détecte si l'affilié parle d'un document attendu non reçu."""
    text_norm = normalize(text)
    patterns = [
        "deja attendu", "attendu et non recu",
        "document attendu", "document attendu et non recu",
    ]
    return any(pattern in text_norm for pattern in patterns)


def _should_ask_screenshot(text: str) -> bool:
    """Détermine si on doit demander une capture d'écran."""
    text_norm = normalize(text)
    screenshot_triggers = [
        "erreur", "message d'erreur", "page blanche", "bug",
        "ecran", "affichage", "bloque", "ne s'ouvre pas",
        "ne fonctionne pas", "ne repond pas", "inaccessible",
        "indisponible", "batch en cours", "erreur 500",
    ]
    return any(trigger in text_norm for trigger in screenshot_triggers)


def _get_service_replies(ticket_type: str) -> list[str]:
    """Retourne les labels de services selon le type de ticket."""
    cfg = get_config()
    services = cfg.get_services_for_type(ticket_type)
    return [svc["label"] for svc in services.values()]


def _find_service_by_label(label: str, ticket_type: str) -> Optional[dict]:
    """Trouve un service par son label dans le type donné."""
    cfg = get_config()
    services = cfg.get_services_for_type(ticket_type)
    label_norm = normalize(label)
    for code, svc in services.items():
        if normalize(svc["label"]) == label_norm or label_norm in normalize(svc["label"]):
            return {
                "code": code, "label": svc["label"],
                "system": svc.get("system", ""),
                "description": svc.get("description", ""),
                "auto_detected": False,
            }
    return None


def _get_target_path(classe: str) -> str:
    """Retourne le chemin frontend selon le type de ticket."""
    paths = {
        "INCIDENT":    "/incidents",
        "DEMANDE":     "/demandes/nouvelle",
        "RECLAMATION": "/reclamations/nouvelle",
    }
    return paths.get(classe.upper().replace("É", "E"), "/incidents")


# ══════════════════════════════════════════════════════════════════════════════
# ÉTATS DE SESSION
# ══════════════════════════════════════════════════════════════════════════════

STATE_CLASSIFYING      = "classifying"
STATE_COLLECT_SERVICE  = "collect_service"
STATE_COLLECT_DATE     = "collect_date"
STATE_COLLECT_FREQ     = "collect_freq"
STATE_COLLECT_DESC     = "collect_desc"
STATE_COLLECT_SOLUTION = "collect_solution"
STATE_DONE             = "done"


class ClassificationSession:
    """Maintient l'état d'une conversation de classification entre les tours HTTP."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = STATE_CLASSIFYING
        self.clean_text = ""
        self.conversation: list[dict] = []
        self.questions_seen: set[str] = set()
        self.nb_questions = 0
        self.classif_result: Optional[ClassificationResult] = None
        self.extracted: dict = {}
        self.fiche_data: dict = {}
        self.user_profile: dict = {}
        self.last_question_text: Optional[str] = None
        self.fallback_repeat_count: int = 0
        self.screenshot_asked: bool = False


# ══════════════════════════════════════════════════════════════════════════════
# AGENT PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

class SupportClassificationAgent(BaseAgent):
    """
    Agent conversationnel de classification.

    Deux interfaces :
      1. Via orchestrateur : process(message, context) — utilise AgentContext
      2. Via route /classify : classify(session_id, text, profile) — sessions internes
    """

    # Mots-clés pour le routage orchestrateur (can_handle)
    INCIDENT_KEYWORDS = [
        "bloque", "inaccessible", "impossible", "erreur",
        "dysfonctionnement", "probleme", "panne", "bug",
        "ne fonctionne pas", "ne marche pas", "indisponible",
        "incident", "tcs bancs", "mymaroclear ne",
        "page blanche", "erreur 500", "lenteur", "vide", "corrompu",
        "ne pouvons pas", "ne peux pas", "batch en cours", "pending",
    ]
    DEMANDE_KEYWORDS = [
        "demande", "besoin", "souhaite", "voudrais", "pouvez-vous",
        "retransmission", "reinitialisation", "pin", "token",
        "acces", "document", "releve", "merci de", "priere de",
        "je vous prie", "veuillez", "transmettre", "retransmettre",
        "communiquer", "mettre a disposition", "prolonger", "valider", "envoyer",
    ]
    RECLAMATION_KEYWORDS = [
        "reclamation", "insatisfait", "inacceptable", "contestation",
        "delai depasse", "toujours pas", "aucune reponse",
        "prejudice", "facture", "ecart", "errone", "incorrect",
        "manquant", "incomplet", "pas recu", "non recu", "ice faux",
    ]

    def __init__(self, config: Dict[str, Any]):
        super().__init__(agent_name="SupportClassificationAgent", config=config)
        self._sessions: Dict[str, ClassificationSession] = {}
        self._lock = threading.Lock()
        self.log("SupportClassificationAgent initialisé (v9 merge type-aware)")

    # ── Interface BaseAgent (pour l'orchestrateur) ────────────────────────────

    def can_handle(self, message: AgentMessage, context: AgentContext) -> bool:
        """Participe au routage de l'orchestrateur."""
        state = context.get_session_data("classif_state")
        if state and state != STATE_CLASSIFYING and state != STATE_DONE:
            return True

        query_lower = message.content.lower()
        doc_starters = [
            "qu'est-ce", "c'est quoi", "quelle est la definition",
            "comment fonctionne", "quel est le role", "quels sont les services",
            "comment devenir", "quelles sont les etapes",
        ]
        if any(s in query_lower for s in doc_starters):
            return False

        all_kw = self.INCIDENT_KEYWORDS + self.DEMANDE_KEYWORDS + self.RECLAMATION_KEYWORDS
        return any(kw in query_lower for kw in all_kw)

    def process(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
        """Interface orchestrateur — délègue à classify() avec session du contexte."""
        session_id = context.get_session_data("classif_session_id")
        if not session_id:
            session_id = str(uuid.uuid4())[:8]
            context.set_session_data("classif_session_id", session_id)

        user_profile = context.get_session_data("user_profile", {})
        result = self.classify(session_id, message.content, user_profile)

        # Stocker l'état dans le contexte pour can_handle()
        context.set_session_data("classif_state", result.get("state", STATE_DONE))

        # Construire la réponse AgentMessage
        response_text = result.get("question", "")
        if result.get("done"):
            response_text = "J'ai bien noté toutes les informations. Voici le récapitulatif de votre dossier."

        return AgentMessage.create_response(
            sender=self.agent_name,
            content=response_text,
            metadata={
                "classification":  result.get("classe", ""),
                "priorite":        result.get("priorite", ""),
                "service":         result.get("service", ""),
                "systeme":         result.get("service_system", ""),
                "needs_glpi":      result.get("classe") == "INCIDENT" and result.get("done", False),
                "form_data":       result.get("form_data"),
                "quick_replies":   result.get("quick_replies", []),
                "is_complete":     result.get("done", False),
                "agent_used":      self.agent_name,
                "confiance":       result.get("confiance", 0),
            },
        )

    # ── Gestion des sessions ──────────────────────────────────────────────────

    def _get_session(self, session_id: str) -> ClassificationSession:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = ClassificationSession(session_id)
            return self._sessions[session_id]

    def reset_session(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)

    # ══════════════════════════════════════════════════════════════════════════
    # POINT D'ENTRÉE PRINCIPAL — classify()
    # ══════════════════════════════════════════════════════════════════════════

    def classify(
        self,
        session_id:   str,
        user_text:    str,
        user_profile: Optional[dict] = None,
    ) -> dict:
        """
        Traite un tour de conversation.

        Returns dict avec :
          - done: bool
          - Si done=False : question (str), quick_replies (list), state (str)
          - Si done=True  : form_data (dict), classe, confiance, justification
        """
        session = self._get_session(session_id)
        session.user_profile = user_profile or {}
        clean_text = strip_html(user_text)

        if session.state == STATE_CLASSIFYING:
            return self._handle_classifying(session, clean_text)
        elif session.state == STATE_COLLECT_SERVICE:
            return self._handle_collect_service(session, clean_text)
        elif session.state == STATE_COLLECT_DATE:
            return self._handle_collect_date(session, clean_text)
        elif session.state == STATE_COLLECT_FREQ:
            return self._handle_collect_freq(session, clean_text)
        elif session.state == STATE_COLLECT_DESC:
            return self._handle_collect_desc(session, clean_text)
        elif session.state == STATE_COLLECT_SOLUTION:
            return self._handle_collect_solution(session, clean_text)
        else:
            # Session terminée ou état inconnu → reset et recommencer
            self.reset_session(session_id)
            session = self._get_session(session_id)
            session.user_profile = user_profile or {}
            return self._handle_classifying(session, clean_text)


    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 1 — CLASSIFICATION CONVERSATIONNELLE
    # ══════════════════════════════════════════════════════════════════════════

    def _handle_classifying(self, session: ClassificationSession, user_text: str) -> dict:
        """
        Lance ou continue run_classification() avec le texte courant.
        Si une question de clarification est nécessaire, la retourne au frontend.
        """
        cfg = get_config()

        # Détection de message trop vague → poser Q1
        if not session.clean_text and _is_vague_problem_statement(user_text):
            session.clean_text = user_text
            session.questions_seen.add("Q1_collectif")
            session.nb_questions += 1
            return {
                "done":          False,
                "question":      cfg.questions["Q1_collectif"],
                "quick_replies": QUICK_REPLIES_CLASSIFICATION.get("Q1_collectif", []),
                "state":         STATE_CLASSIFYING,
                "classe":        "AMBIGU",
                "confiance":     0.0,
                "justification": "Le message est trop général pour déterminer la nature du ticket.",
            }

        # Accumuler le texte au fil des tours
        if not session.clean_text:
            session.clean_text = user_text
        else:
            session.clean_text += "\n" + user_text

        # Construire l'historique minimise pour le LLM
        llm_user_text = minimize_text_for_llm(user_text, session.user_profile)
        if not session.conversation or session.conversation[-1]["role"] != "user":
            session.conversation.append({"role": "user", "content": llm_user_text})
        elif session.conversation[-1]["content"] != llm_user_text:
            session.conversation.append({"role": "user", "content": llm_user_text})

        # Callback pour capturer la question du LLM
        pending_question: dict = {"key": None, "text": None}

        def ask_question_fn(question_text: str) -> Optional[str]:
            for key, q in cfg.questions.items():
                if q.strip() == question_text.strip():
                    pending_question["key"] = key
                    pending_question["text"] = question_text
                    break
            else:
                pending_question["text"] = question_text
                pending_question["key"] = None
            return None  # Suspend — on retourne la question au frontend

        try:
            result, nb_q = run_classification(
                clean_text=session.clean_text,
                ask_question=ask_question_fn,
                initial_questions_seen=session.questions_seen,
                conversation_history=session.conversation,
                user_profile=session.user_profile,
            )
        except Exception as exc:
            logger.error("Erreur run_classification : %s", exc)
            return {
                "done":     False,
                "question": "Je n'ai pas pu analyser votre demande. Pouvez-vous reformuler ?",
                "quick_replies": [],
                "state":    STATE_CLASSIFYING,
                "error":    str(exc),
            }

        session.nb_questions += nb_q

        # ── Cas 1 : question de clarification nécessaire ──────────────────────
        if pending_question["text"] and not result.is_certain(cfg.certainty_threshold):
            key = pending_question["key"]
            quick_replies = QUICK_REPLIES_CLASSIFICATION.get(key, []) if key else []

            if key:
                session.questions_seen.add(key)

            session.classif_result = result
            session.last_question_text = pending_question["text"]
            session.fallback_repeat_count = 0

            logger.info(
                "Question posée [%s] : %s (confiance=%.0f%%)",
                key, pending_question["text"][:60], result.confiance * 100
            )

            return {
                "done":          False,
                "question":      pending_question["text"],
                "quick_replies": quick_replies,
                "state":         STATE_CLASSIFYING,
                "classe":        result.classe.value,
                "confiance":     round(result.confiance, 3),
                "justification": result.justification,
            }

        # ── Cas 2 : encore AMBIGU après LLM → fallback questions ─────────────
        if result.classe == TicketClass.AMBIGU:
            if _is_expected_document_not_received(session.clean_text):
                result = ClassificationResult(
                    classe=TicketClass.RECLAMATION,
                    confiance=max(result.confiance, 0.70),
                    justification="Document attendu confirmé comme non reçu → réclamation.",
                    ambiguite=None,
                    noeud_question=None,
                )
            else:
                fallback_key = get_next_question_key(
                    result.noeud_question or "",
                    normalize(session.clean_text),
                    session.questions_seen,
                )
                if fallback_key:
                    fallback_question = cfg.questions[fallback_key]
                    quick_replies = QUICK_REPLIES_CLASSIFICATION.get(fallback_key, [])
                    session.questions_seen.add(fallback_key)
                else:
                    fallback_question = self._build_contextual_question(session)
                    quick_replies = []

                if fallback_question == session.last_question_text:
                    fallback_question = self._build_contextual_question(session, repeated=True)
                    session.fallback_repeat_count += 1
                else:
                    session.fallback_repeat_count = 0

                session.last_question_text = fallback_question
                session.classif_result = result
                return {
                    "done":          False,
                    "question":      fallback_question,
                    "quick_replies": quick_replies,
                    "state":         STATE_CLASSIFYING,
                    "classe":        result.classe.value,
                    "confiance":     round(result.confiance, 3),
                    "justification": result.justification,
                }

        # ── Cas 3 : classification confiante → passer à la collecte ──────────
        session.classif_result = result
        logger.info("Classification : %s (%.0f%%)", result.classe.value, result.confiance * 100)

        # Extraction automatique des champs depuis le texte
        session.extracted = extract_fields_from_text(session.clean_text, result.classe, session.user_profile)

        # Déterminer le type pour la détection de service
        ticket_type = result.classe.value.lower().replace("é", "e")
        if ticket_type == "reclamation":
            ticket_type = "reclamation"

        # Tenter la détection automatique du service
        service = detect_service(session.clean_text, ticket_type)
        if service:
            session.fiche_data["service"] = service.to_dict()
            # Pour INCIDENT → demander screenshot si pertinent, puis passer à description
            if result.classe == TicketClass.INCIDENT:
                return self._transition_after_service_incident(session)
            else:
                # DEMANDE / RECLAMATION → collecter date
                session.state = STATE_COLLECT_DATE
                return self._ask_date(session)

        # Sinon demander le service
        session.state = STATE_COLLECT_SERVICE
        return self._ask_service(session)

    def _build_contextual_question(self, session: ClassificationSession, repeated: bool = False) -> str:
        """Retourne une question de classification adaptée au contexte."""
        if repeated:
            return (
                "Pour mieux qualifier votre déclaration, s'agit-il d'un incident technique/blocage, "
                "d'un fichier métier inexploitable, d'un contenu erroné ou d'une demande d'action/information ?"
            )
        return "Pouvez-vous préciser la nature exacte de votre déclaration ?"


    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 2 — COLLECTE CONVERSATIONNELLE (type-aware)
    # ══════════════════════════════════════════════════════════════════════════

    # ── SERVICE ───────────────────────────────────────────────────────────────

    def _ask_service(self, session: ClassificationSession) -> dict:
        """Demande le service concerné avec boutons selon le type de ticket."""
        classe = session.classif_result.classe.value
        ticket_type = classe.lower().replace("é", "e")
        services = _get_service_replies(ticket_type)
        return {
            "done":          False,
            "question":      "Quel service est concerné par votre demande ?",
            "quick_replies": services,
            "state":         STATE_COLLECT_SERVICE,
            "classe":        classe,
            "confiance":     round(session.classif_result.confiance, 3),
            "justification": session.classif_result.justification,
        }

    def _handle_collect_service(self, session: ClassificationSession, user_text: str) -> dict:
        """Traite la réponse de l'affilié pour le service."""
        classe = session.classif_result.classe.value
        ticket_type = classe.lower().replace("é", "e")

        # Détecter les réponses vagues → mapper à "Autres"
        vague_responses = [
            "je sais pas", "je ne sais pas", "aucune idee", "aucune idée",
            "je sais pas trop", "pas sur", "pas sûr", "je ne sais pas trop",
            "aucun", "rien", "je sais po", "sais pas", "jsp",
        ]
        text_norm = normalize(user_text)
        if any(normalize(v) in text_norm for v in vague_responses):
            # Tenter une dernière détection automatique depuis le texte initial
            service = detect_service(session.clean_text, ticket_type)
            if service:
                session.fiche_data["service"] = service.to_dict()
            else:
                fallback_code = "10" if ticket_type == "incident" else "R10" if ticket_type == "reclamation" else "D4"
                cfg = get_config()
                services = cfg.get_services_for_type(ticket_type)
                fallback_svc = services.get(fallback_code, {})
                session.fiche_data["service"] = {
                    "code": fallback_code,
                    "label": fallback_svc.get("label", "Autres"),
                    "system": fallback_svc.get("system", ""),
                    "description": fallback_svc.get("description", ""),
                    "auto_detected": False,
                }
        else:
            # Chercher le service par label
            found = _find_service_by_label(user_text, ticket_type)
            if found:
                session.fiche_data["service"] = found
            else:
                # Fallback : stocker tel quel avec code "Autre"
                session.fiche_data["service"] = {
                    "code": "10" if ticket_type == "incident" else "R10" if ticket_type == "reclamation" else "D4",
                    "label": user_text.strip(),
                    "system": "",
                    "description": "",
                    "auto_detected": False,
                }

        # Transition selon le type
        if session.classif_result.classe == TicketClass.INCIDENT:
            return self._transition_after_service_incident(session)
        else:
            session.state = STATE_COLLECT_DATE
            return self._ask_date(session)

    def _transition_after_service_incident(self, session: ClassificationSession) -> dict:
        """
        Pour un INCIDENT : après le service, raffiner le système si possible,
        demander un screenshot si pertinent, puis passer à la description.
        """
        # Raffiner le système détecté en fonction du texte
        service = session.fiche_data.get("service", {})
        text_norm = normalize(session.clean_text)
        if service.get("system") in ("MyMaroclear / TCS", ""):
            if any(kw in text_norm for kw in ["tcs bancs", "tcs banks", "tcs", "bancs"]):
                service["system"] = "TCS BaNCS"
            elif any(kw in text_norm for kw in ["mymaroclear", "my maroclear", "extranet"]):
                service["system"] = "MyMaroclear"
            session.fiche_data["service"] = service

        # Demander screenshot si pertinent et pas encore demandé
        if not session.screenshot_asked and _should_ask_screenshot(session.clean_text):
            session.screenshot_asked = True
            # Ne pas passer directement à DONE — demander plus de détails
            session.state = STATE_COLLECT_DESC
            return {
                "done":          False,
                "question": (
                    "Avez-vous un message d'erreur affiché à l'écran ? "
                    "Si oui, merci de joindre une capture d'écran via le bouton 📎.\n\n"
                    "Aussi, depuis quand ce problème se produit-il ? Est-ce que d'autres collègues sont impactés ?"
                ),
                "quick_replies": QUICK_REPLIES_CLASSIFICATION["Q7_screenshot"],
                "state":         STATE_COLLECT_DESC,
                "classe":        session.classif_result.classe.value,
                "confiance":     round(session.classif_result.confiance, 3),
                "justification": session.classif_result.justification,
            }

        # Sinon passer à la description
        session.state = STATE_COLLECT_DESC
        return self._ask_desc(session)

    # ── DATE (DEMANDE / RECLAMATION uniquement) ───────────────────────────────

    def _ask_date(self, session: ClassificationSession) -> dict:
        """Demande la date d'occurrence (skip si déjà extraite)."""
        if session.extracted.get("date_occurrence"):
            session.fiche_data["date_occurrence"] = session.extracted["date_occurrence"]
            session.state = STATE_COLLECT_FREQ
            return self._ask_freq(session)
        return {
            "done":          False,
            "question":      "Depuis quand ce problème se produit-il ?",
            "quick_replies": list(QUICK_REPLIES_DATE),
            "state":         STATE_COLLECT_DATE,
            "classe":        session.classif_result.classe.value,
            "confiance":     round(session.classif_result.confiance, 3),
            "justification": session.classif_result.justification,
        }

    def _handle_collect_date(self, session: ClassificationSession, user_text: str) -> dict:
        """Traite la réponse date."""
        from services.classifier import extract_date_local
        date = extract_date_local(user_text) or user_text.strip()
        session.fiche_data["date_occurrence"] = date
        session.state = STATE_COLLECT_FREQ
        return self._ask_freq(session)

    # ── FRÉQUENCE (DEMANDE / RECLAMATION uniquement) ──────────────────────────

    def _ask_freq(self, session: ClassificationSession) -> dict:
        """Demande la fréquence d'occurrence (skip si déjà extraite)."""
        if session.extracted.get("frequence_occurrence"):
            session.fiche_data["frequence_occurrence"] = session.extracted["frequence_occurrence"]
            session.state = STATE_COLLECT_DESC
            return self._ask_desc(session)
        return {
            "done":          False,
            "question":      "Ce problème se produit-il pour la première fois ou est-il récurrent ?",
            "quick_replies": list(QUICK_REPLIES_FREQ),
            "state":         STATE_COLLECT_FREQ,
            "classe":        session.classif_result.classe.value,
            "confiance":     round(session.classif_result.confiance, 3),
            "justification": session.classif_result.justification,
        }

    def _handle_collect_freq(self, session: ClassificationSession, user_text: str) -> dict:
        """Traite la réponse fréquence."""
        session.fiche_data["frequence_occurrence"] = user_text.strip()
        session.state = STATE_COLLECT_DESC
        return self._ask_desc(session)

    # ── DESCRIPTION ───────────────────────────────────────────────────────────

    def _ask_desc(self, session: ClassificationSession) -> dict:
        """Demande la description. Pour un INCIDENT, exige plus de détails si le texte est trop vague."""
        text = session.clean_text.strip()
        has_enough_detail = len(text) > 80 and any(
            kw in normalize(text) for kw in [
                "depuis", "message", "erreur", "capture", "screenshot",
                "ce matin", "hier", "aujourd'hui", "collegue", "tous",
            ]
        )

        if has_enough_detail:
            session.fiche_data["description"] = text
            if session.classif_result.classe == TicketClass.INCIDENT:
                session.state = STATE_DONE
                return self._build_result(session)
            else:
                session.state = STATE_COLLECT_SOLUTION
                return self._ask_solution(session)

        # Pour un INCIDENT avec peu de détails → poser des questions de diagnostic
        if session.classif_result.classe == TicketClass.INCIDENT:
            return {
                "done":          False,
                "question": (
                    "Pour mieux qualifier votre incident, pouvez-vous préciser :\n"
                    "- Depuis quand le problème se produit-il ?\n"
                    "- Y a-t-il un message d'erreur affiché ?\n"
                    "- Le problème concerne-t-il uniquement vous ou d'autres collègues aussi ?"
                ),
                "quick_replies": ["Depuis ce matin", "Depuis hier", "Pas de message d'erreur"],
                "state":         STATE_COLLECT_DESC,
                "classe":        session.classif_result.classe.value,
                "confiance":     round(session.classif_result.confiance, 3),
                "justification": session.classif_result.justification,
            }

        # Pour DEMANDE/RECLAMATION avec texte suffisant
        if len(text) > 30:
            session.fiche_data["description"] = text
            session.state = STATE_COLLECT_SOLUTION
            return self._ask_solution(session)

        return {
            "done":          False,
            "question":      "Pouvez-vous décrire le problème plus en détail ?",
            "quick_replies": [],
            "state":         STATE_COLLECT_DESC,
            "classe":        session.classif_result.classe.value,
            "confiance":     round(session.classif_result.confiance, 3),
            "justification": session.classif_result.justification,
        }

    def _handle_collect_desc(self, session: ClassificationSession, user_text: str) -> dict:
        """Traite la réponse description — combine avec le contexte initial."""
        # Accumuler le texte dans la session
        session.clean_text += "\n" + user_text
        # La description = tout le contexte de la conversation
        session.fiche_data["description"] = session.clean_text.strip()

        # Si l'affilié mentionne un message d'erreur et n'a pas encore joint de capture
        text_norm = normalize(user_text)
        mentions_error = any(kw in text_norm for kw in [
            "message d'erreur", "message erreur", "erreur affichee",
            "oui il ya", "oui message", "oui erreur",
        ])

        if mentions_error and not session.screenshot_asked:
            session.screenshot_asked = True
            return {
                "done":          False,
                "question": (
                    "Merci. Pouvez-vous joindre une capture d'écran du message d'erreur "
                    "via le bouton 📎 ? Cela nous aidera à diagnostiquer le problème plus rapidement."
                ),
                "quick_replies": ["Je joins une capture", "Pas de capture disponible"],
                "state":         STATE_COLLECT_DESC,
                "classe":        session.classif_result.classe.value,
                "confiance":     round(session.classif_result.confiance, 3),
                "justification": session.classif_result.justification,
            }

        # Pour INCIDENT → terminé (pas de solution à demander)
        if session.classif_result.classe == TicketClass.INCIDENT:
            session.state = STATE_DONE
            return self._build_result(session)

        # Pour DEMANDE / RECLAMATION → demander la solution attendue
        session.state = STATE_COLLECT_SOLUTION
        return self._ask_solution(session)

    # ── SOLUTION (DEMANDE / RECLAMATION uniquement) ───────────────────────────

    def _ask_solution(self, session: ClassificationSession) -> dict:
        """
        Pour DEMANDE/RECLAMATION : génère automatiquement la solution attendue via LLM.
        Ne demande PAS à l'affilié — on déduit la solution du contexte.
        """
        from services.llm_client import call_llm

        # Générer la solution via LLM
        prompt = (
            "À partir de la déclaration suivante d'un affilié Maroclear, "
            "déduis en UNE phrase l'action attendue de la part de Maroclear.\n"
            "Formule la solution de manière directe et actionnable.\n"
            "Exemples :\n"
            "- 'Token perdu suite à panne' → 'Génération et envoi d'un nouveau token RSA'\n"
            "- 'Facture au mauvais nom' → 'Correction et réémission de la facture au nom correct'\n"
            "- 'AOE non reçus depuis le 15/05' → 'Retransmission des AOE manquants via CFT'\n"
            "- 'Réinitialisation mot de passe' → 'Réinitialisation du mot de passe TCS BaNCS'\n\n"
            "Retourne UNIQUEMENT la phrase de solution, sans JSON, sans explication.\n\n"
            f"Déclaration : {minimize_text_for_llm(session.clean_text, session.user_profile).strip()}"
        )

        try:
            result = call_llm(
                [{"role": "user", "content": prompt}],
                system="Tu es un assistant qui déduit l'action attendue. Réponds en une seule phrase."
            )
            if isinstance(result, dict):
                solution = str(result.get("solution", result.get("content", "")))
            else:
                solution = str(result)
            solution = solution.strip().strip('"\'')
        except Exception:
            # Fallback : déduire une solution simple du contexte
            solution = self._fallback_solution(session.clean_text)

        session.fiche_data["solution"] = solution
        session.state = STATE_DONE
        return self._build_result(session)

    def _fallback_solution(self, text: str) -> str:
        """Génère une solution basique en fallback (sans LLM)."""
        text_norm = normalize(text)
        if any(kw in text_norm for kw in ["token", "rsa", "certificat"]):
            return "Génération et envoi d'un nouveau token/certificat RSA"
        if any(kw in text_norm for kw in ["mot de passe", "password", "reinitialisation"]):
            return "Réinitialisation du mot de passe TCS BaNCS"
        if any(kw in text_norm for kw in ["aoe", "retransmission", "transmettre", "non recu"]):
            return "Retransmission des documents manquants"
        if any(kw in text_norm for kw in ["facture", "ice", "montant"]):
            return "Correction et réémission de la facture"
        if any(kw in text_norm for kw in ["solde", "position", "releve"]):
            return "Communication des données demandées"
        return "Traitement de la demande par le service concerné"


    # ══════════════════════════════════════════════════════════════════════════
    # RÉSULTAT FINAL — Construction du form_data
    # ══════════════════════════════════════════════════════════════════════════

    def _build_result(self, session: ClassificationSession) -> dict:
        """
        Construit le form_data final.
        - Pour INCIDENT : calcule la priorité GLPI via la matrice
        - Pour DEMANDE/RECLAMATION : priorité = "Qualifiée par dispatcher"
        - Reformule objet + description pour le formulaire
        """
        from services.glpi_service import compute_glpi

        classif  = session.classif_result
        fiche    = session.fiche_data
        profile  = session.user_profile
        service  = fiche.get("service", {})
        desc     = fiche.get("description", session.clean_text)

        # Reformuler objet + description
        summary = reformulate_ticket_summary(
            text=desc or session.clean_text,
            classe=classif.classe,
            service_label=service.get("label", ""),
            date_occurrence=fiche.get("date_occurrence", ""),
            frequence_occurrence=fiche.get("frequence_occurrence", ""),
            user_profile=profile,
        )

        # Calcul priorité GLPI (uniquement pour INCIDENT)
        service_code = service.get("code", "10")
        if classif.classe == TicketClass.INCIDENT:
            glpi = compute_glpi(service_code, desc or session.clean_text)
            priorite = glpi.priorite.value if hasattr(glpi.priorite, 'value') else str(glpi.priorite)
            urgence  = glpi.urgence
            impact   = glpi.impact
            gravite  = glpi.gravite_detectee
        else:
            # DEMANDE / RECLAMATION → priorité qualifiée par le dispatcher
            priorite = "Qualifiee par dispatcher"
            urgence  = "À qualifier"
            impact   = "À qualifier"
            gravite  = ""

        form_data = {
            "ticket_id":           "TKT-" + str(uuid.uuid4())[:8].upper(),
            "type":                classif.classe.value,
            "serviceConcerne":     service.get("label", ""),
            "systemeImpacte":      service.get("system", ""),
            "service_code":        service_code,
            "objet":               summary["objet"],
            "description":         summary["description"],
            # Champs DEMANDE / RECLAMATION
            "dateOccurrence":      fiche.get("date_occurrence", ""),
            "frequenceOccurrence": fiche.get("frequence_occurrence", ""),
            "solution":            fiche.get("solution", ""),
            # Documents
            "documentsJoints":     [],
            # Priorité GLPI (pour dispatcher — pas affiché à l'affilié)
            "priorite":            priorite,
            "urgence":             urgence,
            "impact":              impact,
            "gravite":             gravite,
            # Profil utilisateur
            "reporterName":        profile.get("reporterName", ""),
            "reporterActivity":    profile.get("reporterActivity", ""),
            "institution":         profile.get("institution", ""),
            "reporterEmail":       profile.get("reporterEmail", ""),
            "reporterPhone":       profile.get("reporterPhone", ""),
        }

        logger.info(
            "Session [%s] terminée : %s | Service=%s | Priorité=%s",
            session.session_id, classif.classe.value,
            service.get("label", "?"), priorite
        )

        return {
            "done":           True,
            "classe":         classif.classe.value,
            "confiance":      round(classif.confiance, 3),
            "justification":  classif.justification,
            "service":        service.get("label", ""),
            "service_system": service.get("system", ""),
            "service_code":   service_code,
            "priorite":       priorite,
            "urgence":        urgence,
            "impact":         impact,
            "gravite":        gravite,
            "form_data":      form_data,
            "state":          STATE_DONE,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # CAPACITÉS
    # ══════════════════════════════════════════════════════════════════════════

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "agent_name":  self.agent_name,
            "description": "Classification conversationnelle MyMaroclear (INCIDENT/DEMANDE/RÉCLAMATION)",
            "version":     "v9-merge-type-aware",
            "handles": [
                "Classification LLM + règles déterministes prioritaires",
                "Questions de clarification avec quick replies (boutons)",
                "Demande de screenshots quand pertinent",
                "Collecte type-aware : INCIDENT (service+desc) vs DEMANDE/RECLAMATION (service+date+freq+desc+solution)",
                "Détection automatique du service par type de ticket",
                "Calcul priorité GLPI (P1-P4) par matrice service × gravité (INCIDENT uniquement)",
                "Reformulation objet/description pour le formulaire",
                "Sessions par affilié avec état persistant entre les tours",
            ],
        }
