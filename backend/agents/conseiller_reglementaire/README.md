# Agent Conseiller Réglementaire

## Rôle
Répond aux questions sur la réglementation du marché financier marocain,  
spécifiquement sur la **Loi 35-96** et le **Règlement Général de Maroclear**.

## Capacités
- Analyse juridique sourcée avec références d'articles
- Distinction Loi 35-96 (norme supérieure) vs Règlement Général (application)
- Retrieval hybride vectoriel + BM25
- Conversation multi-tours avec historique

## Données propres (`data/`)
| Dossier | Contenu |
|---|---|
| `data/input/` | PDFs réglementaires (Loi 35-96, Règlement Général) |
| `data/input/jsons/` | Chunks JSON pré-traités |
| `data/vectordb/` | Base vectorielle ChromaDB |
| `data/settings.yaml` | Configuration du pipeline RAG réglementaire |

## Pipeline RAG (`rag/`)
Pipeline complet issu de `rag_reglementaire/` :
- `retriever.py` — retrieval hybride vectoriel + BM25
- `embedder.py` — embeddings
- `vector_store.py` — ChromaDB
- `llm_client.py` — client LLM
- `chunking_pipeline.py` — découpage des documents
- `ingest.py` / `ingest_new_doc.py` — ingestion de nouveaux documents

## Parsing en cours (`parsing/`)
Pipeline Docling pour le **Recueil AMMC VF Mars 2026** :
- Extraction article par article avec métadonnées
- Liens inter-articles et inter-pages
- ⚠️ **Non finalisé** — à intégrer dans `data/` une fois terminé

## Fichiers
- `agent.py` — classe `ReglementaireAgent`
- `config.yaml` — configuration
- `schemas.py` — modèles Pydantic input/output

## Dépendances
- `backend/shared/core/` — `AgentMessage`, `AgentContext`
- `backend/shared/base/` — `BaseAgent`
