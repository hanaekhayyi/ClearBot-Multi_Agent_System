"""
eval_rag_reglementaire.py
=========================
Évaluation du RAG Réglementaire de ClearBot (Recueil AMMC, Loi 35-96, Circulaires).

Métriques calculées (LLM-as-judge + déterministe) :
  - Faithfulness         : la réponse est-elle fidèle aux chunks récupérés ?
  - Answer Relevancy     : la réponse répond-elle à la question juridique ?
  - Keyword Coverage     : les concepts juridiques attendus sont-ils couverts dans la réponse ?
  - Context Support      : le contexte récupéré supporte-t-il bien la question ?
  - Factual Correctness  : la réponse est-elle factuellement correcte vs référence ?
  - Citation Quality     : la réponse cite-t-elle des articles/sources précis ?

Usage :
    cd backend
    python evaluation/eval_rag_reglementaire.py
    python evaluation/eval_rag_reglementaire.py --verbose
    python evaluation/eval_rag_reglementaire.py --save rapports/rag_regl.json
    python evaluation/eval_rag_reglementaire.py --endpoint reglementaire
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# ── Chemins Python ────────────────────────────────────────────────────────────
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
    - Points dans les nombres supprimés (50.000 → 50000)
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
        num_clean = re.sub(r'\s+', '', num_match.group(1))
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


def _parse_json_score(raw: str) -> tuple[float, str]:
    """Extrait score + justification d'une réponse JSON du LLM juge."""
    try:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        data  = json.loads(raw[start:end])
        return float(data["score"]), data.get("justification", "")
    except Exception as e:
        return 0.0, f"Erreur parsing JSON: {e} | Raw: {raw[:100]}"


# ══════════════════════════════════════════════════════════════════════════════
# MÉTRIQUES
# ══════════════════════════════════════════════════════════════════════════════

def score_faithfulness(question: str, answer: str, context: str, api_key: str) -> tuple[float, str]:
    """Vérifie que la réponse juridique est supportée par les chunks récupérés."""
    system = (
        "Tu es un évaluateur expert en droit marocain et en systèmes RAG. "
        "Vérifie si une réponse juridique est entièrement basée sur le contexte fourni."
    )
    user = f"""Contexte juridique récupéré :
\"\"\"
{context[:3000]}
\"\"\"

Question : {question}
Réponse générée : {answer}

Évalue la FAITHFULNESS (fidélité) :
- 1.0 : toutes les affirmations juridiques sont directement dans le contexte.
- 0.5 : réponse partiellement supportée, quelques éléments non vérifiables.
- 0.0 : la réponse contient des affirmations juridiques inventées ou non présentes dans le contexte.

Réponds UNIQUEMENT avec ce format JSON :
{{"score": <float 0.0-1.0>, "justification": "<une phrase>"}}"""

    return _parse_json_score(_llm_judge(system, user, api_key))


def score_answer_relevancy(question: str, answer: str, api_key: str) -> tuple[float, str]:
    """Vérifie que la réponse répond bien à la question juridique posée."""
    system = (
        "Tu es un évaluateur expert en droit marocain. "
        "Évalue si une réponse répond correctement à une question juridique."
    )
    user = f"""Question juridique : {question}
Réponse : {answer}

Évalue la PERTINENCE de la réponse :
- 1.0 : répond directement et complètement à la question juridique.
- 0.5 : partiellement pertinente ou incomplète.
- 0.0 : hors sujet ou ne répond pas à la question.

Réponds UNIQUEMENT avec ce format JSON :
{{"score": <float 0.0-1.0>, "justification": "<une phrase>"}}"""

    return _parse_json_score(_llm_judge(system, user, api_key))


def score_keyword_coverage(answer: str, mots_cles: list[str]) -> tuple[float, str]:
    """
    Keyword Coverage : les concepts juridiques attendus sont-ils couverts dans la réponse ?
    Mesure la couverture des termes juridiques importants dans la réponse générée.
    Calcul déterministe — pas de LLM.
    """
    if not mots_cles:
        return 1.0, "Aucun mot-clé attendu"

    answer_lower  = answer.lower()
    found         = [kw for kw in mots_cles if kw.lower() in answer_lower]
    manquants     = [kw for kw in mots_cles if kw.lower() not in answer_lower]
    score         = len(found) / len(mots_cles)

    just = f"{len(found)}/{len(mots_cles)} concepts juridiques couverts"
    if manquants:
        just += f" | Manquants: {', '.join(manquants)}"
    return score, just


