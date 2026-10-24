"""
Génération des figures d'évaluation – Maroclear
Couleurs : #e4923a (orange) et palette gris
"""

import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.gridspec as gridspec
from math import pi
import os
from pathlib import Path

# ─── Palette Maroclear ──────────────────────────────────────────────────────
ORANGE      = "#e4923a"
ORANGE_LIGHT= "#f5c98a"
ORANGE_PALE = "#fdf0e0"
GRAY_DARK   = "#3a3a3a"
GRAY_MID    = "#7a7a7a"
GRAY_LIGHT  = "#c8c8c8"
GRAY_BG     = "#f5f5f5"
WHITE       = "#ffffff"
GREEN_OK    = "#4aaa7a"   # pour les bons scores
RED_WARN    = "#d95f5f"   # pour les points faibles

plt.rcParams.update({
    "font.family":       "sans-serif",
    "font.sans-serif":   ["DejaVu Sans", "Arial", "Helvetica"],
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.spines.left":  False,
    "axes.spines.bottom":False,
    "figure.facecolor":  WHITE,
    "axes.facecolor":    WHITE,
    "axes.grid":         False,
    "xtick.bottom":      False,
    "ytick.left":        False,
})

# ─── Données ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
RAPPORTS_DIR = BASE_DIR / "rapports"
OUTPUT_DIR = RAPPORTS_DIR / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with open(RAPPORTS_DIR / "classification_final.json", encoding="utf-8") as f:
    clf = json.load(f)

with open(RAPPORTS_DIR / "rag_info_final.json", encoding="utf-8") as f:
    ri = json.load(f)

with open(RAPPORTS_DIR / "rag_regl_final.json", encoding="utf-8") as f:
    rr = json.load(f)

pc = clf["per_class"]
cm = clf["confusion"]
classes = list(pc.keys())

# ─── Helper ─────────────────────────────────────────────────────────────────
def pct(v):
    return f"{v*100:.1f}%"

def score_color(v):
    if v >= 0.9: return GREEN_OK
    if v >= 0.8: return ORANGE
    return RED_WARN

def save(fig, name):
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=WHITE)
    plt.close(fig)
    print(f"  [OK] {name}")


# ════════════════════════════════════════════════════════════════════════════
# Fig 1 – Métriques globales Classification (scorecard)
# ════════════════════════════════════════════════════════════════════════════
def fig_classification_summary():
    metrics = {
        "Accuracy":   clf["accuracy"],
        "F1 macro":   clf["f1_macro"],
        "Précision\nmacro": clf["precision_macro"],
        "Rappel\nmacro":    clf["recall_macro"],
    }

    fig, axes = plt.subplots(1, 4, figsize=(11, 2.8), facecolor=WHITE)
    fig.suptitle("Classification — métriques globales", fontsize=13,
                 fontweight="bold", color=GRAY_DARK, y=1.02)

    for ax, (label, val) in zip(axes, metrics.items()):
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.axis("off")
        # fond arrondi
        bg = FancyBboxPatch((0.05, 0.08), 0.9, 0.84,
                            boxstyle="round,pad=0.04",
                            linewidth=1.2, edgecolor=GRAY_LIGHT,
                            facecolor=GRAY_BG)
        ax.add_patch(bg)
        # valeur
        ax.text(0.5, 0.55, f"{val*100:.1f}%",
                ha="center", va="center", fontsize=22,
                fontweight="bold", color=ORANGE, transform=ax.transAxes)
        # label
        ax.text(0.5, 0.22, label,
                ha="center", va="center", fontsize=10,
                color=GRAY_MID, transform=ax.transAxes, linespacing=1.4)

    plt.tight_layout(pad=1.2)
    save(fig, "fig1_classification_summary.png")


