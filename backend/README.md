# Backend — Système Multi-Agents ClearBot

## Architecture

```
backend/
├── api/                          ← FastAPI (routes /chat, /dispatch, /feedback, /classify)
├── agents/
│   ├── orchestrateur/            ← Routage LangGraph + LLM + fallback lexical
│   ├── support_classification/   ← Classification conversationnelle (INCIDENT/DEMANDE/RÉCLAMATION)
│   ├── informationnel_procedural/← RAG institutionnel (documents Maroclear + glossaire)
│   ├── conseiller_reglementaire/ ← RAG juridique (Recueil AMMC, Loi 35-96, circulaires)
│   └── auto_dispatcher/          ← Notification email Brevo au dispatcher
├── shared/
│   ├── base/                     ← BaseAgent (classe abstraite)
│   ├── core/                     ← AgentMessage, AgentContext
│   ├── llm/                      ← Client OpenRouter
│   └── rag/                      ← SmartChunker, Embeddings, VectorStore, Retriever
├── config/
│   ├── config.yaml               ← Configuration globale multi-agents
│   └── requirements.txt
├── evaluation/
│   ├── eval_classification_unit.py
│   ├── eval_rag_informationnel.py
│   ├── eval_rag_reglementaire.py
│   ├── streamlit_app.py          ← Dashboard d'évaluation
│   └── rapports/                 ← Résultats JSON des évaluations
└── tests/                        ← ~80 tests pytest
```

## Lancer l'API (développement local)

```bash
cd backend
pip install -r config/requirements.txt
uvicorn api.api:app --reload --port 8000
```

## Lancer via Docker

```bash
# Depuis la racine du projet
docker-compose up --build
```

## Variables d'environnement requises

Créer `backend/.env` à partir de `.env.example` :

```env
OPENROUTER_API_KEY=...   # Clé OpenRouter (LLM)
BREVO_API_KEY=...        # Clé Brevo (email dispatcher)
SESSION_SECRET_KEY=...   # Clé secrète sessions FastAPI
```

## Tests

```bash
cd backend
pytest tests/ -v
```

## Évaluation

```bash
cd backend

# Classification
python evaluation/eval_classification_unit.py --save evaluation/rapports/classification_final.json

# RAG informationnel (backend doit tourner sur :8000)
python evaluation/eval_rag_informationnel.py --save evaluation/rapports/rag_info_final.json

# RAG réglementaire
python evaluation/eval_rag_reglementaire.py --save evaluation/rapports/rag_regl_final.json

# Dashboard Streamlit
python -m streamlit run evaluation/streamlit_app.py
```
