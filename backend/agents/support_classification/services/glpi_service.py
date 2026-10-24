"""
services/glpi_service.py — Calcul GLPI et détection de service.

Améliorations vs v6 :
  - Toutes les règles viennent du YAML (zéro hardcodé)
  - Scoring pondéré par spécificité du mot-clé (longueur)
  - Confidence score sur la détection de gravité
  - Séparation claire service / gravité / GLPI
"""
from __future__ import annotations

import re
import unicodedata
import logging
from functools import lru_cache

from core.config import get_config
from core.models import GlpiInfo, ServiceInfo, GlpiPriority

logger = logging.getLogger(__name__)


# ── Normalisation texte ───────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """
    Normalise les accents, apostrophes et espaces pour fiabiliser
    les comparaisons de mots-clés.
    """
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.lower()
    return re.sub(r"\s+", " ", text).strip()


def _contains(text_norm: str, keyword: str) -> bool:
    """Vérifie si le mot-clé normalisé est dans le texte."""
    return normalize(keyword) in text_norm


# ── Détection service ─────────────────────────────────────────────────────────

def detect_service(text: str, ticket_type: str = "incident") -> ServiceInfo | None:
    """
    Détecte le service depuis le texte par scoring.
    Cherche dans les services du type de ticket donné.
    Retourne None si aucun service n'est détecté avec certitude.
    """
    cfg        = get_config()
    text_norm  = normalize(text)
    services   = cfg.get_services_for_type(ticket_type)
    best_code  = None
    best_score = 0.0

    for code, svc in services.items():
        keywords = svc.get("keywords", [])
        if not keywords:  # "Autre" = dernier recours
            continue
        matched  = [kw for kw in keywords if _contains(text_norm, kw)]
        if not matched:
            continue
        score = sum(len(kw) for kw in matched)
        if score > best_score:
            best_score = score
            best_code  = code

    if best_code:
        svc = services[best_code]
        logger.debug("Service détecté : %s (score=%.0f)", svc["label"], best_score)
        return ServiceInfo(
            code=best_code,
            label=svc["label"],
            system=svc.get("system", ""),
            description=svc.get("description", ""),
            auto_detected=True,
        )
    return None


def get_service_by_code(code: str) -> ServiceInfo | None:
    """Retourne un ServiceInfo depuis un code connu."""
    cfg = get_config()
    svc = cfg.get_service(code)
    if not svc:
        return None
    return ServiceInfo(
        code=code,
        label=svc["label"],
        system=svc.get("system", ""),
        description=svc.get("description", ""),
        auto_detected=False,
    )


def list_services(ticket_type: str = "incident") -> list[tuple[str, str, str]]:
    """Retourne [(code, label, system), …] pour affichage."""
    services = get_config().get_services_for_type(ticket_type)
    return [
        (code, svc["label"], svc.get("system", ""))
        for code, svc in services.items()
    ]


# ── Détection gravité ─────────────────────────────────────────────────────────

def detect_gravite(text: str, service_code: str) -> tuple[str, float]:
    """
    Détecte la gravité GLPI depuis le texte.

    Stratégie :
    1. Parcourt les gravités dans l'ordre défini par service_gravite_order
       (du plus spécifique au plus général).
    2. Score = somme des longueurs des mots-clés matchés (spécificité).
    3. Retourne (gravite, confidence) où confidence = score / max_possible.

    Returns:
        (gravite_key, confidence_float)  confidence ∈ [0.0, 1.0]
    """
    cfg       = get_config()
    text_norm = normalize(text)
    order     = cfg.service_gravite_order.get(service_code, list(cfg.gravite_keywords.keys()))
    kw_map    = cfg.gravite_keywords

    best_gravite = None
    best_score   = 0

    for gravite in order:
        keywords = kw_map.get(gravite, [])
        matched  = [kw for kw in keywords if _contains(text_norm, kw)]
        if matched:
            score = sum(len(kw) for kw in matched)
            if score > best_score:
                best_score   = score
                best_gravite = gravite

    if best_gravite:
        # Confidence normalisée dynamiquement :
        # score_max = somme des longueurs de tous les mots-clés de cette gravité
        all_keywords = kw_map.get(best_gravite, [])
        score_max    = sum(len(kw) for kw in all_keywords) if all_keywords else 1
        confidence   = min(best_score / max(score_max, 1), 1.0)
        return best_gravite, confidence

    # Fallback sans confidence
    fallback = cfg.default_gravite.get(service_code, "blocage_affilie")
    logger.debug(
        "Gravité non détectée pour service %s — fallback : %s",
        service_code, fallback
    )
    return fallback, 0.3  # confidence basse = fallback


# ── Calcul GLPI ───────────────────────────────────────────────────────────────

def compute_glpi(service_code: str, description: str) -> GlpiInfo:
    """
    Calcule Urgence, Impact, Priorité GLPI.

    Algorithme :
    1. Détecte la gravité depuis le texte
    2. Cherche dans la matrice (service, gravité)
    3. Fallback sur gravité générique si absent
    """
    cfg     = get_config()
    matrix  = cfg.glpi_matrix

    gravite, grav_conf = detect_gravite(description, service_code)

    # Lookup direct
    service_matrix = matrix.get(service_code, {})
    row            = service_matrix.get(gravite)

    if not row:
        # Fallback : cherche une gravité plus générique dans le même service
        fallback_order = ["blocage_affilie", "partiel", "impossible", "autre"]
        for fallback in fallback_order:
            row = service_matrix.get(fallback)
            if row:
                gravite   = fallback
                grav_conf = max(0.0, grav_conf - 0.2)
                break
        else:
            logger.warning(
                "Aucune règle GLPI pour service=%s. Priorité P3 par défaut.",
                service_code
            )
            return GlpiInfo(
                urgence="Moyenne", impact="Moyen",
                priorite=GlpiPriority.P3,
                gravite_detectee=gravite,
                confidence=0.0,
            )

    urgence, impact, priorite_str = row
    try:
        priorite = GlpiPriority(priorite_str)
    except ValueError:
        priorite = priorite_str  # ex: "Qualifiée par dispatcher"

    return GlpiInfo(
        urgence=urgence,
        impact=impact,
        priorite=priorite,
        gravite_detectee=gravite,
        confidence=grav_conf,
    )