# ════════════════════════════════════════════════════════════════════════════
# Fig 2 – Barres groupées par classe (P / R / F1)
# ════════════════════════════════════════════════════════════════════════════
def fig_per_class_bars():
    metrics_keys = ["precision", "recall", "f1"]
    labels_fr    = ["Précision", "Rappel", "F1"]
    bar_colors   = [ORANGE, GRAY_MID, GRAY_LIGHT]

    n_classes = len(classes)
    n_metrics = len(metrics_keys)
    x = np.arange(n_classes)
    width = 0.22

    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.suptitle("Classification — performances par classe",
                 fontsize=13, fontweight="bold", color=GRAY_DARK, y=1.01)

    for i, (key, color) in enumerate(zip(metrics_keys, bar_colors)):
        vals = [pc[c][key] for c in classes]
        bars = ax.bar(x + (i - 1) * width, vals, width,
                      color=color, zorder=3, label=labels_fr[i])
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.008,
                    f"{v*100:.0f}%", ha="center", va="bottom",
                    fontsize=8.5, color=GRAY_DARK)

    ax.set_xticks(x)
    ax.set_xticklabels(classes, fontsize=11, color=GRAY_DARK)
    ax.set_ylim(0.6, 1.10)
    ax.set_yticks([0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_yticklabels(["60%","70%","80%","90%","100%"],
                       fontsize=9, color=GRAY_MID)
    ax.yaxis.set_tick_params(left=True)
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_color(GRAY_LIGHT)
    ax.axhline(0.9, color=GRAY_LIGHT, linewidth=0.8, linestyle="--", zorder=1)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.08),
              fontsize=9, frameon=False, ncol=3, handlelength=2.4,
              columnspacing=1.8)
    ax.set_facecolor(WHITE)

    # support annotation
    for i, cls in enumerate(classes):
        ax.text(x[i], 0.615, f"n={pc[cls]['support']}",
                ha="center", fontsize=8, color=GRAY_MID)

    plt.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, "fig2_per_class_bars.png")


# ════════════════════════════════════════════════════════════════════════════
# Fig 3 – Matrice de confusion
# ════════════════════════════════════════════════════════════════════════════
def fig_confusion_matrix():
    n = len(classes)
    matrix = np.array([[cm[actual][pred] for pred in classes] for actual in classes])
    totals = matrix.sum(axis=1, keepdims=True)
    matrix_pct = matrix / totals

    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    fig.suptitle("Classification — matrice de confusion",
                 fontsize=13, fontweight="bold", color=GRAY_DARK)

    # Colormap : gris pour hors-diagonale, orange pour la diagonale
    cmap = plt.cm.Oranges
    im = ax.imshow(matrix_pct, cmap="Greys", vmin=0, vmax=1, aspect="auto")

    # Surcharge diagonale en orange
    for i in range(n):
        for j in range(n):
            alpha = matrix_pct[i, j]
            if i == j:
                color = ORANGE
            else:
                color = GRAY_LIGHT if alpha < 0.01 else RED_WARN
            rect = plt.Rectangle([j-0.5, i-0.5], 1, 1,
                                  facecolor=color,
                                  alpha=max(0.12, alpha) if i != j else alpha * 0.8 + 0.15,
                                  zorder=2)
            ax.add_patch(rect)

            val = matrix[i, j]
            text_color = WHITE if (i == j and alpha > 0.4) else GRAY_DARK
            ax.text(j, i, str(val), ha="center", va="center",
                    fontsize=13, fontweight="bold" if i == j else "normal",
                    color=text_color, zorder=3)

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(classes, fontsize=10, color=GRAY_DARK, rotation=15, ha="right")
    ax.set_yticklabels(classes, fontsize=10, color=GRAY_DARK)
    ax.set_xlabel("Prédit", fontsize=11, color=GRAY_MID, labelpad=8)
    ax.set_ylabel("Réel", fontsize=11, color=GRAY_MID, labelpad=8)
    ax.tick_params(bottom=True, left=True)

    plt.tight_layout()
    save(fig, "fig3_confusion_matrix.png")


