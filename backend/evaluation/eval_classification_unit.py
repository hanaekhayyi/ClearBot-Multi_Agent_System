"""
eval_classification_unit.py
============================
Évaluation UNITAIRE de l'agent de classification ClearBot.
Appelle ClassificationAgent directement (sans passer par l'API).

Métriques calculées :
  - Accuracy globale
  - Précision, Rappel, F1-score par classe
  - F1 macro / F1 weighted
  - Matrice de confusion
  - Confiance moyenne par classe

Usage :
    cd backend
    python evaluation/eval_classification_unit.py
    python evaluation/eval_classification_unit.py --verbose
    python evaluation/eval_classification_unit.py --save evaluation/rapports/classification_unit.json
    python evaluation/eval_classification_unit.py --cases evaluation/datasets/classification_cases.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

# ── Chemins Python ────────────────────────────────────────────────────────────
BACKEND_DIR    = Path(__file__).parent.parent
CLASSIF_DIR    = BACKEND_DIR / "agents" / "support_classification"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(CLASSIF_DIR))   # pour importer core.agent

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(CLASSIF_DIR / ".env")


# ══════════════════════════════════════════════════════════════════════════════
# CALCUL DES MÉTRIQUES
# ══════════════════════════════════════════════════════════════════════════════

def compute_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    all_classes = sorted(set(y_true) | set(y_pred))
    confusion = {c: {c2: 0 for c2 in all_classes} for c in all_classes}
    for true, pred in zip(y_true, y_pred):
        confusion[true][pred] += 1

    per_class = {}
    for cls in all_classes:
        tp      = confusion[cls][cls]
        fp      = sum(confusion[other][cls] for other in all_classes if other != cls)
        fn      = sum(confusion[cls][other] for other in all_classes if other != cls)
        support = sum(confusion[cls].values())
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)
        per_class[cls] = {
            "precision": round(precision, 4),
            "recall":    round(recall,    4),
            "f1":        round(f1,        4),
            "support":   support,
            "tp": tp, "fp": fp, "fn": fn,
        }

    n         = len(y_true)
    accuracy  = sum(1 for t, p in zip(y_true, y_pred) if t == p) / n if n > 0 else 0.0
    total_sup = sum(m["support"] for m in per_class.values())

    f1_macro    = sum(m["f1"] for m in per_class.values()) / len(per_class) if per_class else 0.0
    f1_weighted = (sum(m["f1"] * m["support"] for m in per_class.values()) / total_sup
                   if total_sup > 0 else 0.0)
    prec_macro  = sum(m["precision"] for m in per_class.values()) / len(per_class) if per_class else 0.0
    rec_macro   = sum(m["recall"]    for m in per_class.values()) / len(per_class) if per_class else 0.0

    return {
        "accuracy":        round(accuracy,    4),
        "f1_macro":        round(f1_macro,    4),
        "f1_weighted":     round(f1_weighted, 4),
        "precision_macro": round(prec_macro,  4),
        "recall_macro":    round(rec_macro,   4),
        "per_class":       per_class,
        "confusion":       confusion,
        "all_classes":     all_classes,
        "n":               n,
    }


# ══════════════════════════════════════════════════════════════════════════════
# AFFICHAGE
# ══════════════════════════════════════════════════════════════════════════════

_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_CYAN   = "\033[96m"
_DIM    = "\033[2m"
_BOLD   = "\033[1m"
_RESET  = "\033[0m"

CLASS_COLORS = {
    "INCIDENT":    _YELLOW,
    "DEMANDE":     _GREEN,
    "RÉCLAMATION": _RED,
    "AMBIGU":      _CYAN,
}

def _color(text, code): return f"{code}{text}{_RESET}"
def _bar(v, w=20):
    filled = round(v * w)
    col = _GREEN if v >= 0.9 else _YELLOW if v >= 0.7 else _RED
    return _color("█" * filled + "░" * (w - filled), col)


# ══════════════════════════════════════════════════════════════════════════════
# ÉVALUATION PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

def run_eval(cases_path: str, verbose: bool, save_path: str | None) -> None:
    from core.agent import ClassificationAgent  # import relatif à CLASSIF_DIR

    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    agent = ClassificationAgent()
    total = len(cases)

    print(f"\n{'═'*64}")
    print(f"  {_BOLD}ÉVALUATION UNITAIRE — CLASSIFICATION{_RESET}")
    print(f"  {total} cas de référence  |  Dataset : {cases_path}")
    print(f"{'═'*64}\n")

    y_true:      list[str]              = []
    y_pred:      list[str]              = []
    confidences: dict[str, list[float]] = defaultdict(list)
    errors:      int                    = 0
    details:     list[dict]             = []

    for case in cases:
        cid     = case["id"]
        texte   = case["texte"]
        attendu = case["classe_attendue"]
        note    = case.get("note", "")

        try:
            result = agent.run_batch(texte, ticket_id=cid)
            obtenu = result.classe.value
            conf   = result.confiance

            y_true.append(attendu)
            y_pred.append(obtenu)
            confidences[obtenu].append(conf)

            correct = (obtenu == attendu)
            status  = "✓" if correct else "✗"
            col     = _GREEN if correct else _RED

            line = f"  {_color(status, col)} [{cid}] {attendu:<14} → {obtenu:<14} ({conf:.0%})"
            if verbose:
                line += f"\n      {_DIM}{texte[:90]}{_RESET}"
                if note:
                    line += f"\n      💡 {note}"
            print(line)

            details.append({
                "id": cid, "texte": texte, "attendu": attendu,
                "obtenu": obtenu, "confiance": conf, "correct": correct, "note": note,
            })

        except Exception as exc:
            print(f"  {_color('✗', _RED)} [{cid}] ERREUR : {exc}")
            errors += 1
            details.append({
                "id": cid, "texte": texte, "attendu": attendu,
                "obtenu": "ERREUR", "confiance": 0.0, "correct": False, "note": str(exc),
            })

        time.sleep(0.5)

    if not y_true:
        print("Aucun résultat.")
        sys.exit(1)

    metrics = compute_metrics(y_true, y_pred)
    acc = metrics["accuracy"]
    f1m = metrics["f1_macro"]
    f1w = metrics["f1_weighted"]

    print(f"\n{'═'*64}")
    print(f"  {_BOLD}RÉSUMÉ GLOBAL{_RESET}")
    print(f"{'─'*64}")
    print(f"  Cas évalués     : {total}  ({errors} erreur(s))")
    print(f"\n  Accuracy        : {_bar(acc)}  {acc:.1%}")
    print(f"  F1 macro        : {_bar(f1m)}  {f1m:.1%}  {_DIM}(moyenne par classe){_RESET}")
    print(f"  F1 weighted     : {_bar(f1w)}  {f1w:.1%}  {_DIM}(pondéré par support){_RESET}")
    print(f"  Précision macro : {metrics['precision_macro']:.1%}")
    print(f"  Rappel macro    : {metrics['recall_macro']:.1%}")

    # Matrice de confusion
    all_cls = metrics["all_classes"]
    col_w   = 13
    print(f"\n  Matrice de confusion  {_DIM}(lignes=attendu, colonnes=obtenu){_RESET}\n")
    header = f"  {'':15}"
    for cls in all_cls:
        header += f"{_color(cls[:col_w], CLASS_COLORS.get(cls, '')):<{col_w + 10}}"
    print(header)
    print(f"  {'─' * (15 + col_w * len(all_cls))}")
    for true_cls in all_cls:
        c    = CLASS_COLORS.get(true_cls, "")
        line = f"  {_color(true_cls[:14], c):<24}"
        for pred_cls in all_cls:
            val  = metrics["confusion"][true_cls][pred_cls]
            cell = _color(f"{val:>{col_w}}", _GREEN if (true_cls == pred_cls and val > 0)
                                              else _RED if val > 0 else _DIM)
            line += cell
        print(line)

    # Métriques par classe
    print(f"\n  {'Classe':<14} {'Précision':>10} {'Rappel':>10} {'F1':>10} {'Support':>9} {'Conf. moy.':>11}")
    print(f"  {'─'*68}")
    for cls, m in metrics["per_class"].items():
        c      = CLASS_COLORS.get(cls, "")
        confs  = confidences.get(cls, [])
        avg_c  = sum(confs) / len(confs) if confs else 0.0
        f1_col = _GREEN if m["f1"] >= 0.9 else _YELLOW if m["f1"] >= 0.7 else _RED
        f1_str = f"{m['f1']:>8.2%}"
        print(
            f"  {_color(f'{cls:<14}', c)}"
            f"  {m['precision']:>8.2%}"
            f"  {m['recall']:>8.2%}"
            f"  {_color(f1_str, f1_col)}"
            f"  {m['support']:>8}"
            f"  {avg_c:>9.1%}"
        )

    # Cas incorrects
    wrong = [d for d in details if not d["correct"] and d["obtenu"] != "ERREUR"]
    if wrong:
        print(f"\n{'─'*64}")
        print(f"  {_BOLD}CAS INCORRECTS :{_RESET}")
        for w in wrong:
            print(f"\n  [{w['id']}]  Attendu : {_color(w['attendu'], CLASS_COLORS.get(w['attendu'], ''))}"
                  f"  →  Obtenu : {_color(w['obtenu'], _RED)}  ({w['confiance']:.0%})")
            print(f"    {_DIM}{w['texte'][:100]}{_RESET}")
            if w["note"]:
                print(f"    💡 {w['note']}")

    print(f"\n{'═'*64}\n")

    if save_path:
        rapport = {
            "type":            "Classification (test unitaire)",
            "dataset":         cases_path,
            "total":           total,
            "erreurs":         errors,
            "accuracy":        metrics["accuracy"],
            "f1_macro":        metrics["f1_macro"],
            "f1_weighted":     metrics["f1_weighted"],
            "precision_macro": metrics["precision_macro"],
            "recall_macro":    metrics["recall_macro"],
            "per_class":       metrics["per_class"],
            "confusion":       metrics["confusion"],
            "details":         details,
        }
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        Path(save_path).write_text(
            json.dumps(rapport, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  Rapport sauvegardé → {save_path}\n")

    sys.exit(0 if metrics["f1_macro"] >= 0.80 else 1)


# ══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Évaluation unitaire de la classification ClearBot",
    )
    parser.add_argument(
        "--cases", default="evaluation/datasets/classification_cases.json",
        help="Fichier JSON des cas de référence"
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--save",    metavar="FILE", default=None)
    args = parser.parse_args()

    if not Path(args.cases).exists():
        print(f"Fichier introuvable : {args.cases}")
        sys.exit(1)

    run_eval(args.cases, args.verbose, args.save)


if __name__ == "__main__":
    main()
