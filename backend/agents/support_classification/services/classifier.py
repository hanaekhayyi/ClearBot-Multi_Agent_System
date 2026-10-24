"""
services/classifier.py — Logique de classification et collecte.

Améliorations vs v6 :
  - Prompts construits dynamiquement depuis la config (pas de chaînes hardcodées)
  - Validation stricte de la réponse LLM (classe, confiance, types)
  - Extraction locale améliorée (date, fréquence, description)
  - Séparation claire phase1 / phase2 / extraction
  - Logging structuré
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional

from core.config import get_config
from core.models import (
    ClassificationResult, DeclarationResult, TicketClass,
    TicketFiche, ValidationError,
)
from services.glpi_service import compute_glpi, detect_service, normalize
from services.llm_client import call_llm
from shared.security import minimize_text_for_llm

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# CONSTRUCTION DES PROMPTS (depuis YAML, pas hardcodés)
# ══════════════════════════════════════════════════════════════════════════════

_BUSINESS_RULES = """
ARBRE DE DECISION — CLASSIFICATION MAROCLEAR
=============================================

ETAPE 1 : Identifier la NATURE du message

A) DYSFONCTIONNEMENT TECHNIQUE → INCIDENT
   - Plateforme inaccessible (page blanche, erreur 500, ne repond pas)
   - Fichiers recus vides ou corrompus (CFT, flux metier)
   - Bug generalise, lenteur extreme bloquante
   - Utilisateur bloque dans une action habituelle (saisie impossible, "Batch en cours")
   - Statuts errones sans action de l'affilie (ex: "Pending for Fund Transfer" alors que cash disponible)
   - Document/donnee METIER recu avec erreur (AOE errone, RSM vide, RCQ incomplet)
   - Document/donnee METIER attendu et non recu (si c'est un flux metier = probleme systeme)

B) CONTENU ERRONE COTE FACTURATION → RECLAMATION
   - Facture incorrecte (montant, quantite, droit d'admission, TVA, ICE faux)
   - Ecart de donnees comptables (position != reel, solde incorrect)
   - Document/donnee lie a la FACTURATION manquant ou errone

C) ACTION / INFORMATION SOLLICITEE → DEMANDE
   - L'affilie demande activement quelque chose : "merci de", "priere de", "veuillez"
   - Retransmission demandee : "veuillez nous transmettre", "retransmettre"
   - Token perdu suite a incident materiel (probleme COTE AFFILIE, pas cote depositaire)
   - Nouveau token/certificat suite a changement de poste
   - Extraction de donnees, traitement exceptionnel
   - "Mettre a disposition" un document specifique

D) CAS AMBIGUS → poser une question de clarification
   - "Nous n'avons pas recu le fichier RSM/AOE" SANS precision sur la cause
     → Poser Q4_action_ou_constat : veut-il une retransmission (DEMANDE) ou constate-t-il un manque (INCIDENT/RECLAMATION) ?
   - Si constat de manque → Poser Q2_contenu_type : flux metier (INCIDENT) ou facture (RECLAMATION) ?

