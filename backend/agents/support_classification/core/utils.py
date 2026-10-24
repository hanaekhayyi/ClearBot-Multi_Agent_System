"""
core/utils.py — Utilitaires partagés Maroclear v7.

Fonctions communes utilisées par plusieurs modules.
Centralisées ici pour éviter les imports croisés et les violations d'encapsulation.
"""
from __future__ import annotations

import re


def strip_html(text: str) -> str:
    """Supprime les balises HTML et normalise les espaces."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()