def score_context_support(question: str, context: str, api_key: str) -> tuple[float, str]:
    """
    Context Support : le contexte récupéré supporte-t-il bien la réponse à la question juridique ?
    Évalue si les chunks retournés par le retriever sont pertinents pour la question.
    Score : 0.0 (contexte non pertinent) → 1.0 (contexte parfaitement adapté)
    """
    system = (
        "Tu es un évaluateur expert en RAG juridique. "
        "Évalue si le contexte récupéré est pertinent pour répondre à la question de droit."
    )
    user = f"""Question juridique : {question}

Contexte récupéré :
\"\"\"
{context[:2000]}
\"\"\"

Évalue si le contexte récupéré supporte bien une réponse à cette question juridique.
- 1.0 : le contexte contient exactement les dispositions légales nécessaires.
- 0.5 : contexte partiellement pertinent, contient du bruit ou des articles non liés.
- 0.0 : contexte hors sujet, ne contient pas les dispositions nécessaires.

Réponds UNIQUEMENT avec ce format JSON :
{{"score": <float 0.0-1.0>, "justification": "<une phrase>"}}"""

    return _parse_json_score(_llm_judge(system, user, api_key))


def score_factual_correctness(question: str, answer: str, reference: str, api_key: str) -> tuple[float, str]:
    """Compare la réponse générée avec la réponse de référence annotée."""
    system = (
        "Tu es un expert juriste marocain. "
        "Compare une réponse générée avec une réponse de référence et évalue sa correction factuelle."
    )
    user = f"""Question : {question}

Réponse de référence (annotée manuellement) : {reference}

Réponse générée : {answer}

Évalue la CORRECTION FACTUELLE :
- 1.0 : factuellement correcte et cohérente avec la référence.
- 0.5 : partiellement correcte, quelques inexactitudes mineures.
- 0.0 : erreurs factuelles importantes ou contradictions avec la référence.

Réponds UNIQUEMENT avec ce format JSON :
{{"score": <float 0.0-1.0>, "justification": "<une phrase>"}}"""

    return _parse_json_score(_llm_judge(system, user, api_key))


def score_citation_quality(answer: str) -> tuple[float, str]:
    """
    Citation Quality : la réponse cite-t-elle des articles/lois précis ?
    Calcul déterministe — vérifie la présence de patterns de citation juridique.
    """
    # Patterns de citation juridique attendus dans une réponse réglementaire
    citation_patterns = [
        r"article\s+\d+",                          # Article 12
        r"loi\s+n[°o]?\s*\d+[-–]\d+",             # Loi n° 35-96
        r"loi\s+\d+[-–]\d+",                       # Loi 35-96
        r"dahir\s+n[°o]?\s*\d+",                   # Dahir n°...
        r"circulaire\s+n[°o]?\s*\d+",              # Circulaire n°...
        r"règlement\s+général",                     # Règlement Général
        r"reglement\s+general",
        r"titre\s+[ivxlcdm]+",                     # Titre II
        r"chapitre\s+[ivxlcdm\d]+",                # Chapitre III
        r"alinéa\s+\d+",                           # Alinéa 2
        r"page\s+\d+",                             # page 45
    ]

    answer_lower = answer.lower()
    found_patterns = []
    for pattern in citation_patterns:
        matches = re.findall(pattern, answer_lower)
        if matches:
            found_patterns.extend(matches[:2])  # max 2 par pattern

    if len(found_patterns) >= 3:
        score = 1.0
        just  = f"Bonnes citations : {', '.join(found_patterns[:4])}"
    elif len(found_patterns) >= 1:
        score = 0.6
        just  = f"Citations partielles : {', '.join(found_patterns)}"
    else:
        score = 0.0
        just  = "Aucune citation d'article ou de loi trouvée dans la réponse"

    return score, just


