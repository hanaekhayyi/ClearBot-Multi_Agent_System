"""
eval_rag_informationnel.py
==========================
Évaluation du RAG Informationnel/Procédural de ClearBot.

Métriques calculées (LLM-as-judge + déterministe) :
  - Faithfulness        : la réponse est-elle fidèle aux chunks récupérés ?
  - Answer Relevancy    : la réponse répond-elle à la question ?
  - Keyword Coverage    : les concepts-clés attendus sont-ils couverts dans la réponse ?
  - Context Support     : le contexte récupéré supporte-t-il bien la réponse ?
  - Factual Correctness : la réponse est-elle factuellement correcte vs référence ?

Usage :
    cd backend
    python evaluation/eval_rag_informationnel.py
    python evaluation/eval_rag_informationnel.py --verbose
    python evaluation/eval_rag_informationnel.py --save evaluation/rapports/rag_info_final.json
    python evaluation/eval_rag_informationnel.py --dataset evaluation/datasets/rag_informationnel_dataset.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

import requests

# ══════════════════════════════════════════════════════════════════════════════
# COULEURS CONSOLE
# ══════════════════════════════════════════════════════════════════════════════
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_CYAN   = "\033[96m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_RESET  = "\033[0m"

def _c(text, code): return f"{code}{text}{_RESET}"
def _bar(v, w=20):
    filled = round(v * w)
    col = _GREEN if v >= 0.75 else _YELLOW if v >= 0.5 else _RED
    return _c("█" * filled + "░" * (w - filled), col)


# ══════════════════════════════════════════════════════════════════════════════
# NORMALISATION ROBUSTE
# ══════════════════════════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    """
    Normalise un texte pour comparaison robuste :
    - Minuscules
    - Espaces insécables → espaces normaux
    - Points dans les nombres supprimés (10.000 → 10000)
    - Tirets longs normalisés
    - Espaces multiples → espace simple
    """
    text = text.lower()
    text = text.replace('\u00a0', ' ').replace('\u202f', ' ').replace('\u2009', ' ')
    text = re.sub(r'(\d)\.(\d)', r'\1\2', text)
    text = text.replace('–', '-').replace('—', '-')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _keyword_matches(keyword: str, text_norm: str) -> bool:
    """
    Vérifie si un mot-clé est couvert dans le texte normalisé.
    Stratégie multi-niveaux :
    1. Matching exact normalisé
    2. Pour les références légales (article X, loi X) : matching du numéro seul
    3. Pour les montants : matching sans séparateur de milliers
    4. Matching des tokens principaux (tous les mots de 4+ chars présents)
    """
    kw_norm = _normalize(keyword)

    # 1. Matching exact normalisé
    if kw_norm in text_norm:
        return True

    # 2. Références légales : "article 73" → chercher "73" avec "article" ou "art"
    art_match = re.match(r'(article|art\.?)\s+(\w+[-\w]*)', kw_norm)
    if art_match:
        num = art_match.group(2)
        if num in text_norm and ('article' in text_norm or 'art.' in text_norm or 'art ' in text_norm):
            return True

    # 3. Montants numériques : "50 000" → chercher "50000" ou "50 000" ou "50.000"
    num_match = re.match(r'^(\d[\d\s]*\d)\s*(dh|dirhams?)?$', kw_norm.strip())
    if num_match:
        num_clean = re.sub(r'\s+', '', num_match.group(1))  # "50 000" → "50000"
        # Chercher le nombre sous différentes formes
        variants = [num_clean, num_match.group(1)]
        for v in variants:
            if v in text_norm:
                return True

    # 4. Matching par tokens principaux (mots de 4+ caractères)
    tokens = [w for w in kw_norm.split() if len(w) >= 4]
    if len(tokens) >= 2 and all(t in text_norm for t in tokens):
        return True

    # 5. Pour les mots-clés courts (1 mot), matching exact suffit
    if len(kw_norm.split()) == 1 and len(kw_norm) >= 4:
        return kw_norm in text_norm

    return False


# ══════════════════════════════════════════════════════════════════════════════
# CLIENT LLM JUGE
# ══════════════════════════════════════════════════════════════════════════════

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
JUDGE_MODEL    = "openai/gpt-4o-mini"


def _llm_judge(system: str, user: str, api_key: str) -> str:
    resp = requests.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": JUDGE_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "max_tokens": 512,
            "temperature": 0.0,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ══════════════════════════════════════════════════════════════════════════════
# MÉTRIQUES
# ══════════════════════════════════════════════════════════════════════════════

def score_faithfulness(question: str, answer: str, context: str, api_key: str) -> tuple[float, str]:
    """Faithfulness : la réponse est-elle fidèle au contexte récupéré ?"""
    system = (
        "Tu es un évaluateur expert en RAG. "
        "Ton rôle est de vérifier si une réponse est fidèle au contexte fourni, "
        "sans hallucination ni information inventée."
    )
    user = f"""Contexte récupéré :
