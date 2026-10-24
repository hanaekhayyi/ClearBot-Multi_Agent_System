# Agent Support & Classification

## Rôle
Identifie s'il s'agit d'une **demande**, d'un **incident** ou d'une **réclamation**  
et extrait les informations structurées à partir de la discussion.

## Capacités
- Classification : INCIDENT / DEMANDE / RÉCLAMATION
- Détermination de la priorité OLA (P1 à P4)
- Vérification fondé / non fondé
- Extraction : service, système, statut
- Orientation vers le bon circuit de traitement

## Fichiers
- `agent.py` — classe `ClassificationAgent`
- `config.yaml` — configuration et seuils
- `schemas.py` — modèles Pydantic input/output
- `prompts/` — prompts système

## Dépendances
- `backend/shared/core/` — `AgentMessage`, `AgentContext`
- `backend/shared/base/` — `BaseAgent`
- `backend/shared/llm/` — `OllamaClient` (OpenRouter)