# ════════════════════════════════════════════════════════════════════════════
# Fig 4 – Radar RAG informationnel
# ════════════════════════════════════════════════════════════════════════════
def radar_chart(ax, values, labels, color, title):
    N = len(labels)
    angles = [n / float(N) * 2 * pi for n in range(N)]
    angles += angles[:1]
    values_plot = list(values) + [values[0]]

    ax.set_facecolor(WHITE)
    ax.spines["polar"].set_color(GRAY_LIGHT)

    # grille
    for level in [0.6, 0.7, 0.8, 0.9, 1.0]:
        ax.plot(angles, [level]*len(angles), color=GRAY_LIGHT,
                linewidth=0.6, linestyle="--", zorder=1)
    for angle in angles[:-1]:
        ax.plot([angle, angle], [0.5, 1.0], color=GRAY_LIGHT,
                linewidth=0.6, zorder=1)

    # remplissage
    ax.fill(angles, values_plot, alpha=0.18, color=color, zorder=2)
    ax.plot(angles, values_plot, color=color, linewidth=2.5, zorder=3)
    ax.scatter(angles[:-1], values[:N],
               s=55, color=color, zorder=4)

    ax.set_ylim(0.5, 1.05)
    ax.set_yticks([0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_yticklabels(["60%","70%","80%","90%","100%"],
                       fontsize=7.5, color=GRAY_MID)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10, color=GRAY_DARK)
    ax.set_title(title, fontsize=12, fontweight="bold",
                 color=GRAY_DARK, pad=18)


def fig_rag_info_radar():
    scores = ri["scores_moyens"]
    keys   = ["faithfulness","answer_relevancy","keyword_coverage",
              "context_support","factual_correctness"]
    labels = ["Fidélité","Pertinence\nréponse","Couverture\nmots-clés",
              "Support\ncontexte","Exactitude\nfactuelle"]
    vals   = [scores[k] for k in keys]

    fig, ax = plt.subplots(figsize=(6, 6),
                           subplot_kw=dict(polar=True))
    fig.suptitle("RAG informationnel — radar des scores",
                 fontsize=13, fontweight="bold", color=GRAY_DARK, y=1.01)
    radar_chart(ax, vals, labels, ORANGE, "")

    # score global
    sg = scores["score_global"]
    fig.text(0.5, -0.02,
             f"Score global : {sg*100:.1f}%  •  {ri['total']} questions  •  0 erreur",
             ha="center", fontsize=10, color=GRAY_MID)

    plt.tight_layout()
    save(fig, "fig4_rag_info_radar.png")


# ════════════════════════════════════════════════════════════════════════════
# Fig 5 – Radar RAG réglementaire
# ════════════════════════════════════════════════════════════════════════════
def fig_rag_regl_radar():
    scores = rr["scores_moyens"]
    keys   = ["faithfulness","answer_relevancy","keyword_coverage",
              "context_support","factual_correctness","citation_quality"]
    labels = ["Fidélité","Pertinence\nréponse","Couverture\nmots-clés",
              "Support\ncontexte","Exactitude\nfactuelle","Qualité\ncitations"]
    vals   = [scores[k] for k in keys]

    fig, ax = plt.subplots(figsize=(6.5, 6.5),
                           subplot_kw=dict(polar=True))
    fig.suptitle("RAG réglementaire — radar des scores",
                 fontsize=13, fontweight="bold", color=GRAY_DARK, y=1.01)
    radar_chart(ax, vals, labels, ORANGE, "")

    sg = scores["score_global"]
    fig.text(0.5, -0.02,
             f"Score global : {sg*100:.1f}%  •  {rr['total']} questions  •  0 erreur",
             ha="center", fontsize=10, color=GRAY_MID)

    plt.tight_layout()
    save(fig, "fig5_rag_regl_radar.png")


# ════════════════════════════════════════════════════════════════════════════
# Fig 6 – Barres horizontales par catégorie RAG réglementaire
# ════════════════════════════════════════════════════════════════════════════
def fig_rag_regl_categories():
    cats_raw = rr["scores_par_categorie"]
    cats_fr  = {
        "definition":  "Définition",
        "obligations": "Obligations",
        "sanctions":   "Sanctions",
        "conditions":  "Conditions",
        "croisement":  "Croisement"
    }
    items = [(cats_fr.get(k, k), v) for k, v in sorted(cats_raw.items(),
             key=lambda x: x[1], reverse=True)]
    labels, vals = zip(*items)

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.suptitle("RAG réglementaire — scores par catégorie de questions",
                 fontsize=13, fontweight="bold", color=GRAY_DARK, y=1.01)

    y = np.arange(len(labels))
    bar_colors = [score_color(v) for v in vals]

    bars = ax.barh(y, vals, height=0.55, color=bar_colors, zorder=3)
    ax.set_xlim(0, 1.12)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11, color=GRAY_DARK)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0%","25%","50%","75%","100%"],
                       fontsize=9, color=GRAY_MID)
    ax.xaxis.set_tick_params(bottom=True)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color(GRAY_LIGHT)

    # fond rayé léger
    for i, v in enumerate(vals):
        ax.barh(i, 1.0, height=0.55,
                color=GRAY_BG if i%2==0 else WHITE, zorder=1)
        ax.barh(i, v, height=0.55, color=bar_colors[i], zorder=3)
        ax.text(v + 0.015, i, f"{v*100:.1f}%",
                va="center", fontsize=10, fontweight="bold",
                color=bar_colors[i])

    # ligne score global
    sg = rr["scores_moyens"]["score_global"]
    ax.axvline(sg, color=GRAY_MID, linewidth=1.2, linestyle="--", zorder=4)
    moyenne_label = f"Moyenne {sg*100:.1f}%".replace(".", ",")
    ax.text(sg + 0.015, 0.98, moyenne_label,
            transform=ax.get_xaxis_transform(), ha="left", va="top",
            fontsize=8.5, color=GRAY_MID)

    # légende
    patches = [
        mpatches.Patch(color=GREEN_OK,  label="≥ 90%"),
        mpatches.Patch(color=ORANGE,    label="80–90%"),
        mpatches.Patch(color=RED_WARN,  label="< 80%"),
    ]
    ax.legend(handles=patches, loc="upper center", bbox_to_anchor=(0.5, 1.08),
              fontsize=9, frameon=False, ncol=3, handlelength=2.4,
              columnspacing=1.8)

    plt.tight_layout(rect=(0, 0, 1, 0.95))
    save(fig, "fig6_rag_regl_categories.png")