# ══════════════════════════════════════════════════════════════════════════════
# APPEL AU RAG RÉGLEMENTAIRE
# ══════════════════════════════════════════════════════════════════════════════

def call_rag_reglementaire(question: str, endpoint: str,
                            api_url: str = "http://localhost:8000",
                            max_retries: int = 3) -> dict:
    """
    Appelle le RAG réglementaire avec retry automatique en cas de timeout.
    endpoint = "reglementaire" → /chat-reglementaire (direct)
    endpoint = "orchestrateur" → /chat (via orchestrateur)
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            if endpoint == "reglementaire":
                url  = f"{api_url}/chat-reglementaire"
                resp = requests.post(
                    url,
                    json={"message": question, "context": "private"},
                    timeout=240,   # 4 minutes — gpt-oss-120b:free peut être lent
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "answer":   data.get("response", ""),
                    "sources":  data.get("sources", []),
                    "n_chunks": data.get("retrieved_docs_count", 0),
                    "route":    "reglementaire",
                }
            else:
                url  = f"{api_url}/chat"
                resp = requests.post(
                    url,
                    json={"message": question, "context": "private"},
                    timeout=240,
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "answer":   data.get("response", ""),
                    "sources":  data.get("regl_sources", []),
                    "n_chunks": 0,
                    "route":    data.get("route", ""),
                }

        except requests.exceptions.Timeout as e:
            last_error = e
            if attempt < max_retries:
                wait = 10 * (attempt + 1)
                print(f"     {_c(f'⏱ Timeout (tentative {attempt+1}/{max_retries+1}), retry dans {wait}s...', _YELLOW)}")
                time.sleep(wait)
            continue
        except requests.exceptions.ConnectionError:
            raise
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                time.sleep(5)
            continue

    raise last_error


# ══════════════════════════════════════════════════════════════════════════════
# ÉVALUATION PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

def run_eval(dataset_path: str, verbose: bool, save_path: str | None,
             api_url: str, endpoint: str, api_key: str) -> None:

    cases  = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    total  = len(cases)
    errors = 0

    print(f"\n{'═'*68}")
    print(f"  {_c('ÉVALUATION RAG RÉGLEMENTAIRE', _BOLD)}")
    print(f"  Dataset  : {dataset_path}  ({total} questions)")
    print(f"  API      : {api_url}  (endpoint: /{endpoint if endpoint == 'reglementaire' else 'chat'})")
    print(f"  Juge     : {JUDGE_MODEL}")
    print(f"{'═'*68}\n")

    results = []

    scores_faith    = []
    scores_relev    = []
    scores_coverage = []
    scores_support  = []
    scores_factual  = []
    scores_citation = []

    # Grouper par catégorie pour le rapport
    by_category: dict[str, list[float]] = {}

    for i, case in enumerate(cases, 1):
        qid       = case["id"]
        question  = case["question"]
        reference = case["reponse_reference"]
        mots_cles = case.get("mots_cles_attendus", [])
        categorie = case.get("categorie", "general")

        print(f"  [{i:02d}/{total}] {_c(qid, _CYAN)} [{categorie}] — {question[:55]}...")

        # ── 1. Appel au RAG ──────────────────────────────────────────────────
        try:
            rag_result = call_rag_reglementaire(question, endpoint, api_url)
            answer  = rag_result["answer"]
            sources = rag_result["sources"]
            n_chunks = rag_result["n_chunks"]
            # Contexte proxy : sources + réponse (le RAG ne retourne pas les chunks bruts via API)
            context_proxy = (
                f"Sources juridiques récupérées: {', '.join(str(s) for s in sources)}\n\n"
                f"Réponse générée:\n{answer}"
            )
        except requests.exceptions.ConnectionError:
            print(f"     {_c('✗ ERREUR', _RED)}: Backend inaccessible sur {api_url}")
            print(f"     {_c('→ Lance le backend :', _YELLOW)} uvicorn api.api:app --reload --port 8000")
            sys.exit(1)
        except Exception as e:
            print(f"     {_c('✗ ERREUR API', _RED)}: {e}")
            errors += 1
            results.append({
                "id": qid, "question": question, "categorie": categorie,
                "error": str(e),
                "faithfulness": 0, "answer_relevancy": 0, "keyword_coverage": 0,
                "context_support": 0, "factual_correctness": 0, "citation_quality": 0,
            })
            continue

        # ── 2. Métriques ─────────────────────────────────────────────────────
        faith_score,    faith_just    = score_faithfulness(question, answer, context_proxy, api_key)
        relev_score,    relev_just    = score_answer_relevancy(question, answer, api_key)
        coverage_score, coverage_just = score_keyword_coverage(answer, mots_cles)
        support_score,  support_just  = score_context_support(question, context_proxy, api_key)
        factual_score,  factual_just  = score_factual_correctness(question, answer, reference, api_key)
        citation_score, citation_just = score_citation_quality(answer)

        scores_faith.append(faith_score)
        scores_relev.append(relev_score)
        scores_coverage.append(coverage_score)
        scores_support.append(support_score)
        scores_factual.append(factual_score)
        scores_citation.append(citation_score)

        avg = (faith_score + relev_score + coverage_score +
               support_score + factual_score + citation_score) / 6

        # Grouper par catégorie
        by_category.setdefault(categorie, []).append(avg)

        color = _GREEN if avg >= 0.75 else _YELLOW if avg >= 0.5 else _RED
        print(f"     Score global : {_c(f'{avg:.0%}', color)}  "
              f"(chunks: {n_chunks})")
        print(f"     Faith={faith_score:.2f}  Relev={relev_score:.2f}  "
              f"Coverage={coverage_score:.2f}  Support={support_score:.2f}  "
              f"Factual={factual_score:.2f}  Citation={citation_score:.2f}")

        if verbose:
            print(f"\n     {_c('Question  :', _BOLD)} {question}")
            print(f"     {_c('Réponse   :', _BOLD)} {answer[:250]}...")
            print(f"     {_c('Sources   :', _DIM)} {sources[:3]}")
            print(f"     {_c('Faith     :', _DIM)} {faith_just}")
            print(f"     {_c('Relevancy :', _DIM)} {relev_just}")
            print(f"     {_c('Coverage  :', _DIM)} {coverage_just}")
            print(f"     {_c('Support   :', _DIM)} {support_just}")
            print(f"     {_c('Factual   :', _DIM)} {factual_just}")
            print(f"     {_c('Citation  :', _DIM)} {citation_just}\n")

        results.append({
            "id":                  qid,
            "question":            question,
            "categorie":           categorie,
            "answer":              answer,
            "sources":             sources,
            "n_chunks_retrieved":  n_chunks,
            "reponse_reference":   reference,
            "faithfulness":        round(faith_score,    4),
            "answer_relevancy":    round(relev_score,    4),
            "keyword_coverage":    round(coverage_score, 4),
            "context_support":     round(support_score,  4),
            "factual_correctness": round(factual_score,  4),
            "citation_quality":    round(citation_score, 4),
            "score_global":        round(avg,            4),
            "justifications": {
                "faithfulness":        faith_just,
                "answer_relevancy":    relev_just,
                "keyword_coverage":    coverage_just,
                "context_support":     support_just,
                "factual_correctness": factual_just,
                "citation_quality":    citation_just,
            },
        })

        time.sleep(3.0)  # délai entre questions — évite le rate limiting sur gpt-oss-120b:free

    # ── Résumé global ─────────────────────────────────────────────────────────
    def _avg(lst): return sum(lst) / len(lst) if lst else 0.0

    m_faith    = _avg(scores_faith)
    m_relev    = _avg(scores_relev)
    m_coverage = _avg(scores_coverage)
    m_support  = _avg(scores_support)
    m_factual  = _avg(scores_factual)
    m_citation = _avg(scores_citation)
    m_global   = _avg([m_faith, m_relev, m_coverage, m_support, m_factual, m_citation])

    print(f"\n{'═'*68}")
    print(f"  {_c('RÉSUMÉ GLOBAL — RAG RÉGLEMENTAIRE', _BOLD)}")
    print(f"{'─'*68}")
    print(f"  Questions évaluées : {total - errors}  ({errors} erreur(s))")
    print(f"\n  {'Faithfulness':<24} {_bar(m_faith)}  {m_faith:.1%}")
    print(f"  {'Answer Relevancy':<24} {_bar(m_relev)}  {m_relev:.1%}")
    print(f"  {'Keyword Coverage':<24} {_bar(m_coverage)}  {m_coverage:.1%}")
    print(f"  {'Context Support':<24} {_bar(m_support)}  {m_support:.1%}")
    print(f"  {'Factual Correctness':<24} {_bar(m_factual)}  {m_factual:.1%}")
    print(f"  {'Citation Quality':<24} {_bar(m_citation)}  {m_citation:.1%}")
    print(f"{'─'*68}")
    print(f"  {'Score Global RAG':<24} {_bar(m_global)}  {_c(f'{m_global:.1%}', _BOLD)}")

    # ── Scores par catégorie ──────────────────────────────────────────────────
    if by_category:
        print(f"\n{'─'*68}")
        print(f"  {_c('SCORES PAR CATÉGORIE', _BOLD)}")
        for cat, scores in sorted(by_category.items()):
            cat_avg = _avg(scores)
            print(f"  {cat:<25} {_bar(cat_avg, 15)}  {cat_avg:.1%}  ({len(scores)} questions)")

    print(f"{'═'*68}\n")

    # ── Cas faibles ───────────────────────────────────────────────────────────
    faibles = [r for r in results if r.get("score_global", 1) < 0.5 and "error" not in r]
    if faibles:
        print(f"  {_c('CAS FAIBLES (score < 50%) :', _BOLD)}")
        for r in faibles:
            sg = f"{r['score_global']:.0%}"
            print(f"\n  [{r['id']}] {_c(sg, _RED)} — {r['question'][:70]}")
            print(f"    Réponse : {r['answer'][:150]}...")
            if r.get("justifications", {}).get("citation_quality"):
                print(f"    Citation: {r['justifications']['citation_quality']}")

    # ── Sauvegarde ────────────────────────────────────────────────────────────
    if save_path:
        rapport = {
            "type":          "RAG Réglementaire",
            "dataset":       dataset_path,
            "endpoint":      endpoint,
            "total":         total,
            "erreurs":       errors,
            "juge_model":    JUDGE_MODEL,
            "scores_moyens": {
                "faithfulness":        round(m_faith,    4),
                "answer_relevancy":    round(m_relev,    4),
                "keyword_coverage":    round(m_coverage, 4),
                "context_support":     round(m_support,  4),
                "factual_correctness": round(m_factual,  4),
                "citation_quality":    round(m_citation, 4),
                "score_global":        round(m_global,   4),
            },
            "scores_par_categorie": {
                cat: round(_avg(scores), 4)
                for cat, scores in by_category.items()
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
    parser = argparse.ArgumentParser(
        description="Évaluation du RAG Réglementaire ClearBot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python evaluation/eval_rag_reglementaire.py
  python evaluation/eval_rag_reglementaire.py --verbose
  python evaluation/eval_rag_reglementaire.py --save rapports/rag_regl.json
  python evaluation/eval_rag_reglementaire.py --endpoint orchestrateur
        """,
    )
    parser.add_argument(
        "--dataset", default="evaluation/datasets/rag_reglementaire_dataset.json",
        help="Chemin vers le dataset JSON"
    )
    parser.add_argument("--verbose",  action="store_true", help="Affiche les détails de chaque cas")
    parser.add_argument("--save",     metavar="FILE", default=None, help="Sauvegarde le rapport JSON")
    parser.add_argument("--api",      default="http://localhost:8000", help="URL de l'API backend")
    parser.add_argument(
        "--endpoint", default="reglementaire",
        choices=["reglementaire", "orchestrateur"],
        help="Endpoint à utiliser : 'reglementaire' (/chat-reglementaire) ou 'orchestrateur' (/chat)"
    )
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print(f"{_c('ERREUR', _RED)}: OPENROUTER_API_KEY non définie dans .env")
        sys.exit(1)

    if not Path(args.dataset).exists():
        print(f"{_c('ERREUR', _RED)}: Dataset introuvable → {args.dataset}")
        sys.exit(1)

    run_eval(args.dataset, args.verbose, args.save, args.api, args.endpoint, api_key)


if __name__ == "__main__":
    main()
