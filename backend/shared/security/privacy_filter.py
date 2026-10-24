"""
Filtrage minimal des donnees sensibles avant appel LLM externe.

Le texte original reste disponible cote backend pour la fiche, le dispatch et
les traitements internes. Ce module produit uniquement une vue minimisee pour
les prompts.
"""
from __future__ import annotations

import re
from typing import Any


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)

PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?212|0)?[\s.-]?(?:5|6|7)[\s.-]?(?:\d[\s.-]?){8}(?!\w)"
)

LONG_ID_RE = re.compile(r"\b(?:[A-Z]{2,}[-_/]?)?\d{6,}(?:[-_/]?[A-Z0-9]+)?\b", re.IGNORECASE)

LABELLED_ID_RE = re.compile(
    r"\b(?:id|identifiant|login|matricule|compte|code|numero|num[eé]ro|n[°o])"
    r"\s*[:#-]?\s*[A-Z0-9][A-Z0-9._/-]{3,}\b",
    re.IGNORECASE,
)

SENSITIVE_PATTERNS = [EMAIL_RE, PHONE_RE, LABELLED_ID_RE, LONG_ID_RE]

PROFILE_KEYS = (
    "reporterName",
    "reporterEmail",
    "reporterPhone",
    "institution",
    "id",
    "username",
)


def contains_sensitive_data(text: str, user_profile: dict[str, Any] | None = None) -> bool:
    """Retourne True si le texte contient une donnee sensible evidente."""
    if not text:
        return False
    if any(pattern.search(text) for pattern in SENSITIVE_PATTERNS):
        return True
    return any(_profile_value_in_text(text, value) for value in _profile_values(user_profile))


def minimize_text_for_llm(text: str, user_profile: dict[str, Any] | None = None) -> str:
    """Masque les donnees personnelles/identifiants evidents avant appel LLM."""
    if not text:
        return text

    minimized = EMAIL_RE.sub("[EMAIL]", text)
    minimized = PHONE_RE.sub("[TELEPHONE]", minimized)
    minimized = LABELLED_ID_RE.sub(lambda m: _mask_labelled_identifier(m.group(0)), minimized)
    minimized = LONG_ID_RE.sub("[IDENTIFIANT]", minimized)

    for value in _profile_values(user_profile):
        minimized = _replace_literal(minimized, value, _label_for_profile_value(value, user_profile))

    return minimized


def _profile_values(user_profile: dict[str, Any] | None) -> list[str]:
    if not user_profile:
        return []
    values: list[str] = []
    for key in PROFILE_KEYS:
        value = user_profile.get(key)
        if value is None:
            continue
        value = str(value).strip()
        if len(value) >= 3:
            values.append(value)
    return values


def _profile_value_in_text(text: str, value: str) -> bool:
    return bool(value and re.search(re.escape(value), text, flags=re.IGNORECASE))


def _replace_literal(text: str, value: str, label: str) -> str:
    if not value:
        return text
    return re.sub(re.escape(value), label, text, flags=re.IGNORECASE)


def _label_for_profile_value(value: str, user_profile: dict[str, Any] | None) -> str:
    if not user_profile:
        return "[DONNEE_PROFIL]"
    for key, profile_value in user_profile.items():
        if str(profile_value).strip().lower() != value.lower():
            continue
        if key == "reporterName":
            return "[NOM_AFFILIE]"
        if key == "reporterEmail":
            return "[EMAIL]"
        if key == "reporterPhone":
            return "[TELEPHONE]"
        if key == "institution":
            return "[INSTITUTION]"
        return "[DONNEE_PROFIL]"
    return "[DONNEE_PROFIL]"


def _mask_labelled_identifier(value: str) -> str:
    label = re.split(r"[:#-]", value, maxsplit=1)[0].strip()
    if label and len(label) < len(value):
        return f"{label}: [IDENTIFIANT]"
    return "[IDENTIFIANT]"