\"\"\"
{context[:3000]}
\"\"\"

Question posée : {question}
Réponse générée : {answer}

Évalue la FAITHFULNESS (fidélité) :
- 1.0 : toutes les affirmations sont directement supportées par le contexte.
- 0.5 : partiellement supportée, quelques éléments hors contexte.
- 0.0 : informations inventées ou contredisant le contexte.

Réponds UNIQUEMENT avec ce format JSON :
{{"score": <float 0.0-1.0>, "justification": "<une phrase>"}}"""

    try:
        raw = _llm_judge(system, user, api_key)
        start = raw.find("{"); end = raw.rfind("}") + 1
        data  = json.loads(raw[start:end])
        return float(data["score"]), data.get("justification", "")
    except Exception as e:
        return 0.0, f"Erreur parsing: {e}"


def score_answer_relevancy(question: str, answer: str, api_key: str) -> tuple[float, str]:
    """Answer Relevancy : la réponse répond-elle bien à la question ?"""
    system = (
        "Tu es un évaluateur expert en systèmes de questions-réponses. "
        "Évalue si une réponse répond correctement et complètement à la question posée."
    )
    user = f"""Question : {question}
Réponse : {answer}

Évalue la PERTINENCE :
- 1.0 : répond directement et complètement.
- 0.5 : partiellement pertinente ou incomplète.
- 0.0 : hors sujet ou ne répond pas.

Réponds UNIQUEMENT avec ce format JSON :
{{"score": <float 0.0-1.0>, "justification": "<une phrase>"}}"""

    try:
        raw = _llm_judge(system, user, api_key)
        start = raw.find("{"); end = raw.rfind("}") + 1
        data  = json.loads(raw[start:end])
        return float(data["score"]), data.get("justification", "")
    except Exception as e:
        return 0.0, f"Erreur parsing: {e}"


def score_keyword_coverage(answer: str, mots_cles: list[str]) -> tuple[float, str]:
    """
    Keyword Coverage : les concepts-clés attendus sont-ils couverts dans la réponse ?
    Utilise un matching multi-niveaux robuste :
    - Matching exact normalisé
    - Matching des références légales (article X → cherche numéro + mot "article")
    - Matching des montants (50.000 / 50 000 / 50000)
    - Matching par tokens principaux (tous les mots de 4+ chars)
    """
    if not mots_cles:
        return 1.0, "Aucun mot-clé attendu"

    answer_norm = _normalize(answer)
    found     = [kw for kw in mots_cles if _keyword_matches(kw, answer_norm)]
    manquants = [kw for kw in mots_cles if not _keyword_matches(kw, answer_norm)]
    score     = len(found) / len(mots_cles)

    just = f"{len(found)}/{len(mots_cles)} concepts-clés couverts"
    if manquants:
        just += f" | Manquants: {', '.join(manquants)}"
    return score, just


def score_context_support(question: str, context: str, api_key: str) -> tuple[float, str]:
    """
    Context Support : le contexte récupéré supporte-t-il bien la réponse à la question ?
    Évalue si les informations retournées par le retriever sont pertinentes.
    """
    system = (
        "Tu es un évaluateur expert en RAG. "
        "Évalue si le contexte récupéré est pertinent et utile pour répondre à la question."
    )
    user = f"""Question : {question}

Contexte récupéré :
\"\"\"
{context[:2000]}
\"\"\"

Évalue si le contexte supporte bien une réponse à cette question.
- 1.0 : contient exactement les informations nécessaires.
- 0.5 : partiellement pertinent, contient du bruit.
- 0.0 : hors sujet ou ne contient pas les informations nécessaires.

Réponds UNIQUEMENT avec ce format JSON :
{{"score": <float 0.0-1.0>, "justification": "<une phrase>"}}"""

    try:
        raw = _llm_judge(system, user, api_key)
        start = raw.find("{"); end = raw.rfind("}") + 1
        data  = json.loads(raw[start:end])
        return float(data["score"]), data.get("justification", "")
    except Exception as e:
        return 0.0, f"Erreur parsing: {e}"


def score_factual_correctness(question: str, answer: str, reference: str, api_key: str) -> tuple[float, str]:
    """Factual Correctness : la réponse est-elle factuellement correcte vs référence ?"""
    system = (
        "Tu es un évaluateur expert. "
        "Compare une réponse générée avec une réponse de référence et évalue sa correction factuelle."
    )
    user = f"""Question : {question}
