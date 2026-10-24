"""
core/config.py — Chargement et validation de la configuration YAML.
Singleton thread-safe. Toute logique métier est dans rules.yaml.
"""
from __future__ import annotations

import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from core.models import ConfigError

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "rules.yaml"
_lock        = threading.Lock()
_instance: "AppConfig | None" = None


class AppConfig:
    """
    Wrapper typé autour du YAML de configuration.
    Lève ConfigError sur tout champ manquant ou invalide.
    """

    def __init__(self, path: Path = _CONFIG_PATH) -> None:
        try:
            with open(path, encoding="utf-8") as fh:
                raw = yaml.safe_load(fh)
        except FileNotFoundError:
            raise ConfigError(f"Fichier de configuration introuvable : {path}")
        except yaml.YAMLError as exc:
            raise ConfigError(f"YAML invalide : {exc}")

        self._raw = raw
        self._validate()

    # ── Accesseurs modèle ─────────────────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._get("model.name")

    @property
    def model_fallback(self) -> str:
        return self._get("model.fallback")

    @property
    def temperature(self) -> float:
        return float(self._get("model.temperature"))

    @property
    def max_tokens(self) -> int:
        return int(self._get("model.max_tokens"))

    @property
    def timeout(self) -> int:
        return int(self._get("model.timeout_seconds"))

    @property
    def max_retries(self) -> int:
        return int(self._get("model.max_retries"))

    @property
    def retry_backoff(self) -> float:
        return float(self._get("model.retry_backoff_seconds"))

    # ── Accesseurs classification ─────────────────────────────────────────────

    @property
    def certainty_threshold(self) -> float:
        return float(self._get("classification.certainty_threshold"))

    @property
    def max_clarif_questions(self) -> int:
        return int(self._get("classification.max_clarification_questions"))

    @property
    def valid_classes(self) -> list[str]:
        return self._get("classification.valid_classes")

    # ── Accesseurs services ───────────────────────────────────────────────────

    @property
    def services(self) -> dict[str, dict]:
        """Retourne les services INCIDENT (compatibilité avec glpi_service)."""
        return self._get("services.incident")

    @property
    def services_by_type(self) -> dict[str, dict[str, dict]]:
        """Retourne tous les services groupés par type de ticket."""
        return {
            "incident":    self._get("services.incident"),
            "reclamation": self._get("services.reclamation"),
            "demande":     self._get("services.demande"),
        }

    def get_service(self, code: str) -> dict | None:
        """Cherche un service par code dans tous les types."""
        for type_services in self.services_by_type.values():
            if code in type_services:
                return type_services[code]
        return None

    def get_services_for_type(self, ticket_type: str) -> dict[str, dict]:
        """Retourne les services disponibles pour un type de ticket donné."""
        key = ticket_type.lower().replace("é", "e")
        if key in ("incident",):
            return self._get("services.incident")
        elif key in ("reclamation", "réclamation"):
            return self._get("services.reclamation")
        elif key in ("demande",):
            return self._get("services.demande")
        return self._get("services.incident")

    # ── Accesseurs GLPI ───────────────────────────────────────────────────────

    @property
    def glpi_matrix(self) -> dict[str, dict[str, list[str]]]:
        return self._get("glpi.matrix")

    @property
    def gravite_keywords(self) -> dict[str, list[str]]:
        return self._get("glpi.gravite_keywords")

    @property
    def service_gravite_order(self) -> dict[str, list[str]]:
        return self._get("glpi.service_gravite_order")

    @property
    def default_gravite(self) -> dict[str, str]:
        return self._get("glpi.default_gravite")

    # ── Accesseurs questions ──────────────────────────────────────────────────

    @property
    def questions(self) -> dict[str, str]:
        raw = self._get("questions")
        return {k: v for k, v in raw.items() if k != "triggers"}

    @property
    def question_triggers(self) -> dict[str, list[str]]:
        return self._get("questions.triggers")

    # ── Helpers internes ──────────────────────────────────────────────────────

    def _get(self, dotpath: str) -> Any:
        parts  = dotpath.split(".")
        cursor = self._raw
        for part in parts:
            if not isinstance(cursor, dict) or part not in cursor:
                raise ConfigError(f"Clé manquante dans rules.yaml : '{dotpath}'")
            cursor = cursor[part]
        return cursor

    def _validate(self) -> None:
        required_paths = [
            "model.name", "model.temperature", "model.max_tokens",
            "classification.certainty_threshold",
            "classification.valid_classes",
            "services.incident",
            "glpi.matrix", "glpi.gravite_keywords",
            "glpi.service_gravite_order", "glpi.default_gravite",
            "questions",
        ]
        for path in required_paths:
            self._get(path)  # lève ConfigError si absent

        if not self._get("services.incident"):
            raise ConfigError("La section 'services.incident' est vide.")


def get_config() -> AppConfig:
    """Singleton thread-safe."""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = AppConfig()
    return _instance


def reload_config(path: Path = _CONFIG_PATH) -> AppConfig:
    """Force le rechargement (utile pour les tests).
    Invalide aussi le cache du prompt système dans classifier.
    """
    global _instance
    with _lock:
        _instance = AppConfig(path)

    # Invalider le cache du prompt système qui dépend de la config
    try:
        from services.classifier import _get_cached_system_prompt
        _get_cached_system_prompt.cache_clear()
    except ImportError:
        pass

    return _instance