# ════════════════════════════════════════════════════════════════════════════
# Fig 7 – Vue comparée RAG info vs RAG régl (radar superposé)
# ════════════════════════════════════════════════════════════════════════════
def fig_rag_comparison_radar():
    common_keys = ["faithfulness","answer_relevancy","keyword_coverage",
                   "context_support","factual_correctness"]
    labels = ["Fidélité","Pertinence\nréponse","Couverture\nmots-clés",
              "Support\ncontexte","Exactitude\nfactuelle"]
    N = len(labels)
    angles = [n / float(N) * 2 * pi for n in range(N)] + [0]

    info_vals  = [ri["scores_moyens"][k] for k in common_keys] + [ri["scores_moyens"][common_keys[0]]]
    regl_vals  = [rr["scores_moyens"][k] for k in common_keys] + [rr["scores_moyens"][common_keys[0]]]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    fig.suptitle("Comparaison RAG informationnel vs réglementaire",
                 fontsize=13, fontweight="bold", color=GRAY_DARK, y=1.01)
    ax.set_facecolor(WHITE)
    ax.spines["polar"].set_color(GRAY_LIGHT)

    for level in [0.6, 0.7, 0.8, 0.9, 1.0]:
        ax.plot(angles, [level]*len(angles), color=GRAY_LIGHT,
                linewidth=0.6, linestyle="--", zorder=1)
    for angle in angles[:-1]:
        ax.plot([angle, angle], [0.5, 1.0], color=GRAY_LIGHT,
                linewidth=0.6, zorder=1)

    ax.fill(angles, info_vals, alpha=0.15, color=ORANGE, zorder=2)
    ax.plot(angles, info_vals, color=ORANGE, linewidth=2.5, zorder=3, label="RAG informationnel")
    ax.scatter(angles[:-1], info_vals[:-1], s=55, color=ORANGE, zorder=4)

    ax.fill(angles, regl_vals, alpha=0.15, color=GRAY_MID, zorder=2)
    ax.plot(angles, regl_vals, color=GRAY_MID, linewidth=2.5, zorder=3, linestyle="--", label="RAG réglementaire")
    ax.scatter(angles[:-1], regl_vals[:-1], s=55, color=GRAY_MID, zorder=4)

    ax.set_ylim(0.5, 1.05)
    ax.set_yticks([0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_yticklabels(["60%","70%","80%","90%","100%"],
                       fontsize=7.5, color=GRAY_MID)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10, color=GRAY_DARK)

    legend = ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15),
                       fontsize=10, frameon=False)
    for text in legend.get_texts():
        text.set_color(GRAY_DARK)

    plt.tight_layout()
    save(fig, "fig7_rag_comparison_radar.png")


