# Agent Orchestrateur

## Rôle
Coordonne le fonctionnement global du système multi-agents Maroclear.  
Reçoit chaque message utilisateur et décide quel agent appeler.

## Logique de routage
| Priorité | Agent cible | Déclencheur |
|---|---|---|
| 1 | `conseiller_reglementaire` | Mots-clés juridiques (Loi 35-96, RG, article...) |
| 2 | `support_classification` | Incident / demande / réclamation détectés |
| 3 | `informationnel_procedural` | Question documentaire générale |
| — | Réponse par défaut | Aucun agent éligible |

## Fichiers
- `agent.py` — classe `OrchestratorAgent`
- `config.yaml` — configuration de routage
- `schemas.py` — modèles Pydantic input/output

## Dépendances
- `backend/shared/core/` — `AgentMessage`, `AgentContext`
- `backend/shared/base/` — `BaseAgent`
