# ClearBot — Known Issues

Ce document recense les problèmes connus et les limitations identifiées au moment de la livraison.

## 1. Fonctionnalités

- `Auto-Dispatcher` : le mécanisme email est fonctionnel, mais dépend d'une configuration Brevo valide et d'un expéditeur vérifié.
- `RAG réglementaire` : nécessite que le dossier `backend/agents/conseiller_reglementaire/data/vectordb/` soit présent et indexé.
- `RAG informationnel` : les performances peuvent varier selon la qualité des documents PDF et du glossaire.
- `Authentification MyMaroclear` : le raccordement réel à l’authentification institutionnelle n’est pas encore intégré.

## 2. Déploiement

- Docker : la stack fonctionne localement, mais l'orchestration dépend des images Docker et de la disponibilité des ports `8000`, `3000`, `5173`, `8501`.
- Variables d’environnement : les clés `OPENROUTER_API_KEY` et `BREVO_API_KEY` sont obligatoires.
- Ollama : nécessaire si le mode local est utilisé pour `bge-m3`.

## 3. Performances et données

- Le modèle `bge-m3` peut nécessiter des ressources CPU/GPU importantes.
- Les bases vectorielles ChromaDB sont volumineuses ; en cas de ré-indexation, prévoir du temps de calcul.

## 4. Tests

- Tests backend : `68 passed`.
- Il est recommandé de relancer `pytest -q backend/tests` après toute modification majeure.

## 5. Limites connues

- Le calcul de priorité des tickets reste interne et n’est pas exposé à l’affilié.
- La journalisation complète des conversations n’est pas encore formalisée pour l’audit.
- Les évaluations RAG sont basées sur une méthode `LLM-as-judge` et doivent être complétées par une revue humaine.

## 6. Recommandations

- Vérifier que les dossiers `vectordb` sont bien présents avant le déploiement.
- Valider les clés API et les expéditeurs Brevo dans l’environnement de production.
- Prévoir une phase pilote pour mesurer les gains opérationnels et les ajustements métier.