# ════════════════════════════════════════════════════════════════════════════
# Fig 8 – Dashboard synthèse globale (une seule figure récapitulative)
# ════════════════════════════════════════════════════════════════════════════
def fig_global_dashboard():
    fig = plt.figure(figsize=(14, 7.5))
    fig.patch.set_facecolor(WHITE)

    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35,
                           left=0.06, right=0.97, top=0.88, bottom=0.08)

    # ── Titre ──
    fig.suptitle("Tableau de synthèse — Évaluation du système",
                 fontsize=15, fontweight="bold", color=GRAY_DARK)

    # ── 1. Scorecards (row 0, col 0-2 sur toute la largeur) ──
    scorecard_ax = fig.add_subplot(gs[0, :])
    scorecard_ax.axis("off")
    entries = [
        ("Classification", f"{clf['accuracy']*100:.1f}%", f"F1 {clf['f1_macro']*100:.1f}%", f"{clf['total']} tests"),
        ("RAG informationnel", f"{ri['scores_moyens']['score_global']*100:.1f}%", "Score global", f"{ri['total']} questions"),
        ("RAG réglementaire", f"{rr['scores_moyens']['score_global']*100:.1f}%", "Score global", f"{rr['total']} questions"),
    ]
    for i, (title, big, sub, foot) in enumerate(entries):
        x = 0.05 + i * 0.32
        scorecard_ax.add_patch(FancyBboxPatch(
            (x, 0.05), 0.28, 0.88,
            boxstyle="round,pad=0.03",
            linewidth=1.5, edgecolor=ORANGE,
            facecolor=ORANGE_PALE, transform=scorecard_ax.transAxes
        ))
        scorecard_ax.text(x+0.14, 0.73, title, ha="center", va="center",
                          fontsize=10, color=GRAY_MID,
                          transform=scorecard_ax.transAxes)
        scorecard_ax.text(x+0.14, 0.44, big, ha="center", va="center",
                          fontsize=22, fontweight="bold", color=ORANGE,
                          transform=scorecard_ax.transAxes)
        scorecard_ax.text(x+0.14, 0.22, sub, ha="center", va="center",
                          fontsize=9, color=GRAY_MID,
                          transform=scorecard_ax.transAxes)
        scorecard_ax.text(x+0.14, 0.06, foot, ha="center", va="center",
                          fontsize=8, color=GRAY_LIGHT,
                          transform=scorecard_ax.transAxes)

    # ── 2. F1 par classe ──
    ax_bar = fig.add_subplot(gs[1, 0])
    f1_vals = [pc[c]["f1"] for c in classes]
    bar_colors = [ORANGE if v >= 0.9 else ORANGE_LIGHT for v in f1_vals]
    bars = ax_bar.bar(classes, f1_vals, color=bar_colors, width=0.55, zorder=3)
    for bar, v in zip(bars, f1_vals):
        ax_bar.text(bar.get_x()+bar.get_width()/2, v+0.005,
                    f"{v*100:.0f}%", ha="center", fontsize=8.5, color=GRAY_DARK)
    ax_bar.set_ylim(0.7, 1.07)
    ax_bar.set_yticks([0.7, 0.8, 0.9, 1.0])
    ax_bar.set_yticklabels(["70%","80%","90%","100%"], fontsize=7, color=GRAY_MID)
    ax_bar.yaxis.set_tick_params(left=True)
    ax_bar.spines["left"].set_visible(True)
    ax_bar.spines["left"].set_color(GRAY_LIGHT)
    ax_bar.tick_params(axis="x", labelsize=8, colors=GRAY_DARK, bottom=True)
    ax_bar.axhline(0.9, color=GRAY_LIGHT, linewidth=0.8, linestyle="--")
    ax_bar.set_title("F1 par classe", fontsize=10, color=GRAY_DARK, pad=6)

    # ── 3. Radar RAG info (mini) ──
    ax_ri = fig.add_subplot(gs[1, 1], polar=True)
    ri_keys = ["faithfulness","answer_relevancy","keyword_coverage",
               "context_support","factual_correctness"]
    ri_labels = ["Fidélité","Pertinence","Mots-clés","Contexte","Exactitude"]
    ri_vals = [ri["scores_moyens"][k] for k in ri_keys]
    N = len(ri_labels)
    angles = [n/float(N)*2*pi for n in range(N)] + [0]
    ri_plot = ri_vals + [ri_vals[0]]
    ax_ri.set_facecolor(WHITE)
    ax_ri.spines["polar"].set_color(GRAY_LIGHT)
    for lvl in [0.7, 0.85, 1.0]:
        ax_ri.plot(angles, [lvl]*len(angles), color=GRAY_LIGHT, linewidth=0.5)
    ax_ri.fill(angles, ri_plot, alpha=0.18, color=ORANGE)
    ax_ri.plot(angles, ri_plot, color=ORANGE, linewidth=2)
    ax_ri.set_xticks(angles[:-1])
    ax_ri.set_xticklabels(ri_labels, fontsize=7.5, color=GRAY_DARK)
    ax_ri.set_ylim(0.5, 1.05)
    ax_ri.set_yticks([])
    ax_ri.set_title("RAG informationnel", fontsize=10, color=GRAY_DARK, pad=12)

    # ── 4. Radar RAG regl (mini) ──
    ax_rr = fig.add_subplot(gs[1, 2], polar=True)
    rr_keys = ["faithfulness","answer_relevancy","keyword_coverage",
               "context_support","factual_correctness","citation_quality"]
    rr_labels = ["Fidélité","Pertinence","Mots-clés","Contexte","Exactitude","Citations"]
    rr_vals = [rr["scores_moyens"][k] for k in rr_keys]
    N2 = len(rr_labels)
    angles2 = [n/float(N2)*2*pi for n in range(N2)] + [0]
    rr_plot = rr_vals + [rr_vals[0]]
    ax_rr.set_facecolor(WHITE)
    ax_rr.spines["polar"].set_color(GRAY_LIGHT)
    for lvl in [0.7, 0.85, 1.0]:
        ax_rr.plot(angles2, [lvl]*len(angles2), color=GRAY_LIGHT, linewidth=0.5)
    ax_rr.fill(angles2, rr_plot, alpha=0.18, color=GRAY_MID)
    ax_rr.plot(angles2, rr_plot, color=GRAY_MID, linewidth=2)
    ax_rr.set_xticks(angles2[:-1])
    ax_rr.set_xticklabels(rr_labels, fontsize=7.5, color=GRAY_DARK)
    ax_rr.set_ylim(0.5, 1.05)
    ax_rr.set_yticks([])
    ax_rr.set_title("RAG réglementaire", fontsize=10, color=GRAY_DARK, pad=12)

    save(fig, "fig8_global_dashboard.png")


# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Génération des figures…")
    fig_classification_summary()     # fig1
    fig_per_class_bars()             # fig2
    fig_confusion_matrix()           # fig3
    fig_rag_info_radar()             # fig4
    fig_rag_regl_radar()             # fig5
    fig_rag_regl_categories()        # fig6
    fig_rag_comparison_radar()       # fig7
    fig_global_dashboard()           # fig8
    print(f"\nToutes les figures sont dans : {OUTPUT_DIR}")
