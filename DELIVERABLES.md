# ClearBot — Livrables et Guide de Passage

Ce fichier est un document de livraison pour l'entreprise. Il synthétise l'état du projet, les commandes de démarrage, les tests validés et les livrables disponibles sur SharePoint.

## 1. Objectif

Fournir un point unique de référence pour :
- démarrage du projet ClearBot,
- documents livrables sur SharePoint,
- état de livraison,
- prochaines étapes.

## 2. Documents livrables

Ces documents sont disponibles sur SharePoint (non inclus dans le dépôt) :

- `DAT.docx` — Document d'Architecture Technique
- `Document_Cadrage_Projet.docx` — Document de cadrage projet
- `Documentation_des_tests_ClearBot.docx` — tests
- `DOCUMENTATION_TECHNIQUE.md` — Documentation technique détaillée
- `Guide Utilisateur.docx` — Guide utilisateur final
- `KNOWN_ISSUES.md` — Liste des problèmes connus
- `RELEASE_NOTES.md` — Notes de version / clôture
- `évaluation.url` — Lien vers la page d'évaluation


## 3. Contenu présent dans le dépôt

Le dépôt contient :

- `README.md` — Présentation générale et démarrage rapide
- `SETUP.md` — Guide d'installation et de déploiement
- `backend/README.md` — Guide d'usage backend
- `backend/evaluation/README.md` — Guide d'évaluation RAG
- `docker-compose.yml` — Orchestration Docker complète
- Code source backend / frontends / tests

## 4. Commandes de démarrage recommandées

### Mode Docker (recommandé)

```powershell
cd ClearBot
# Copier le fichier d'exemple d'environnement
cp backend/.env.example backend/.env
# Éditer backend/.env puis lancer les services
docker-compose up --build
```

### Commandes utiles

- Backend API : http://localhost:8000
- Frontend affilié MyMaroclear : http://localhost:3000
- Portail public : http://localhost:5173
- Dashboard d'évaluation Streamlit : http://localhost:8501

### Mode local (sans Docker)

```powershell
cd ClearBot/backend
pip install -r config/requirements.txt
uvicorn api.api:app --reload --port 8000
```

Frontend privé :

```powershell
cd ClearBot/frontend/mymaroclear
npm install
npm start
```

Frontend public :

```powershell
cd ClearBot/frontend/portail-public
npm install
npm run dev
```

Dashboard d'évaluation :

```powershell
cd ClearBot/backend
pip install -r evaluation/requirements_streamlit.txt
python -m streamlit run evaluation/streamlit_app.py
```

## 5. Tests validés

Tests exécutés et validés :

```powershell
cd ClearBot/backend
pytest -q tests
```

Résultats : `68 passed`.

## 6. État du projet

- Branche Git finale : `main`
- Commit final : `4b7aaeb`
- Backend testé et fonctionnel
- Chemin `rag_project_path` corrigé pour l'agent réglementaire

