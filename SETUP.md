# Setup — ClearBot Maroclear

Deux modes de déploiement sont disponibles : **Docker (recommandé)** ou **développement local**.

---

## Mode 1 — Docker (recommandé)

### Prérequis
- Docker Desktop installé et en cours d'exécution
- Git

### Étapes

```bash
# 1. Cloner le projet
git clone https://github.com/Boutanfitsalma/ClearBot--Systeme-multi-agents-Maroclear.git
cd ClearBot--Systeme-multi-agents-Maroclear

# 2. Configurer les variables d'environnement
cp backend/.env.example backend/.env
```

Éditer `backend/.env` :
```env
OPENROUTER_API_KEY=votre_cle_openrouter
BREVO_API_KEY=votre_cle_brevo
SESSION_SECRET_KEY=changez-moi-en-production
```

```bash
# 3. Lancer tous les services (backend + 2 frontends + Streamlit)
docker-compose up --build
```

Les bases vectorielles ChromaDB sont **embarquées dans l'image Docker** — aucune re-indexation nécessaire au premier démarrage.

### Services lancés

| Service | URL | Description |
|---|---|---|
| Backend API | http://localhost:8000 | FastAPI + agents IA |
| MyMaroclear | http://localhost:3000 | Espace privé affilié |
| Portail public | http://localhost:5173 | Site public + ClearBot |
| Dashboard Streamlit | http://localhost:8501 | Visualisation des évaluations |

### Dashboard d'évaluation Streamlit (optionnel)

```bash
docker-compose --profile evaluation up --build
```

Accès : http://localhost:8501

---

## Mode 2 — Développement local (sans Docker)

### Prérequis
- Python 3.11+
- Node.js 18+
- Ollama (pour les embeddings BGE-M3)

### 1. Configurer les fichiers .env

**`backend/.env`**
```env
OPENROUTER_API_KEY=votre_cle_openrouter
BREVO_API_KEY=votre_cle_brevo
SESSION_SECRET_KEY=dev-secret
```

**`backend/agents/support_classification/.env`**
```env
OPENROUTER_API_KEY=votre_cle_openrouter
```

### 2. Installer les dépendances Python

```bash
cd backend
pip install -r config/requirements.txt
```

### 3. Installer et démarrer Ollama (embeddings BGE-M3)

```bash
# Télécharger Ollama : https://ollama.com/download
ollama serve
ollama pull bge-m3
```

### 4. Bases vectorielles ChromaDB

Les bases vectorielles sont incluses dans le dépôt via Git LFS (ou à télécharger depuis le lien partagé séparément).
Elles doivent être placées dans :

```
backend/agents/conseiller_reglementaire/data/vectordb/
backend/agents/informationnel_procedural/data/vectordb/
```

Si vous souhaitez **re-indexer** les documents sources :
```bash
cd backend
# RAG institutionnel
python agents/informationnel_procedural/agent.py --index

# RAG réglementaire
python agents/conseiller_reglementaire/rag/build_reglementaire_index.py
```

### 5. Lancer les services

**Terminal 1 — Backend (port 8000)**
```bash
cd backend
uvicorn api.api:app --reload --port 8000
```

**Terminal 2 — Frontend privé MyMaroclear (port 3000)**
```bash
cd frontend/mymaroclear
npm install
npm start
```

**Terminal 3 — Portail public (port 5173)**
```bash
cd frontend/portail-public
npm install
npm run dev
```

**Terminal 4 — Dashboard Streamlit (port 8501, optionnel)**
```bash
cd backend
pip install -r evaluation/requirements_streamlit.txt
python -m streamlit run evaluation/streamlit_app.py
```

---

## Comptes de test

| Username | Password | Rôle |
|---|---|---|
| `asmae.hidra` | `maroclear123` | Responsable support affilié |
| `adil.elbouzgui` | `maroclear123` | Responsable |

---

## Structure du projet

```
ClearBot/
├── docker-compose.yml              ← Orchestration complète (3 services + Streamlit)
├── backend/
│   ├── Dockerfile
│   ├── .env.example
│   ├── api/                        ← FastAPI (routes /chat, /dispatch, /feedback)
│   ├── agents/
│   │   ├── orchestrateur/          ← Routeur LangGraph + LLM + fallback lexical
│   │   ├── support_classification/ ← Classification conversationnelle
│   │   ├── informationnel_procedural/ ← RAG institutionnel
│   │   ├── conseiller_reglementaire/  ← RAG juridique (Recueil AMMC)
│   │   └── auto_dispatcher/        ← Email Brevo au dispatcher
│   ├── shared/                     ← BaseAgent, LLM client, RAG pipeline
│   ├── config/                     ← config.yaml global + requirements.txt
│   ├── evaluation/                 ← Scripts d'évaluation + dashboard Streamlit
│   └── tests/                      ← Tests pytest (~80 tests)
├── frontend/
│   ├── mymaroclear/                ← React 18 — espace privé affilié (port 3000)
│   └── portail-public/             ← Vite + React 19 — portail public (port 5173)
└── SETUP.md
```

---

## Configuration Brevo (email dispatcher)

1. Créer un compte sur https://app.brevo.com
2. Settings → Senders → Ajouter et vérifier l'email expéditeur
3. Settings → SMTP & API → Copier la clé API v3
4. Mettre la clé dans `backend/.env` : `BREVO_API_KEY=...`

---

## Tests

```bash
cd backend
pytest tests/ -v
```
