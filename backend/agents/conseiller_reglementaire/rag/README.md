# RAG Réglementaire

Pipeline RAG juridique pour l'agent `ReglementaireAgent`.

## Structure

```
rag/
├── agent.py              ← Classe ReglementaireAgent (point d'entrée)
├── retriever.py          ← Retrieval hybride vectoriel + BM25
├── embedder.py           ← Embeddings BGE-M3
├── vector_store.py       ← ChromaDB (persistant)
├── llm_client.py         ← Client OpenRouter
├── chunking_pipeline.py  ← Découpage article par article
├── ingest.py             ← Ingestion initiale (build index)
├── ingest_new_doc.py     ← Ingestion d'un nouveau document
├── config.py             ← Configuration du pipeline
├── rag_config.py         ← Paramètres RAG (top_k, seuils, modèles)
├── document_cleaner.py   ← Nettoyage des textes extraits
├── metadata_extractor.py ← Extraction des métadonnées juridiques
├── legal_chunk_rag.py    ← Logique de chunking juridique
└── run.py                ← Script de test en ligne de commande
```

## Données

Les bases vectorielles sont dans `data/vectordb/` (incluses dans le dépôt).
Les documents sources sont dans `data/input/`.

## Re-indexation

Si besoin de reconstruire l'index depuis les sources :

```bash
cd backend/agents/conseiller_reglementaire/rag
python build_reglementaire_index.py
```

## Ajouter un nouveau document

```bash
cd backend/agents/conseiller_reglementaire/rag
python ingest_new_doc.py chemin/vers/document.pdf
```

## Dépendances
- `backend/shared/core/` — `AgentMessage`, `AgentContext`
- `backend/shared/base/` — `BaseAgent`
- Ollama local avec modèle `bge-m3` (embeddings)
