"""
services/llm_client.py — Client LLM robuste.

Améliorations vs v6 :
  - Retry exponentiel avec jitter
  - Fallback automatique sur modèle secondaire
  - Validation stricte du JSON de retour
  - Séparation nette parsing / réseau
  - Logging structuré (pas de print)
  - Pas d'injection de clé API dans le code
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import random
from typing import Any

import requests
from dotenv import load_dotenv

from core.config import get_config
from core.models import LLMError, ValidationError
from shared.security import minimize_text_for_llm

logger = logging.getLogger(__name__)

API_URL = "https://openrouter.ai/api/v1/chat/completions"

load_dotenv()


def _get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise LLMError(
            "Variable d'environnement OPENROUTER_API_KEY non définie.",
            retryable=False,
        )
    return key


def _build_headers() -> dict[str, str]:
    return {
        "Authorization":  f"Bearer {_get_api_key()}",
        "Content-Type":   "application/json",
        "HTTP-Referer":   "https://maroclear-classifier.local",
        "X-Title":        "Maroclear Agent v7",
    }


def _parse_json_response(raw: str) -> dict:
    """
    Parse le JSON LLM de manière robuste :
    - Retire les blocs ```json … ```
    - Retire les commentaires // … en fin de ligne
    - Lève ValidationError si le JSON est invalide
    """
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    clean = re.sub(r"//[^\n]*", "", clean)        # retire commentaires inline
    clean = re.sub(r",\s*([}\]])", r"\1", clean)  # retire virgules finales

    if not clean:
        raise ValidationError("Réponse LLM vide après nettoyage.")

    try:
        return json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"JSON invalide : {exc}. Extrait : {raw[:200]}"
        )


def _call_once(
    messages: list[dict],
    model:    str,
    cfg_timeout:   int,
    cfg_max_tokens: int,
    cfg_temp: float,
) -> dict:
    """Un seul appel HTTP, sans retry."""
    payload = {
        "model":       model,
        "messages":    messages,
        "temperature": cfg_temp,
        "max_tokens":  cfg_max_tokens,
    }
    try:
        resp = requests.post(
            API_URL,
            headers=_build_headers(),
            json=payload,
            timeout=cfg_timeout,
        )
    except requests.exceptions.Timeout:
        raise LLMError(f"Timeout ({cfg_timeout}s) — modèle {model}.", retryable=True)
    except requests.exceptions.ConnectionError as exc:
        raise LLMError(f"Erreur réseau : {exc}", retryable=True)
    except requests.exceptions.RequestException as exc:
        raise LLMError(f"Requête échouée : {exc}", retryable=True)

    # Erreurs HTTP
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError:
        code = resp.status_code
        body = resp.text[:300]
        if code == 401:
            raise LLMError("Clé API invalide (401).", status_code=401, retryable=False)
        if code == 429:
            raise LLMError("Rate limit atteint (429).", status_code=429, retryable=True)
        if code >= 500:
            raise LLMError(f"Erreur serveur {code} : {body}", status_code=code, retryable=True)
        raise LLMError(f"HTTP {code} : {body}", status_code=code, retryable=False)

    data = resp.json()
    try:
        raw_content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise ValidationError(f"Structure de réponse inattendue : {exc}. Data : {str(data)[:300]}")

    return _parse_json_response(raw_content)


def call_llm(
    messages: list[dict],
    system:   str | None = None,
) -> dict[str, Any]:
    """
    Appel LLM avec :
    - Injection du system prompt
    - Retry exponentiel avec jitter
    - Fallback automatique sur modèle secondaire
    """
    cfg = get_config()

    safe_messages = [
        {
            **message,
            "content": minimize_text_for_llm(str(message.get("content", "")))
            if message.get("role") == "user"
            else message.get("content", ""),
        }
        for message in messages
    ]

    full_messages = safe_messages
    if system:
        full_messages = [{"role": "system", "content": system}] + [
            m for m in safe_messages if m.get("role") != "system"
        ]

    models_to_try = [cfg.model_name, cfg.model_fallback]
    last_error: LLMError | None = None

    for model in models_to_try:
        for attempt in range(cfg.max_retries):
            try:
                result = _call_once(
                    full_messages,
                    model=model,
                    cfg_timeout=cfg.timeout,
                    cfg_max_tokens=cfg.max_tokens,
                    cfg_temp=cfg.temperature,
                )
                if attempt > 0 or model != cfg.model_name:
                    logger.info("Succès après %d essai(s) sur modèle %s", attempt + 1, model)
                return result

            except LLMError as exc:
                last_error = exc
                if not exc.retryable:
                    raise

                if attempt < cfg.max_retries - 1:
                    wait = cfg.retry_backoff * (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning(
                        "Tentative %d/%d échouée sur %s : %s. Retry dans %.1fs.",
                        attempt + 1, cfg.max_retries, model, exc, wait
                    )
                    time.sleep(wait)
                else:
                    logger.error("Modèle %s épuisé après %d tentatives.", model, cfg.max_retries)

            except ValidationError:
                raise  # Pas de retry sur erreur de parsing

    raise LLMError(
        f"Tous les modèles ont échoué. Dernière erreur : {last_error}"
    ) from last_error
