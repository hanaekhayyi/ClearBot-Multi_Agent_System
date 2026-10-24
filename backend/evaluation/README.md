# Évaluation des RAG — ClearBot

Évaluation des deux pipelines RAG de ClearBot avec la méthode **LLM-as-judge**.

## Structure

```
evaluation/
├── eval_rag_informationnel.py    ← Évaluation RAG Informationnel/Procédural
├── eval_rag_reglementaire.py     ← Évaluation RAG Réglementaire (Recueil AMMC)
├── datasets/
│   ├── rag_informationnel_dataset.json   ← 20 questions sur Maroclear
│   └── rag_reglementaire_dataset.json    ← 15 questions juridiques
└── rapports/                     ← Rapports JSON générés
```

## Métriques

### RAG Informationnel (5 métriques)

| Métrique | Description | Méthode |
|---|---|---|
| **Faithfulness** | La réponse est-elle fidèle aux chunks récupérés ? | LLM-as-judge |
| **Answer Relevancy** | La réponse répond-elle à la question ? | LLM-as-judge |
| **Context Recall** | Les mots-clés attendus sont-ils dans les chunks ? | Déterministe |
| **Context Precision** | Les chunks récupérés sont-ils pertinents ? | LLM-as-judge |
| **Factual Correctness** | La réponse est-elle correcte vs référence ? | LLM-as-judge |

### RAG Réglementaire (6 métriques)

Mêmes 5 métriques + :

| Métrique | Description | Méthode |
|---|---|---|
| **Citation Quality** | La réponse cite-t-elle des articles/lois précis ? | Déterministe (regex) |

## Prérequis

1. Le backend doit être lancé : `uvicorn api.api:app --reload --port 8000`
2. `OPENROUTER_API_KEY` doit être définie dans `backend/.env`
3. Les bases vectorielles doivent être indexées

## Usage

```bash
# Depuis le dossier backend/
cd backend

# RAG Informationnel
python evaluation/eval_rag_informationnel.py
python evaluation/eval_rag_informationnel.py --verbose
python evaluation/eval_rag_informationnel.py --save evaluation/rapports/rag_info.json

# RAG Réglementaire
python evaluation/eval_rag_reglementaire.py
python evaluation/eval_rag_reglementaire.py --verbose
python evaluation/eval_rag_reglementaire.py --save evaluation/rapports/rag_regl.json

# Via l'orchestrateur (teste aussi le routage)
python evaluation/eval_rag_reglementaire.py --endpoint orchestrateur
```

## Interprétation des scores

| Score global | Interprétation |
|---|---|
| ≥ 75% | Excellent — RAG performant |
| 65–75% | Bon — quelques améliorations possibles |
| 50–65% | Moyen — revoir le chunking ou les embeddings |
| < 50% | Insuffisant — problème de retrieval ou de génération |

## Modèle juge

Le LLM juge utilisé est `openai/gpt-4o-mini` via OpenRouter.
Il est différent du modèle de génération (`gpt-oss-120b`) pour éviter le biais d'auto-évaluation.

## Format des datasets

```json
{
  "id": "RI001",
  "question": "Qu'est-ce que Maroclear ?",
  "reponse_reference": "Maroclear est le dépositaire central...",
  "mots_cles_attendus": ["dépositaire central", "conservation", "règlement-livraison"],
  "categorie": "definition"
}
```
