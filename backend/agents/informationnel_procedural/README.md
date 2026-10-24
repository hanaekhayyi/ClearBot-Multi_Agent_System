# Agent Informationnel & Procédural

## Rôle
Répond aux questions d'ordre général dans le contexte institutionnel Maroclear  
et guide les Affiliés sur les procédures et services.

## Capacités
- Questions sur Maroclear (activités, services, rôle)
- Procédure d'affiliation
- Définitions du glossaire Maroclear
- Questions générales métier (dénouement, conservation, OPCVM...)

## Données propres (`data/`)
| Dossier | Contenu |
|---|---|
| `data/documents/` | PDFs institutionnels (Règles de fonctionnement, glossaire) |
| `data/vectordb/` | Base vectorielle ChromaDB |
| `data/chunks_debug/` | Chunks JSON pour debug et validation |

## Fichiers
- `agent.py` — classe `RAGAgent`
- `config.yaml` — configuration RAG
- `schemas.py` — modèles Pydantic input/output
- `rag/` — pipeline RAG propre (document_loader, embeddings, retriever, chunker, vector_store)

## Dépendances
- `backend/shared/core/` — `AgentMessage`, `AgentContext`
- `backend/shared/base/` — `BaseAgent`
- `backend/shared/llm/` — `OllamaClient` (OpenRouter)
