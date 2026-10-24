# Agent Auto-Dispatcher

## Rôle
Remplissage automatique des formulaires pour incident/demande/réclamation,  
calcul de priorité et envoi d'email au dispatcher.

## Capacités
- Extraction automatique des informations depuis la conversation (via ClassificationAgent)
- Pré-remplissage des formulaires MyMaroclear
- Calcul de priorité OLA (P1 à P4)
- Envoi d'email au dispatcher via Brevo (SendinBlue)

## Fichiers
- `agent.py` — classe `AutoDispatcherAgent`
- `config.yaml` — configuration
- `schemas.py` — modèles Pydantic input/output
- `.env.example` — variables d'environnement requises

## Variables d'environnement
```
BREVO_API_KEY=...
DISPATCHER_EMAIL=...
```

## Dépendances
- `backend/shared/core/` — `AgentMessage`, `AgentContext`
- `backend/agents/support_classification/` — résultats de classification