REGLE CLE — DISTINCTION DOCUMENT METIER vs FACTURE :
- Document METIER (AOE, RSM, RCQ, REQ, RMQ, flux CFT, fichier comptable fin de journee) manquant/errone → INCIDENT
- Document FACTURATION (facture, montant, TVA, ICE, droit d'admission) manquant/errone → RECLAMATION
- "Veuillez nous transmettre/retransmettre..." (demande active) → DEMANDE

REGLES IMPERATIVES :
- IGNORER les mots forts (incident, urgent, panne) → analyser ce qui est REELLEMENT decrit
- Ne JAMAIS demander a l'affilie si le probleme impacte d'autres affilies (il ne sait pas)
- Si bug/erreur visuelle → demander une capture d'ecran (Q7_screenshot)
- Token perdu apres panne materielle (cote affilie) → DEMANDE (pas incident cote depositaire)
"""

_FEW_SHOT = """
EXEMPLES VALIDES PAR LE DISPATCHER :
"Merci de nous communiquer le solde au 31/12/2025." → DEMANDE (demande d'information comptable)
"Suite au changement de mon poste, je vous prie de m'envoyer un nouveau Token." → DEMANDE (nouveau materiel)
"Merci de valider les AOE tardifs de la journee du 04/03/2026." → DEMANDE (traitement exceptionnel — demande active sur fichier metier)
"Merci de prolonger le flux avec les affilies jusqu'a 23h." → DEMANDE (extension de service)
"Bonjour, mon poste a subi une deterioration, j'ai perdu mon Token RSA." → DEMANDE (probleme cote affilie)
"Merci de mettre a notre disposition l'avis d'opere avec reference X." → DEMANDE (demande active de mise a disposition)
"Pouvez-vous nous retransmettre les AOE du 20/05 ? Nous ne les avons pas recus." → DEMANDE (demande active de retransmission — meme si AOE = fichier metier)
"Merci de nous retransmettre le fichier CFT du 10/05." → DEMANDE (demande active = retransmission)
"La facture comporte une erreur au niveau de la quantite du droit d'admission." → RECLAMATION (facture erronee)
"Nous avons constate un ecart : la position devrait etre X mais MCL affiche Y." → RECLAMATION (ecart donnees)
"Nous contestons le rejet de notre operation de transfert sans justification." → RECLAMATION (contestation)
"Nous avons subi un prejudice financier suite a un retard de denouement non justifie." → RECLAMATION (prejudice passe)
"Nous n'avons toujours pas recu de reponse a notre demande. C'est inacceptable." → RECLAMATION (insatisfaction, delai depasse)
"Le montant des droits de garde ne correspond pas au bareme. Nous contestons." → RECLAMATION (contestation facturation)
"Nous n'avons pas recu le fichier RSM (118) de ce jour." → INCIDENT (fichier metier non recu, sans demande active)
"Le fichier RCQ du 22/05 n'a pas ete recu. Est-ce un probleme de votre cote ?" → INCIDENT (fichier metier non recu = probleme systeme)
"Nous ne recevons pas la totalite des avis d'opere." → INCIDENT (non-reception fichier metier sans demande active)
"Nous n'arrivons pas a acceder aux plateformes TCS BANKS." → INCIDENT (plateforme inaccessible)
"Nous ne pouvons pas saisir les operations OTC. Message d'erreur : Batch en cours." → INCIDENT (blocage systeme)
"Les fichiers CFT se font mais sont vides." → INCIDENT (fichiers metier vides = probleme technique)
"Toutes nos operations affichent Pending for Fund Transfer alors que le cash est disponible." → INCIDENT (statut errone)
"Le module de reporting genere des fichiers Excel vides." → INCIDENT (fichiers vides = dysfonctionnement technique)
"""


def _build_system_prompt() -> str:
    cfg       = get_config()
    threshold = cfg.certainty_threshold
    q_keys    = ", ".join(cfg.questions.keys())

    return f"""Tu es un expert senior en classification de tickets MyMaroclear.
Tu appliques rigoureusement les règles officielles validées.

{_BUSINESS_RULES}

{_FEW_SHOT}

FORMAT DE RÉPONSE JSON STRICT (sans markdown, sans texte autour) :
{{
  "classe": "INCIDENT" | "DEMANDE" | "RÉCLAMATION" | "AMBIGU",
  "confiance": <float 0.0-1.0>,
  "justification": "<raisonnement précis 1-2 phrases>",
  "ambiguite": "<aspect ambigu précis, ou null si confiance >= {threshold}>",
  "noeud_question": "<clé parmi : {q_keys} — ou null>"
}}

RÈGLES IMPÉRATIVES :
- IGNORER les mots forts (incident, urgent, panne) → analyser ce qui est RÉELLEMENT décrit.
- Problème technique pour un seul ou plusieurs utilisateurs → INCIDENT.
- Si l'utilisateur ne peut plus réaliser une action habituelle → INCIDENT.
- Token perdu après panne matérielle (côté affilié) → DEMANDE.
- Document metier (AOE/RSM/RCQ/REQ/CFT) non recu ou errone → verifier si constat ou demande active.
  Si "veuillez transmettre/retransmettre" → DEMANDE.
  Si "nous n'avons pas recu" / "errone" / "vide" → poser Q2_contenu_type pour distinguer metier (INCIDENT) vs facture (RECLAMATION).
- Fichier métier erroné, vide, corrompu, illisible → INCIDENT.
- Contenu erroné dans une facture (montant, quantité, TVA, ICE) → RÉCLAMATION.
- Ne JAMAIS demander si le probleme impacte d'autres affilies.
- Si bug/erreur visuelle → suggerer Q7_screenshot (capture d'ecran).
"""


@lru_cache(maxsize=1)
def _get_cached_system_prompt() -> str:
    """
    Retourne le prompt système mis en cache.
    Le cache est invalidé si la config change (reload_config).
    Appeler _get_cached_system_prompt.cache_clear() après reload_config().
    """
    return _build_system_prompt()


_EXTRACTOR_SYSTEM = """Tu es un assistant chargé d'extraire des informations structurées.
Analyse le texte et extrait uniquement ce qui est EXPLICITEMENT présent.
Si un champ n'est pas mentionné, retourne null.
Réponds UNIQUEMENT en JSON pur, sans markdown, sans texte autour."""


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACTION LOCALE (sans LLM)
# ══════════════════════════════════════════════════════════════════════════════

def _format_date(dt: datetime) -> str:
    return dt.strftime("%d/%m/%Y")


def extract_date_local(text: str) -> Optional[str]:
    """Extrait une date depuis le texte (regex + mots relatifs)."""
    # JJ/MM/AAAA ou JJ-MM-AAAA
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", text)
    if m:
        day, month, year = m.groups()
        year = "20" + year if len(year) == 2 else year
        return f"{int(day):02d}/{int(month):02d}/{year}"

    # AAAA-MM-JJ
    m = re.search(r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b", text)
    if m:
        year, month, day = m.groups()
        return f"{int(day):02d}/{int(month):02d}/{year}"

    today    = datetime.now()
    text_low = normalize(text)
    if any(t in text_low for t in ["ce matin", "aujourd'hui", "ce jour"]):
        return _format_date(today)
    if any(t in text_low for t in ["avant-hier", "avant hier"]):
        return _format_date(today - timedelta(days=2))
    if "hier" in text_low:
        return _format_date(today - timedelta(days=1))

    return None


def extract_frequency_local(text: str) -> Optional[str]:
    """Extrait la fréquence d'occurrence depuis le texte."""
    text_low = normalize(text)
    rules = [
        (["chaque jour", "tous les jours", "quotidien"],         "Chaque jour"),
        (["chaque semaine", "toutes les semaines", "hebdomadaire"], "Chaque semaine"),
        (["chaque mois", "tous les mois", "mensuel"],            "Chaque mois"),
        (["recurrent", "plusieurs fois", "se repete"],           "Récurrent"),
        (["une seule fois", "1 fois", "ponctuel", "premiere fois"], "1 fois"),
    ]
    for keywords, value in rules:
        if any(kw in text_low for kw in keywords):
            return value
    if any(t in text_low for t in ["depuis ce matin", "depuis aujourd'hui"]):
        return "1 fois"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACTION LLM
# ══════════════════════════════════════════════════════════════════════════════

def extract_fields_from_text(
    text: str,
    classe: TicketClass,
    user_profile: dict | None = None,
) -> dict:
    """
    Extrait les champs de la fiche depuis le texte initial.
    Combine extraction locale (rapide, sans API) et LLM (pour les champs complexes).
    En cas d'erreur LLM, retourne seulement l'extraction locale.
    """
    local = {
        "date_occurrence":      extract_date_local(text),
        "frequence_occurrence": extract_frequency_local(text),
        "description":          text.strip() or None,
    }

    llm_text = minimize_text_for_llm(text, user_profile)

    prompt = (
        f"Ticket (classe : {classe.value}) :\n\"{llm_text}\"\n\n"
        "Extrais uniquement les champs présents :\n"
        "- date_occurrence : date du problème\n"
        "- frequence_occurrence : fréquence (1 fois, récurrent, chaque jour…)\n"
        "- description : résumé structuré du problème\n"
        "- solution_proposee : action attendue par l'utilisateur\n"
        "- documents_joints : liste de références documentaires mentionnées\n\n"
        "JSON uniquement. null si absent."
    )

    try:
        llm_result = call_llm([{"role": "user", "content": prompt}], system=_EXTRACTOR_SYSTEM)
    except Exception as exc:
        logger.warning("Extraction LLM échouée, fallback local : %s", exc)
        return local

    merged = dict(local)
    for key, value in llm_result.items():
        if not value or str(value).strip() in ("null", "None", ""):
            continue
        # Ne pas écraser une extraction locale fiable sur les dates/fréquences
        if key in ("date_occurrence", "frequence_occurrence") and local.get(key):
            continue
        if key == "description":
            # Garder la plus longue (souvent la locale = texte complet)
            if len(str(value)) >= len(str(local.get("description") or "")):
                merged[key] = value
            continue
        if key == "documents_joints" and isinstance(value, (str, list)):
            if isinstance(value, str):
                merged[key] = [p.strip() for p in re.split(r"[,;]", value) if p.strip()]
            else:
                merged[key] = [str(v) for v in value if v]
        else:
            merged[key] = value

    return merged


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def _validate_classification_response(data: dict) -> ClassificationResult:
    """Valide strictement la réponse de classification LLM."""
    cfg = get_config()

    if "classe" not in data:
        raise ValidationError("Champ 'classe' manquant dans la réponse LLM.")

    classe_raw = str(data.get("classe", "")).strip().upper()
    valid      = [c.upper() for c in cfg.valid_classes] + ["AMBIGU", "RÉCLAMATION", "RECLAMATION"]
    if classe_raw.replace("É", "E") not in [v.replace("É", "E") for v in valid]:
        raise ValidationError(f"Classe invalide : '{classe_raw}'. Valides : {cfg.valid_classes}")

    confiance = float(data.get("confiance", 0.0))
    if not 0.0 <= confiance <= 1.0:
        logger.warning("Confiance hors [0,1] : %s — normalisée.", confiance)
        confiance = max(0.0, min(1.0, confiance))

    return ClassificationResult.from_dict({**data, "confiance": confiance})


def _get_question_for_ticket(
    noeud:          str,
    text_norm:      str,
    questions_seen: set[str],
) -> Optional[str]:
    """
    Choisit la question de clarification la plus pertinente.
    Vérifie que les mots-clés déclencheurs sont présents dans le texte.
    """
    cfg      = get_config()
    triggers = cfg.question_triggers

    # Vérifie que le noeud suggéré est pertinent pour ce texte
    if noeud and noeud in triggers:
        if any(normalize(kw) in text_norm for kw in triggers[noeud]):
            if noeud not in questions_seen:
                return noeud

    # Fallback Q1 si pas encore posée
    if "Q1_collectif" not in questions_seen:
        return "Q1_collectif"

    # Cherche la première question non posée et pertinente
    for key, keywords in triggers.items():
        if key in questions_seen:
            continue
        if not keywords or any(normalize(kw) in text_norm for kw in keywords):
            return key

    return None


def _matches_any(text_norm: str, keywords: list[str]) -> bool:
    return any(normalize(kw) in text_norm for kw in keywords)


# ── Mots-clés pour classification par règles prioritaires ─────────────────────

BUSINESS_FILE_KEYWORDS = [
    "fichier metier", "fichiers metier", "flux metier",
    "aoe", "aoes", "aeos", "avis d'opere", "avis d'operation",
    "are", "arc", "arcs", "aoc",
    "rmq", "rsm", "rcq", "req", "mrb",
    "mt547", "swift", "cft",
    "releve mensuel quantitatif", "rapport de synthese mensuel",
    "donnees journee boursiere", "donnees de la journee boursiere",
    "position titre", "positions titres", "solde titre", "soldes titres",
]

NON_BUSINESS_FILE_KEYWORDS = [
    "facture", "factures", "releve comptable", "bordereau", "attestation",
]

GENERIC_FILE_KEYWORDS = [
    "fichier", "fichiers", "document", "documents",
]

NON_RECEPTION_KEYWORDS = [
    "non reception", "non recu", "non recue", "non recus", "non recues",
    "n'avons pas recu", "nous n'avons pas recu", "je n'ai pas recu",
    "pas recu", "pas recue", "pas recus", "pas recues",
    "manquant", "manquante", "manquants", "manquantes",
    "attendu et non recu", "fichier attendu", "document attendu",
]

ERROR_KEYWORDS = [
    "errone", "erronee", "errones", "erronees", "erreur", "incorrect",
    "incorrecte", "incoherent", "incoherente", "vide", "vides",
    "corrompu", "corrompue", "illisible", "inexploitable",
]

RESEND_KEYWORDS = [
    "renvoyer", "renvoi", "reenvoyer", "reenvoi", "retransmettre",
    "retransmission", "transmettre une autre fois", "envoyer de nouveau",
    "envoyer a nouveau", "recevoir une autre fois", "m'envoyer",
    "nous envoyer", "mettre a disposition",
]

# Mots indiquant une demande ACTIVE (affilié sollicite une action de Maroclear)
ACTIVE_REQUEST_KEYWORDS = [
    "veuillez", "merci de", "priere de", "s'il vous plait", "svp",
    "pourriez-vous", "pouvez-vous", "souhaitons", "je voudrais",
    "nous voudrions", "je souhaite", "nous souhaitons",
    "retransmettre", "retransmission", "nous envoyer", "m'envoyer",
    "mettre a disposition", "transmettre", "communiquer",
    "renvoyer", "envoyer de nouveau", "faire parvenir",
]

# Mots indiquant une RÉCLAMATION (contestation, préjudice, insatisfaction)
RECLAMATION_KEYWORDS = [
    "contestons", "contestation", "nous contestons", "je conteste",
    "prejudice", "prejudice financier", "prejudice subi",
    "inacceptable", "inadmissible", "inadmissible",
    "nous n'avons toujours pas", "toujours pas recu", "toujours aucune reponse",
    "aucune reponse", "sans reponse",
    "retard non justifie", "retard injustifie",
    "sans justification", "sans raison valable",
    "ecart de donnees", "ecart de position", "ecart entre",
    "ne correspond pas au bareme", "ne correspond pas au tarif",
    "montant incorrect", "montant errone", "facturation incorrecte",
    "nous reclamon", "reclamation",
    "barème", "bareme",
]

ALREADY_RECEIVED_KEYWORDS = [
    "deja recu", "deja recue", "deja recus", "deja recues",
    "avons recu", "ai recu", "recue mais", "recu mais",
]


def _contains_business_file(text_norm: str) -> bool:
    return _matches_any(text_norm, BUSINESS_FILE_KEYWORDS)


def _contains_non_business_file(text_norm: str) -> bool:
    return _matches_any(text_norm, NON_BUSINESS_FILE_KEYWORDS)


def _contains_generic_file(text_norm: str) -> bool:
    return _matches_any(text_norm, GENERIC_FILE_KEYWORDS)


def _is_active_request(text_norm: str) -> bool:
    """Retourne True si le message est une demande active de l'affilié vers Maroclear."""
    return _matches_any(text_norm, ACTIVE_REQUEST_KEYWORDS)


def _is_reclamation(text_norm: str) -> bool:
    """Retourne True si le message exprime une contestation ou un préjudice passé."""
    return _matches_any(text_norm, RECLAMATION_KEYWORDS)


def _build_rule_result(classe: TicketClass, justification: str) -> ClassificationResult:
    return ClassificationResult(
        classe=classe,
        confiance=1.0,
        justification=justification,
        ambiguite=None,
        noeud_question=None,
    )


def classify_by_priority_rules(text: str) -> Optional[ClassificationResult]:
    """
    Applique les règles métier déterministes avant le LLM.

    Arbre de décision (par ordre de priorité) :

    1. Demande active (veuillez, merci de, retransmettre...) + fichier métier → DEMANDE
       Exemple : "Merci de nous retransmettre les AOE du 20/05" → DEMANDE

    2. Réclamation explicite (contestons, préjudice, inacceptable...) → RÉCLAMATION
       Exemple : "Nous contestons le rejet..." → RÉCLAMATION
       Exemple : "Préjudice financier suite au retard..." → RÉCLAMATION

    3. Fichier métier (AOE, RSM, RCQ, CFT...) mentionné SANS demande active → INCIDENT
       Exemple : "Les fichiers CFT sont vides" → INCIDENT
       Exemple : "Le RSM de ce jour est erroné" → INCIDENT
       Exemple : "Nous n'avons pas reçu le RCQ" → INCIDENT

    4. Fichier non-métier déjà reçu + demande de renvoi → DEMANDE
    5. Fichier non-métier non reçu ou erroné → RÉCLAMATION
    """
    text_norm = normalize(text)

    has_active_request   = _is_active_request(text_norm)
    has_reclamation      = _is_reclamation(text_norm)
    has_business_file    = _contains_business_file(text_norm)
    has_non_business     = _contains_non_business_file(text_norm)
    has_generic_file     = _contains_generic_file(text_norm)
    has_non_reception    = _matches_any(text_norm, NON_RECEPTION_KEYWORDS)
    has_error            = _matches_any(text_norm, ERROR_KEYWORDS)
    has_resend           = _matches_any(text_norm, RESEND_KEYWORDS)
    already_received     = _matches_any(text_norm, ALREADY_RECEIVED_KEYWORDS)

    # ── Règle 1 : Demande active + fichier métier → DEMANDE ──────────────────
    # "Merci de retransmettre les AOE", "Veuillez nous envoyer le CFT"
    # La demande active prime sur le fichier métier
    if has_active_request and has_business_file:
        return _build_rule_result(
            TicketClass.DEMANDE,
            "Demande active de retransmission/mise à disposition d'un fichier métier → DEMANDE.",
        )

    # ── Règle 2 : Réclamation explicite → RÉCLAMATION ────────────────────────
    # "Nous contestons", "Préjudice financier", "Inacceptable", "Toujours sans réponse"
    if has_reclamation:
        return _build_rule_result(
            TicketClass.RECLAMATION,
            "Message exprimant une contestation ou un préjudice passé → RÉCLAMATION.",
        )

    # ── Règle 3 : Fichier métier sans demande active → INCIDENT ───────────────
    # "Les AOE sont vides", "Le RSM est erroné", "Nous n'avons pas reçu le RCQ"
    if has_business_file:
        return _build_rule_result(
            TicketClass.INCIDENT,
            "Fichier métier Maroclear mentionné sans demande active → INCIDENT.",
        )

    # ── Règle 4 : Fichier non-métier déjà reçu + demande de renvoi → DEMANDE ─
    if has_non_business and already_received and has_resend:
        return _build_rule_result(
            TicketClass.DEMANDE,
            "Document non métier déjà reçu, l'utilisateur demande un renvoi → DEMANDE.",
        )

    # ── Règle 5 : Fichier non-métier non reçu ou erroné → RÉCLAMATION ─────────
    if (has_non_business or has_generic_file) and (has_non_reception or has_error):
        return _build_rule_result(
            TicketClass.RECLAMATION,
            "Document non métier non reçu ou erroné → RÉCLAMATION.",
        )

    return None


def _is_token_question_relevant(text_norm: str) -> bool:
    """Retourne True si le texte parle clairement d'un token/certificat RSA."""
    return any(normalize(kw) in text_norm for kw in ["token", "certificat", "rsa"])


def get_next_question_key(
    noeud:          str,
    text_norm:      str,
    questions_seen: set[str],
) -> Optional[str]:
    """
    Retourne la prochaine question de clarification pertinente.
    N'évite pas de retomber sur Q1_collectif une fois que le dialogue a déjà commencé.
    """
    key = _get_question_for_ticket(noeud, text_norm, questions_seen)
    if key == "Q1_collectif" and questions_seen:
        return None
    return key


# ── Reformulation objet/description ──────────────────────────────────────────

def _fallback_subject(text: str, classe: TicketClass) -> str:
    """Génère un objet court en fallback (sans LLM)."""
    text_clean = text.strip()
    if len(text_clean) <= 80:
        return text_clean
    return text_clean[:77] + "..."


def _fallback_structured_description(
    text: str,
    classe: TicketClass,
    service_label: str = "",
    date_occurrence: str = "",
    frequence_occurrence: str = "",
) -> str:
    """Génère une description structurée en fallback (sans LLM) — garde les mots de l'affilié mais les structure."""
    # Nettoyer : enlever les lignes vides, les doublons, structurer
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    # Dédupliquer les lignes similaires
    seen = set()
    unique_lines = []
    for line in lines:
        normalized = line.lower().strip()
        if normalized not in seen and len(normalized) > 3:
            seen.add(normalized)
            unique_lines.append(line)
    # Joindre avec des points si pas de ponctuation finale
    parts = []
    for line in unique_lines:
        if line and line[-1] not in ".!?":
            parts.append(line + ".")
        else:
            parts.append(line)
    return " ".join(parts)


def reformulate_ticket_summary(
    text: str,
    classe: TicketClass,
    service_label: str = "",
    date_occurrence: str = "",
    frequence_occurrence: str = "",
    user_profile: dict | None = None,
) -> dict:
    """
    Produit un objet court et une description structurée pour le récapitulatif.
    Utilise le LLM si disponible, avec fallback local en cas d'erreur.
    """
    fallback = {
        "objet": _fallback_subject(text, classe),
        "description": _fallback_structured_description(
            text=text,
            classe=classe,
            service_label=service_label,
            date_occurrence=date_occurrence,
            frequence_occurrence=frequence_occurrence,
        ),
    }

    llm_text = minimize_text_for_llm(text, user_profile)

    prompt = (
        "Reformule un ticket support Maroclear pour pré-remplir un formulaire.\n"
        "Retourne uniquement un JSON pur avec les clés objet et description.\n\n"
        "Contraintes :\n"
        "- objet : titre court, nominal, max 80 caractères, sans formule de politesse.\n"
        "- description : 2 à 4 phrases complètes, bien structurées avec connecteurs logiques. "
        "Garder le vocabulaire métier de l'affilié mais reformuler en français correct. "
        "Ajouter des connecteurs (depuis, car, en effet, suite à). "
        "Inclure les détails temporels et contextuels mentionnés.\n"
        "- Ne pas mentionner la classe, le type de dossier, le service, la priorité.\n"
        "- Ne pas inventer de détails non mentionnés.\n"
        "- Ne PAS écrire à la 3ème personne ('L'affilié signale...'). Écrire à la 1ère personne du pluriel ('Nous n'avons pas reçu...').\n\n"
        f"Classe : {classe.value}\n"
        f"Service : {service_label or 'Non précisé'}\n"
        f"Date : {date_occurrence or 'Non précisée'}\n"
        f"Fréquence : {frequence_occurrence or 'Non précisée'}\n\n"
        f"Déclaration initiale (messages de l'affilié) :\n{llm_text.strip()}\n"
    )

    try:
        result = call_llm([{"role": "user", "content": prompt}], system=_EXTRACTOR_SYSTEM)
    except Exception as exc:
        logger.warning("Reformulation LLM échouée, fallback local : %s", exc)
        return fallback

    objet = str(result.get("objet") or "").strip()
    description = str(result.get("description") or "").strip()
    if not objet or not description:
        return fallback
    if normalize(objet) == normalize(description):
        return fallback

    return {
        "objet": objet[:100].rstrip(" .,;:"),
        "description": description,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def run_classification(
    clean_text:   str,
    ask_question: callable,  # fn(question_text: str) -> str | None
    initial_questions_seen: set[str] | None = None,
    conversation_history: list[dict] | None = None,
    user_profile: dict | None = None,
) -> tuple[ClassificationResult, int]:
    """
    Phase 1 : classification avec boucle de clarification.

    Args:
        clean_text:   texte nettoyé du ticket
        ask_question: callable qui pose une question et retourne la réponse (ou None = skip)
        initial_questions_seen: questions déjà posées dans les tours précédents
        conversation_history: historique de conversation existant (pour multi-tour)

    Returns:
        (ClassificationResult, nb_questions_posées)
    """
    cfg            = get_config()
    system_prompt  = _get_cached_system_prompt()
    text_norm      = normalize(clean_text)

    # Règles déterministes prioritaires (avant LLM)
    priority_result = classify_by_priority_rules(clean_text)
    if priority_result:
        logger.info("Classification par règle prioritaire : %s", priority_result.classe.value)
        return priority_result, 0

    if conversation_history is not None:
        conversation = conversation_history
    else:
        llm_text = minimize_text_for_llm(clean_text, user_profile)
        conversation = [{
            "role":    "user",
            "content": (
                f"Voici le ticket à classifier :\n\n\"{llm_text}\"\n\n"
                "Applique l'arbre de décision officiel validé."
            )
        }]

    nb_questions    = 0
    questions_seen: set[str] = set(initial_questions_seen or [])
    last_result:    ClassificationResult | None = None

    while True:
        raw    = call_llm(conversation, system=system_prompt)
        result = _validate_classification_response(raw)
        last_result = result

        logger.debug(
            "Tour %d : %s (%.0f%%) — ambigu=%s",
            nb_questions, result.classe.value, result.confiance * 100, result.ambiguite
        )

        conversation.append({"role": "assistant", "content": json.dumps(raw, ensure_ascii=False)})

        if result.is_certain(cfg.certainty_threshold):
            break

        if len(questions_seen) >= cfg.max_clarif_questions:
            logger.info("Max questions de clarification atteint — décision forcée.")
            break

        noeud = result.noeud_question or ""
        key   = _get_question_for_ticket(noeud, text_norm, questions_seen)
        if not key:
            break

        questions_seen.add(key)
        question_text = cfg.questions[key]

        answer = ask_question(question_text)
        if answer is None or answer.strip().lower() in ("", "/", "skip", "passer"):
            break

        conversation.append({
            "role":    "user",
            "content": f"Réponse : {minimize_text_for_llm(answer, user_profile)}\nMets à jour ta classification."
        })
        nb_questions += 1

    return last_result, nb_questions


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — COLLECTE FICHE
# ══════════════════════════════════════════════════════════════════════════════

def build_fiche(
    extracted:            dict,
    classe:               TicketClass,
    clean_text:           str,
    contexte_utilisateur: dict,
    ask_service:          callable,  # fn() -> ServiceInfo
    ask_field:            callable,  # fn(label, key, question, required) -> str | None
) -> tuple[TicketFiche, int]:
    """
    Phase 2 : construit la fiche complète.
    - Tente la détection automatique du service
    - Complète les champs manquants via ask_field
    - Calcule la priorité GLPI automatiquement
    """
    nb_questions = 0
    fiche        = TicketFiche()

    # ── Contexte utilisateur ──────────────────────────────────────────────────
    fiche.rapporteur = contexte_utilisateur.get("rapporteur")
    fiche.activite   = contexte_utilisateur.get("activite")
    fiche.nom_prenom = contexte_utilisateur.get("nom_prenom")
    fiche.telephone  = contexte_utilisateur.get("telephone")

    # ── Service ───────────────────────────────────────────────────────────────
    service = detect_service(clean_text)
    if service:
        logger.info("Service auto-détecté : %s", service.label)
        fiche.service = service
    else:
        fiche.service = ask_service()
        nb_questions += 1

    # ── Champs extraits ───────────────────────────────────────────────────────
    fiche.date_occurrence      = extracted.get("date_occurrence")
    fiche.frequence_occurrence = extracted.get("frequence_occurrence")
    fiche.description          = extracted.get("description")
    fiche.solution_proposee    = extracted.get("solution_proposee")
    docs = extracted.get("documents_joints")
    if isinstance(docs, list):
        fiche.documents_joints = docs

    # ── Collecte des champs manquants ─────────────────────────────────────────
    FIELDS = [
        ("Date d'occurrence *",      "date_occurrence",      True,
         "Quelle est la date à laquelle le problème s'est produit ? (JJ/MM/AAAA)"),
        ("Fréquence d'occurrence *",  "frequence_occurrence", True,
         "À quelle fréquence ce problème se produit-il ? (1 fois, récurrent, chaque jour…)"),
        ("Description *",             "description",          True,
         "Décrivez le problème en détail : que s'est-il passé, quelles références sont concernées, quel est l'impact ?"),
        ("Solution proposée",         "solution_proposee",    False,
         "Quelle action attendez-vous de notre part ?"),
        ("Documents joints",          "documents_joints",     False,
         "Avez-vous des documents à joindre ? (captures, références…) Sinon tapez '/'."),
    ]

    for label, key, required, question in FIELDS:
        if getattr(fiche, key, None):
            continue  # déjà renseigné par extraction

        answer = ask_field(label, key, question, required)
        if answer is None:
            nb_questions += 1
            continue

        answer = answer.strip()
        nb_questions += 1

        if answer.lower() in ("/", "skip", "passer", ""):
            if required:
                setattr(fiche, key, "Non renseigné")
            continue

        if key == "date_occurrence":
            parsed = extract_date_local(answer)
            if parsed:
                setattr(fiche, key, parsed)
            else:
                # Valeur saisie non parseable — on la stocke mais on avertit
                logger.warning(
                    "Date saisie non reconnue : '%s' — stockée telle quelle.", answer
                )
                setattr(fiche, key, answer)
        elif key == "documents_joints":
            items = [p.strip() for p in re.split(r"[,;]", answer) if p.strip()]
            fiche.documents_joints = items or []
        else:
            setattr(fiche, key, answer)

    # ── GLPI automatique ──────────────────────────────────────────────────────
    description_text = fiche.description or clean_text
    fiche.glpi       = compute_glpi(fiche.service.code, description_text)
    logger.info(
        "GLPI calculé : %s | U=%s | I=%s (confiance=%.0f%%)",
        fiche.glpi.priorite, fiche.glpi.urgence, fiche.glpi.impact,
        fiche.glpi.confidence * 100,
    )

    return fiche, nb_questions
