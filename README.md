# ClearBot — Assistant IA Multi-Agents Maroclear

Système multi-agents conversationnel pour le dépositaire central des titres au Maroc.

## Agents

| Agent | Rôle |
|---|---|
| **Orchestrateur** | Routage intelligent par LLM (LangGraph) + fallback lexical |
| **Classification** | Qualification conversationnelle des incidents, demandes et réclamations |
| **Informationnel** | RAG sur les documents institutionnels Maroclear |
| **Réglementaire** | RAG juridique (Recueil AMMC, Loi 35-96, circulaires) |
| **Auto-Dispatcher** | Notification email structurée au dispatcher avec priorité GLPI |

## Démarrage rapide (Docker)

```bash
git clone https://github.com/Boutanfitsalma/ClearBot--Systeme-multi-agents-Maroclear.git
cd ClearBot--Systeme-multi-agents-Maroclear

# Configurer les clés API
cp backend/.env.example backend/.env
# Éditer backend/.env et renseigner OPENROUTER_API_KEY et BREVO_API_KEY

# Lancer tous les services
docker-compose up --build
```

Les bases vectorielles ChromaDB sont embarquées dans l'image — **aucune re-indexation nécessaire**.

## Accès

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| MyMaroclear (espace affilié) | http://localhost:3000 |
| Portail public | http://localhost:5173 |
| Dashboard Streamlit (évaluation) | http://localhost:8501 |

```bash
docker-compose up --build
```

## Tests

```bash
cd backend
pytest tests/ -v
```

## Documentation

Voir [SETUP.md](SETUP.md) pour les instructions détaillées (développement local sans Docker).