Réponse de référence : {reference}
Réponse générée : {answer}

Évalue la CORRECTION FACTUELLE :
- 1.0 : factuellement correcte et cohérente avec la référence.
- 0.5 : partiellement correcte, inexactitudes mineures.
- 0.0 : erreurs factuelles importantes.

Réponds UNIQUEMENT avec ce format JSON :
{{"score": <float 0.0-1.0>, "justification": "<une phrase>"}}"""

    try:
        raw = _llm_judge(system, user, api_key)
        start = raw.find("{"); end = raw.rfind("}") + 1
        data  = json.loads(raw[start:end])
        return float(data["score"]), data.get("justification", "")
    except Exception as e:
        return 0.0, f"Erreur parsing: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# APPEL AU RAG INFORMATIONNEL
# ══════════════════════════════════════════════════════════════════════════════

def call_rag_informationnel(question: str, api_url: str = "http://localhost:8000",
                            max_retries: int = 2) -> dict:
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(
                f"{api_url}/chat-informationnel",
                json={"message": question, "context": "public"},
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "answer":  data.get("response", ""),
                "sources": data.get("rag_sources", []),
                "route":   data.get("route", "rag"),
                "agent":   data.get("agent_used", "RAGAgent"),
            }
        except requests.exceptions.Timeout as e:
            last_error = e
            if attempt < max_retries:
                print(f"     {_c(f'⏱ Timeout (tentative {attempt+1}/{max_retries+1}), retry dans 5s...', _YELLOW)}")
                time.sleep(5)
            continue
        except requests.exceptions.ConnectionError:
            raise
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(3)
            continue
    raise last_error


# ══════════════════════════════════════════════════════════════════════════════
# ÉVALUATION PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

def run_eval(dataset_path: str, verbose: bool, save_path: str | None,
             api_url: str, api_key: str) -> None:

    cases  = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    total  = len(cases)
    errors = 0

    print(f"\n{'═'*68}")
    print(f"  {_c('ÉVALUATION RAG INFORMATIONNEL', _BOLD)}")
    print(f"  Dataset : {dataset_path}  ({total} questions)")
    print(f"  API     : {api_url}")
    print(f"  Juge    : {JUDGE_MODEL}")
    print(f"{'═'*68}\n")

    results         = []
    scores_faith    = []
    scores_relev    = []
    scores_coverage = []
    scores_support  = []
    scores_factual  = []

    for i, case in enumerate(cases, 1):
        qid       = case["id"]
        question  = case["question"]
        reference = case["reponse_reference"]
        mots_cles = case.get("mots_cles_attendus", [])
        categorie = case.get("categorie", "")

        print(f"  [{i:02d}/{total}] {_c(qid, _CYAN)} — {question[:60]}...")

        try:
            rag_result    = call_rag_informationnel(question, api_url)
            answer        = rag_result["answer"]
            sources       = rag_result["sources"]
            context_proxy = f"Sources récupérées: {', '.join(sources)}\n\nRéponse générée: {answer}"
        except requests.exceptions.ConnectionError:
            print(f"     {_c('✗ ERREUR', _RED)}: Backend inaccessible sur {api_url}")
            print(f"     {_c('→ Lance le backend :', _YELLOW)} uvicorn api.api:app --reload --port 8000")
            sys.exit(1)
        except Exception as e:
            print(f"     {_c('✗ ERREUR API', _RED)}: {e}")
            errors += 1
            results.append({
                "id": qid, "question": question, "error": str(e),
                "faithfulness": 0, "answer_relevancy": 0,
                "keyword_coverage": 0, "context_support": 0, "factual_correctness": 0,
            })
            continue

        faith_score,    faith_just    = score_faithfulness(question, answer, context_proxy, api_key)
        relev_score,    relev_just    = score_answer_relevancy(question, answer, api_key)
        coverage_score, coverage_just = score_keyword_coverage(answer, mots_cles)
        support_score,  support_just  = score_context_support(question, context_proxy, api_key)
        factual_score,  factual_just  = score_factual_correctness(question, answer, reference, api_key)

        scores_faith.append(faith_score)
        scores_relev.append(relev_score)
        scores_coverage.append(coverage_score)
        scores_support.append(support_score)
        scores_factual.append(factual_score)

        avg   = (faith_score + relev_score + coverage_score + support_score + factual_score) / 5
        color = _GREEN if avg >= 0.75 else _YELLOW if avg >= 0.5 else _RED

        print(f"     Score global : {_c(f'{avg:.0%}', color)}")
        print(f"     Faith={faith_score:.2f}  Relev={relev_score:.2f}  "
              f"Coverage={coverage_score:.2f}  Support={support_score:.2f}  Factual={factual_score:.2f}")

        if verbose:
            print(f"\n     {_c('Question  :', _BOLD)} {question}")
            print(f"     {_c('Réponse   :', _BOLD)} {answer[:200]}...")
            print(f"     {_c('Sources   :', _DIM)} {sources}")
            print(f"     {_c('Faith     :', _DIM)} {faith_just}")
            print(f"     {_c('Relevancy :', _DIM)} {relev_just}")
            print(f"     {_c('Coverage  :', _DIM)} {coverage_just}")
            print(f"     {_c('Support   :', _DIM)} {support_just}")
            print(f"     {_c('Factual   :', _DIM)} {factual_just}\n")

        results.append({
            "id":                  qid,
            "question":            question,
            "categorie":           categorie,
            "answer":              answer,
            "sources":             sources,
            "reponse_reference":   reference,
            "faithfulness":        round(faith_score,    4),
            "answer_relevancy":    round(relev_score,    4),
            "keyword_coverage":    round(coverage_score, 4),
            "context_support":     round(support_score,  4),
            "factual_correctness": round(factual_score,  4),
            "score_global":        round(avg,            4),
            "justifications": {
                "faithfulness":        faith_just,
                "answer_relevancy":    relev_just,
                "keyword_coverage":    coverage_just,
                "context_support":     support_just,
                "factual_correctness": factual_just,
            },
        })

        time.sleep(1.0)

    def _avg(lst): return sum(lst) / len(lst) if lst else 0.0

    m_faith    = _avg(scores_faith)
    m_relev    = _avg(scores_relev)
    m_coverage = _avg(scores_coverage)
    m_support  = _avg(scores_support)
    m_factual  = _avg(scores_factual)
    m_global   = _avg([m_faith, m_relev, m_coverage, m_support, m_factual])

    print(f"\n{'═'*68}")
    print(f"  {_c('RÉSUMÉ GLOBAL — RAG INFORMATIONNEL', _BOLD)}")
    print(f"{'─'*68}")
    print(f"  Questions évaluées : {total - errors}  ({errors} erreur(s))")
    print(f"\n  {'Faithfulness':<22} {_bar(m_faith)}  {m_faith:.1%}")
    print(f"  {'Answer Relevancy':<22} {_bar(m_relev)}  {m_relev:.1%}")
    print(f"  {'Keyword Coverage':<22} {_bar(m_coverage)}  {m_coverage:.1%}")
    print(f"  {'Context Support':<22} {_bar(m_support)}  {m_support:.1%}")
    print(f"  {'Factual Correctness':<22} {_bar(m_factual)}  {m_factual:.1%}")
    print(f"{'─'*68}")
    print(f"  {'Score Global RAG':<22} {_bar(m_global)}  {_c(f'{m_global:.1%}', _BOLD)}")
    print(f"{'═'*68}\n")

    faibles = [r for r in results if r.get("score_global", 1) < 0.5 and "error" not in r]
    if faibles:
        print(f"  {_c('CAS FAIBLES (score < 50%) :', _BOLD)}")
        for r in faibles:
            sg = f"{r['score_global']:.0%}"
            print(f"\n  [{r['id']}] {_c(sg, _RED)} — {r['question'][:70]}")
            print(f"    Réponse : {r['answer'][:120]}...")

    if save_path:
        rapport = {
            "type":          "RAG Informationnel",
            "dataset":       dataset_path,
            "total":         total,
            "erreurs":       errors,
            "juge_model":    JUDGE_MODEL,
            "scores_moyens": {
                "faithfulness":        round(m_faith,    4),
                "answer_relevancy":    round(m_relev,    4),
                "keyword_coverage":    round(m_coverage, 4),
                "context_support":     round(m_support,  4),
                "factual_correctness": round(m_factual,  4),
                "score_global":        round(m_global,   4),
            },
            "details": results,
        }
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_text(
            json.dumps(rapport, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  Rapport sauvegardé → {save_path}\n")

    sys.exit(0 if m_global >= 0.65 else 1)


# ══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Évaluation du RAG Informationnel ClearBot")
    parser.add_argument("--dataset", default="evaluation/datasets/rag_informationnel_dataset.json")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--save",    metavar="FILE", default=None)
    parser.add_argument("--api",     default="http://localhost:8000")
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print(f"{_c('ERREUR', _RED)}: OPENROUTER_API_KEY non définie dans .env")
        sys.exit(1)
    if not Path(args.dataset).exists():
        print(f"{_c('ERREUR', _RED)}: Dataset introuvable → {args.dataset}")
        sys.exit(1)

    run_eval(args.dataset, args.verbose, args.save, args.api, api_key)


if __name__ == "__main__":
    main()
