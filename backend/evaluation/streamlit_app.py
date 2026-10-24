"""
Dashboard Streamlit pour les rapports d'evaluation ClearBot.

Lancement :
    streamlit run backend/evaluation/streamlit_app.py
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import fill
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd
import streamlit as st

plt.rcParams.update({
    "figure.dpi": 115,
    "savefig.dpi": 115,
    "axes.titlepad": 8,
    "font.size": 7.8,
})


BASE_DIR = Path(__file__).resolve().parent
RAPPORTS_DIR = BASE_DIR / "rapports"

CLASSIFICATION_PATH = RAPPORTS_DIR / "classification_final.json"
RAG_INFO_PATH       = RAPPORTS_DIR / "rag_info_final.json"
RAG_REGL_PATH       = RAPPORTS_DIR / "rag_regl_final.json"

METRIC_LABELS = {
    "accuracy":           "Accuracy",
    "precision":          "Précision",
    "precision_macro":    "Précision macro",
    "recall":             "Rappel",
    "recall_macro":       "Rappel macro",
    "f1":                 "F1",
    "f1_macro":           "F1 macro",
    "faithfulness":       "Fidélité",
    "answer_relevancy":   "Pertinence réponse",
    "keyword_coverage":   "Couverture mots-clés",
    "context_support":    "Support contexte",
    "factual_correctness":"Exactitude factuelle",
    "citation_quality":   "Qualité citations",
    "score_global":       "Score global",
}

METRIC_EXPLANATIONS = {
    "Accuracy": (
        "Part des tickets correctement classés. Simple à lire, mais moins fine "
        "quand les classes sont déséquilibrées."
    ),
    "Précision": (
        "Quand le modèle prédit une classe, indique la proportion de prédictions "
        "qui étaient correctes. Utile pour mesurer les faux positifs."
    ),
    "Rappel": (
        "Pour une classe donnée, indique la proportion de vrais cas retrouvés par "
        "le modèle. Utile pour mesurer les faux négatifs."
    ),
    "F1": (
        "Moyenne harmonique entre précision et rappel. C'est un bon compromis "
        "quand on veut une lecture robuste par classe."
    ),
    "Fidélité": (
        "Vérifie si la réponse est supportée par les documents récupérés. Une "
        "faible fidélité signale un risque d'hallucination."
    ),
    "Pertinence réponse": (
        "Mesure si la réponse traite vraiment la question posée, sans digression "
        "ni omission importante."
    ),
    "Couverture mots-clés": (
        "Mesure déterministe : proportion des concepts attendus présents dans la "
        "réponse ou le contexte selon le protocole d'évaluation."
    ),
    "Support contexte": (
        "Qualité du retrieval : les chunks récupérés contiennent-ils les éléments "
        "nécessaires pour répondre correctement ?"
    ),
    "Exactitude factuelle": (
        "Comparaison avec une réponse de référence pour vérifier la justesse des "
        "faits, définitions, obligations ou citations."
    ),
    "Qualité citations": (
        "Spécifique au RAG réglementaire : vérifie si les sources juridiques sont "
        "citées avec assez de précision."
    ),
    "Score global": (
        "Score agrégé du pipeline. Il donne une vue rapide, mais il doit toujours "
        "être lu avec les sous-métriques."
    ),
}

# ─── Palette Maroclear ───────────────────────────────────────────────────────
ORANGE      = "#e4923a"
ORANGE_LIGHT= "#f2c389"
ORANGE_PALE = "#fff4e8"
GRAY_DARK   = "#343434"
GRAY_MID    = "#888888"
GRAY_LIGHT  = "#d8d8d8"
GRAY_SOFT   = "#f5f5f5"
GRAY_FAINT  = "#fbfbfb"
MAROCLEAR_CMAP = LinearSegmentedColormap.from_list(
    "maroclear_orange_gray",
    ["#ffffff", "#fff4e8", "#f2c389", "#e4923a"],
)

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ClearBot — Évaluation",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS global ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --orange: #e4923a;
    --orange-soft: #f2c389;
    --orange-pale: #fff4e8;
    --ink: #343434;
    --muted: #707070;
    --muted-2: #888888;
    --line: #e2e2e2;
    --soft: #f7f7f7;
    --white: #ffffff;
}

/* ── Layout ── */
.stApp { background: linear-gradient(180deg, #ffffff 0%, #fbfbfb 42%, #f7f7f7 100%); }
.main .block-container { padding-top: 0.85rem; max-width: 1180px; padding-bottom: 2rem; }
div[data-testid="stVerticalBlock"] { gap: 0.8rem; }

/* ── Headings ── */
h1, h2, h3 { color: var(--ink) !important; font-weight: 700 !important; letter-spacing: 0; }
h1 { font-size: 1.7rem !important; margin-bottom: 0.1rem !important; }
h2 {
    font-size: 1.12rem !important;
    border-top: 1px solid var(--line);
    padding-top: 0.9rem;
    margin-top: 1.15rem !important;
}
h3 { font-size: 1rem !important; }

/* ── Page titles ── */
.page-title {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 0.25rem 0 0.35rem;
    padding-bottom: 0.45rem;
    border-bottom: 1px solid var(--line);
}
.page-title-icon {
    width: 38px;
    height: 38px;
    border-radius: 8px;
    display: grid;
    place-items: center;
    background: linear-gradient(135deg, var(--orange), var(--orange-soft));
    color: #ffffff;
    flex: 0 0 auto;
    box-shadow: 0 8px 18px rgba(228,146,58,0.18);
}
.page-title-text {
    color: var(--ink);
    font-size: 1.55rem;
    line-height: 1.15;
    font-weight: 850;
}
.page-title-text span {
    color: var(--orange);
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] .sidebar-logo {
    padding: 1rem 0.95rem 0.75rem;
    border-bottom: 1px solid var(--line);
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.65rem;
}
[data-testid="stSidebar"] .sidebar-mark {
    width: 34px;
    height: 34px;
    border: 1px solid var(--line);
    border-radius: 8px;
    display: grid;
    place-items: center;
    background: var(--orange-pale);
    flex: 0 0 auto;
}
[data-testid="stSidebar"] .sidebar-logo .brand {
    font-size: 1.05rem;
    font-weight: 800;
    color: var(--orange);
    letter-spacing: 0;
}
[data-testid="stSidebar"] .sidebar-logo .sub {
    font-size: 0.78rem;
    color: var(--muted);
    margin-top: 1px;
}
/* Nav pills */
[data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 2px !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    display: flex !important;
    align-items: center;
    gap: 0.5rem;
    padding: 0.42rem 0.75rem !important;
    border-radius: 6px !important;
    font-size: 0.9rem !important;
    color: var(--muted) !important;
    transition: background 0.15s;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label p { font-size: 0.88rem !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: var(--orange-pale) !important;
    color: var(--orange) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] {
    background: var(--orange-pale) !important;
    color: var(--orange) !important;
    font-weight: 700 !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] [data-checked="true"]::before {
    content: "";
    display: inline-block;
    width: 3px;
    height: 1em;
    background: var(--orange);
    border-radius: 2px;
    margin-right: 0.3rem;
}

/* ── Hero banner ── */
.hero {
    background:
        linear-gradient(135deg, rgba(228,146,58,0.10) 0%, rgba(255,255,255,0) 36%),
        linear-gradient(180deg, #ffffff 0%, #fbfbfb 100%);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 1rem 1.1rem;
    margin-bottom: 1.2rem;
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 1rem;
    align-items: center;
    box-shadow: 0 8px 24px rgba(52,52,52,0.06);
}
.hero-kicker { color: var(--orange); font-size: 0.72rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.3rem; }
.hero-title   { color: var(--ink);    font-size: 1.55rem; font-weight: 800; line-height: 1.15; margin-bottom: 0.35rem; }
.hero-subtitle{ color: var(--muted);  font-size: 0.92rem; line-height: 1.5; }
.hero-mark {
    width: 78px;
    height: 78px;
    border: 1px solid var(--line);
    border-radius: 8px;
    display: grid;
    place-items: center;
    background: #fff;
}

/* ── Metric cards ── */
.metric-card {
    border: 1px solid var(--line);
    background: #fff;
    border-radius: 8px;
    padding: 0.75rem 0.85rem;
    box-shadow: 0 6px 18px rgba(52,52,52,0.05);
    min-height: 118px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: relative;
    overflow: hidden;
}
.metric-card:before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 4px;
    background: linear-gradient(180deg, var(--orange), var(--orange-soft));
}
.metric-card .mc-top { display: flex; justify-content: space-between; gap: 0.5rem; align-items: flex-start; }
.metric-icon {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: var(--orange-pale);
    display: grid;
    place-items: center;
    color: var(--orange);
    flex: 0 0 auto;
}
.metric-card .mc-label   { color: var(--muted); font-size: 0.76rem; margin-bottom: 0.3rem; line-height: 1.25; }
.metric-card .mc-value   { color: var(--orange); font-size: 1.55rem; font-weight: 800; line-height: 1.1; }
.metric-card .mc-caption { color: var(--muted); font-size: 0.78rem; margin-top: 0.3rem; }

/* ── Section note ── */
.section-note { color: var(--muted); font-size: 0.9rem; line-height: 1.55; margin-bottom: 0.9rem; }

/* ── Chart legends ── */
.chart-legend {
    display: flex;
    justify-content: center;
    gap: 1rem;
    flex-wrap: wrap;
    color: var(--muted);
    font-size: 0.76rem;
    margin: 0.45rem 0 0.1rem;
}
.chart-legend span {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}
.chart-dot {
    width: 9px;
    height: 9px;
    border-radius: 2px;
    display: inline-block;
}
.chart-row-spacer { height: 1.45rem; }

/* ── Analysis cards ── */
.analysis-card {
    border: 1px solid var(--line);
    border-left: 4px solid var(--orange);
    border-radius: 6px;
    background: #fff;
    padding: 0.75rem 0.9rem;
    font-size: 0.87rem;
    line-height: 1.5;
    color: var(--muted);
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    min-height: 124px;
}
.analysis-card .ac-head  { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.2rem; }
.analysis-card .ac-idx   { color: var(--orange); font-weight: 800; font-size: 0.75rem; }
.analysis-card .ac-title { color: var(--ink); font-weight: 700; margin-bottom: 0.15rem; font-size: 0.9rem; }
.analysis-icon { color: var(--orange); opacity: 0.9; }

/* ── Sidebar stats ── */
.sidebar-stat {
    font-size: 0.8rem;
    color: var(--muted);
    padding: 0.28rem 0.75rem;
    border-left: 3px solid transparent;
}
.sidebar-stat strong { color: var(--ink); font-weight: 700; }

/* ── Data surfaces ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--line);
    border-radius: 8px;
    overflow: hidden;
}
[data-testid="stExpander"] {
    border: 1px solid var(--line) !important;
    border-radius: 8px !important;
}

@media (max-width: 760px) {
    .hero { grid-template-columns: 1fr; }
    .hero-mark { display: none; }
    .metric-card { min-height: 104px; }
}
</style>
""", unsafe_allow_html=True)


# ─── Data loading ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ─── Helpers ─────────────────────────────────────────────────────────────────
def pct(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{float(value) * 100:.{digits}f}%"


def score_label(value: float | int | None) -> str:
    if value is None:
        return "—"
    v = float(value)
    if v >= 0.90: return "Excellent"
    if v >= 0.80: return "Bon"
    if v >= 0.70: return "À surveiller"
    return "Prioritaire"


def chart_color(value: float | int | None) -> str:
    if value is None: return GRAY_LIGHT
    v = float(value)
    if v >= 0.90: return ORANGE
    if v >= 0.80: return ORANGE_LIGHT
    return GRAY_MID


def wrap_labels(labels: list[str] | tuple[str, ...], width: int = 18) -> list[str]:
    return [fill(str(label), width=width, break_long_words=False) for label in labels]


def section_note(text: str) -> None:
    st.markdown(f'<div class="section-note">{text}</div>', unsafe_allow_html=True)


def page_title(title: str, accent: str | None = None, icon: str = "chart") -> None:
    accent = accent or title.split(" ")[0]
    if accent in title:
        html_title = title.replace(accent, f"<span>{accent}</span>", 1)
    else:
        html_title = f"<span>{accent}</span> {title}"
    st.markdown(f"""
    <div class="page-title">
        <div class="page-title-icon">{svg_icon(icon, 21)}</div>
        <div class="page-title-text">{html_title}</div>
    </div>""", unsafe_allow_html=True)


def chart_legend(items: list[tuple[str, str]]) -> None:
    spans = "".join(
        f'<span><i class="chart-dot" style="background:{color};"></i>{label}</span>'
        for label, color in items
    )
    st.markdown(f'<div class="chart-legend">{spans}</div>', unsafe_allow_html=True)


def svg_icon(name: str, size: int = 22) -> str:
    icons = {
        "pulse": (
            '<polyline points="3 12 7 12 9.5 5 14.5 19 17 12 21 12"></polyline>'
        ),
        "target": (
            '<circle cx="12" cy="12" r="8"></circle>'
            '<circle cx="12" cy="12" r="3"></circle>'
            '<line x1="12" y1="2" x2="12" y2="5"></line>'
            '<line x1="12" y1="19" x2="12" y2="22"></line>'
        ),
        "scale": (
            '<path d="M12 3v18"></path>'
            '<path d="M6 7h12"></path>'
            '<path d="M7 7l-4 7h8l-4-7z"></path>'
            '<path d="M17 7l-4 7h8l-4-7z"></path>'
        ),
        "search": (
            '<circle cx="10.5" cy="10.5" r="6.5"></circle>'
            '<path d="M16 16l5 5"></path>'
        ),
        "shield": (
            '<path d="M12 3l7 3v5c0 4.4-2.8 8.4-7 10-4.2-1.6-7-5.6-7-10V6l7-3z"></path>'
            '<path d="M9 12l2 2 4-5"></path>'
        ),
        "spark": (
            '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z"></path>'
            '<path d="M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16z"></path>'
        ),
        "chart": (
            '<path d="M4 19V5"></path>'
            '<path d="M4 19h16"></path>'
            '<rect x="7" y="11" width="3" height="5"></rect>'
            '<rect x="12" y="7" width="3" height="9"></rect>'
            '<rect x="17" y="9" width="3" height="7"></rect>'
        ),
    }
    body = icons.get(name, icons["chart"])
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        f'<g stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round">{body}</g></svg>'
    )


def hero(title: str, subtitle: str, kicker: str = "Maroclear · ClearBot") -> None:
    st.markdown(f"""
    <div class="hero">
        <div>
            <div class="hero-kicker">{kicker}</div>
            <div class="hero-title">{title}</div>
            <div class="hero-subtitle">{subtitle}</div>
        </div>
        <div class="hero-mark">{svg_icon("spark", 42)}</div>
    </div>""", unsafe_allow_html=True)


def metric_card(label: str, value: str, caption: str = "", icon: str = "chart") -> None:
    st.markdown(f"""
    <div class="metric-card">
        <div class="mc-top">
            <div class="mc-label">{label}</div>
            <div class="metric-icon">{svg_icon(icon, 17)}</div>
        </div>
        <div class="mc-value">{value}</div>
        <div class="mc-caption">{caption}</div>
    </div>""", unsafe_allow_html=True)


def analysis_card(idx: int, title: str, body: str) -> None:
    st.markdown(f"""
    <div class="analysis-card">
        <div class="ac-head">
            <div class="ac-idx">#{idx:02d}</div>
            <div class="analysis-icon">{svg_icon("target", 16)}</div>
        </div>
        <div class="ac-title">{title}</div>
        {body}
    </div>""", unsafe_allow_html=True)


# ─── Matplotlib helpers ───────────────────────────────────────────────────────
def _clean_ax(ax):
    for spine in ["top", "right", "left"]:
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRAY_LIGHT)
    ax.tick_params(axis="y", length=0)


def _render(fig, col_ratio: list | None = None) -> None:
    """Render a matplotlib figure, optionally centred in a column layout."""
    fig.patch.set_facecolor("white")
    fig.tight_layout(pad=0.3)
    if col_ratio:
        cols = st.columns(col_ratio)
        with cols[len(col_ratio) // 2]:
            st.pyplot(fig, use_container_width=False)
    else:
        c1, c2, c3 = st.columns([1, 12, 1])
        with c2:
            st.pyplot(fig, use_container_width=False)
    plt.close(fig)


# ─── Chart functions ──────────────────────────────────────────────────────────
def render_score_bar_chart(title: str, scores: dict[str, float],
                            exclude: set[str] | None = None) -> None:
    exclude = exclude or set()
    items = [(METRIC_LABELS.get(k, k), v) for k, v in scores.items() if k not in exclude]
    if not items:
        return
    labels, values = zip(*items)
    colors = [chart_color(v) for v in values]
    n = len(labels)

    fig, ax = plt.subplots(figsize=(3.65, max(1.35, n * 0.28)))
    y = np.arange(n)
    ax.barh(y, values, color=colors, height=0.42)
    ax.set_yticks(y)
    ax.set_yticklabels(wrap_labels(labels, 17), fontsize=6.8, color=GRAY_DARK)
    ax.set_xlim(0, 1.13)
    ax.set_xticks([0, 0.5, 1.0])
    ax.set_xticklabels(["0%", "50%", "100%"], color=GRAY_MID, fontsize=6.8)
    ax.axvline(0.90, color=GRAY_LIGHT, linestyle="--", linewidth=0.9)
    ax.set_title(title, fontsize=8.2, color=GRAY_DARK, weight="bold", pad=4)
    ax.invert_yaxis()
    for i, v in enumerate(values):
        ax.text(min(v + 0.016, 1.08), i, pct(v), va="center", color=colors[i],
                weight="bold", fontsize=6.7)
    _clean_ax(ax)
    _render(fig)


def render_classification_bars(clf: dict[str, Any]) -> None:
    df = classification_per_class_df(clf)
    x = np.arange(len(df))
    width = 0.25
    series = [
        ("Précision", ORANGE,       df["Precision"].to_numpy()),
        ("Rappel",    GRAY_MID,     df["Rappel"].to_numpy()),
        ("F1",        GRAY_LIGHT,   df["F1"].to_numpy()),
    ]
    chart_legend([("Précision", ORANGE), ("Rappel", GRAY_MID), ("F1", GRAY_LIGHT)])
    fig, ax = plt.subplots(figsize=(3.75, 2.15))
    for idx, (label, color, vals) in enumerate(series):
        ax.bar(x + (idx - 1) * width, vals, width=width, label=label, color=color)
    ax.set_xticks(x)
    ax.set_xticklabels(wrap_labels(df["Classe"].tolist(), 10), color=GRAY_DARK, fontsize=6.6)
    ax.set_ylim(0.6, 1.12)
    ax.set_yticks([0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_yticklabels(["60%", "70%", "80%", "90%", "100%"], color=GRAY_MID, fontsize=6.6)
    ax.axhline(0.9, color=GRAY_LIGHT, linestyle="--", linewidth=0.9)
    ax.set_title("Précision / Rappel / F1 par classe", fontsize=8.2, color=GRAY_DARK, weight="bold", pad=4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRAY_LIGHT)
    ax.spines["bottom"].set_color(GRAY_LIGHT)
    _render(fig)


def render_confusion_heatmap(clf: dict[str, Any]) -> None:
    classes = list(clf["per_class"].keys())
    matrix = np.array([[clf["confusion"][a][p] for p in classes] for a in classes])
    row_totals = matrix.sum(axis=1, keepdims=True)
    matrix_pct = np.divide(matrix, row_totals,
                           out=np.zeros_like(matrix, dtype=float), where=row_totals != 0)
    fig, ax = plt.subplots(figsize=(3.35, 2.55))
    ax.imshow(matrix_pct, cmap=MAROCLEAR_CMAP, vmin=0, vmax=1)
    ax.set_xticks(np.arange(len(classes)))
    ax.set_yticks(np.arange(len(classes)))
    ax.set_xticklabels(wrap_labels(classes, 10), rotation=0, ha="center", color=GRAY_DARK, fontsize=6.4)
    ax.set_yticklabels(wrap_labels(classes, 10), color=GRAY_DARK, fontsize=6.4)
    ax.set_xlabel("Prédit", color=GRAY_MID, fontsize=6.8)
    ax.set_ylabel("Réel",   color=GRAY_MID, fontsize=6.8)
    ax.set_title("Matrice de confusion", fontsize=8.2, color=GRAY_DARK, weight="bold", pad=4)
    for i in range(len(classes)):
        for j in range(len(classes)):
            v = matrix[i, j]
            c = "white" if matrix_pct[i, j] > 0.55 else GRAY_DARK
            ax.text(j, i, str(v), ha="center", va="center", color=c,
                    weight="bold", fontsize=7.2)
    _render(fig)


def render_global_scores(clf: dict[str, Any], ri: dict[str, Any], rr: dict[str, Any]) -> None:
    labels = ["Accuracy", "F1 macro", "RAG info", "RAG régl."]
    values = [
        clf["accuracy"], clf["f1_macro"],
        ri["scores_moyens"]["score_global"],
        rr["scores_moyens"]["score_global"],
    ]
    colors = [chart_color(v) for v in values]
    fig, ax = plt.subplots(figsize=(3.45, 1.85))
    bars = ax.bar(labels, values, color=colors, width=0.5)
    ax.set_ylim(0, 1.14)
    ax.set_yticks([0, 0.5, 0.9, 1.0])
    ax.set_yticklabels(["0%", "50%", "90%", "100%"], color=GRAY_MID, fontsize=6.6)
    ax.axhline(0.9, color=GRAY_LIGHT, linestyle="--", linewidth=0.9)
    ax.set_title("Vue d'ensemble", fontsize=8.2, color=GRAY_DARK, weight="bold", pad=4)
    ax.tick_params(axis="x", colors=GRAY_DARK, labelsize=6.8)
    for bar, v, c in zip(bars, values, colors):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.025,
                pct(v), ha="center", color=c, weight="bold", fontsize=6.8)
    _clean_ax(ax)
    _render(fig, col_ratio=[1, 3, 1])


def render_rag_comparison(ri: dict[str, Any], rr: dict[str, Any]) -> None:
    keys = ["faithfulness", "answer_relevancy", "keyword_coverage",
            "context_support", "factual_correctness"]
    labels = [METRIC_LABELS.get(k, k) for k in keys]
    info_vals = [ri["scores_moyens"][k] for k in keys]
    regl_vals = [rr["scores_moyens"][k] for k in keys]

    chart_legend([("Informationnel", ORANGE), ("Réglementaire", GRAY_MID)])
    fig, ax = plt.subplots(figsize=(3.85, 2.45))
    y = np.arange(len(labels))
    h = 0.32
    ax.barh(y - h / 2, info_vals,  height=h, color=ORANGE,    label="Informationnel")
    ax.barh(y + h / 2, regl_vals,  height=h, color=GRAY_MID,  label="Réglementaire")
    ax.set_yticks(y)
    ax.set_yticklabels(wrap_labels(labels, 17), color=GRAY_DARK, fontsize=6.5)
    ax.set_xlim(0, 1.16)
    ax.set_xticks([0, 0.5, 1.0])
    ax.set_xticklabels(["0%", "50%", "100%"], color=GRAY_MID, fontsize=6.6)
    ax.axvline(0.90, color=GRAY_LIGHT, linestyle="--", linewidth=0.9)
    ax.invert_yaxis()
    ax.set_title("RAG informationnel vs réglementaire", fontsize=8.2, color=GRAY_DARK, weight="bold", pad=4)
    for i, v in enumerate(info_vals):
        ax.text(min(v + 0.015, 1.02), i - h / 2, pct(v), va="center",
                color=ORANGE, weight="bold", fontsize=6.4)
    for i, v in enumerate(regl_vals):
        ax.text(min(v + 0.015, 1.02), i + h / 2, pct(v), va="center",
                color=GRAY_DARK, weight="bold", fontsize=6.4)
    _clean_ax(ax)
    _render(fig)


def render_worst_cases(report: dict[str, Any], title: str, count: int = 8) -> None:
    rows = [(item.get("id", "—"), item.get("score_global"))
            for item in report.get("details", [])
            if item.get("score_global") is not None]
    if not rows:
        return
    rows = sorted(rows, key=lambda r: r[1])[:count]
    labels, values = zip(*rows)
    colors = [chart_color(v) for v in values]

    fig, ax = plt.subplots(figsize=(4.0, 1.9))
    x = np.arange(len(labels))
    ax.bar(x, values, color=colors, width=0.55)
    ax.set_xticks(x)
    ax.set_xticklabels(wrap_labels(labels, 8))
    ax.set_ylim(0, 1.08)
    ax.set_yticks([0, 0.5, 1.0])
    ax.set_yticklabels(["0%", "50%", "100%"], color=GRAY_MID, fontsize=6.6)
    ax.set_title(title, fontsize=8.2, color=GRAY_DARK, weight="bold", pad=4)
    ax.tick_params(axis="x", colors=GRAY_DARK, labelsize=6.2)
    for i, v in enumerate(values):
        ax.text(i, v + 0.025, pct(v), ha="center", color=colors[i],
                weight="bold", fontsize=6.5)
    _clean_ax(ax)
    _render(fig)


# ─── DataFrames ──────────────────────────────────────────────────────────────
def classification_per_class_df(clf: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for cls, m in clf["per_class"].items():
        rows.append({
            "Classe":    cls,
            "Precision": m["precision"],
            "Rappel":    m["recall"],
            "F1":        m["f1"],
            "Support":   m["support"],
            "TP":        m.get("tp", 0),
            "FP":        m.get("fp", 0),
            "FN":        m.get("fn", 0),
        })
    return pd.DataFrame(rows)


def classification_details_df(clf: dict[str, Any]) -> pd.DataFrame:
    rows = [{
        "ID":        item.get("id"),
        "Texte":     item.get("texte"),
        "Attendu":   item.get("attendu"),
        "Obtenu":    item.get("obtenu"),
        "Confiance": item.get("confiance"),
        "Correct":   item.get("correct"),
        "Note":      item.get("note", ""),
    } for item in clf.get("details", [])]
    return pd.DataFrame(rows)


def scores_dataframe(scores: dict[str, float]) -> pd.DataFrame:
    rows = [{
        "Métrique": METRIC_LABELS.get(k, k),
        "Score":    pct(v),
        "Lecture":  score_label(v),
        "Valeur":   v,
    } for k, v in scores.items()]
    return pd.DataFrame(rows)


def rag_details_df(report: dict[str, Any], show_chunks: bool = True) -> pd.DataFrame:
    metric_keys = ["faithfulness", "answer_relevancy", "keyword_coverage",
                   "context_support", "factual_correctness", "citation_quality", "score_global"]
    rows = []
    for item in report.get("details", []):
        row = {
            "ID":           item.get("id"),
            "Catégorie":    item.get("categorie", "—"),
            "Question":     item.get("question"),
            "Score global": item.get("score_global"),
            "Sources":      ", ".join(item.get("sources", [])[:4]),
        }
        if show_chunks:
            row["Nb chunks"] = item.get("n_chunks_retrieved")
        for key in metric_keys:
            if key in item:
                row[METRIC_LABELS.get(key, key)] = item[key]
        rows.append(row)
    return pd.DataFrame(rows)


def recommendation_lines(clf, ri, rr) -> list[tuple[str, str]]:
    lines = []
    per_class = classification_per_class_df(clf)
    w = per_class.sort_values("F1").iloc[0]
    lines.append((
        f"Classe fragile : {w['Classe']}",
        f"F1 de {pct(w['F1'])} — c'est la classe la plus difficile à prédire."
    ))
    ri_weak = min(((k, v) for k, v in ri["scores_moyens"].items() if k != "score_global"),
                  key=lambda x: x[1])
    lines.append((
        f"RAG info · {METRIC_LABELS.get(ri_weak[0], ri_weak[0])}",
        f"Score de {pct(ri_weak[1])} — axe prioritaire à renforcer."
    ))
    rr_weak = min(((k, v) for k, v in rr["scores_moyens"].items() if k != "score_global"),
                  key=lambda x: x[1])
    lines.append((
        f"RAG régl · {METRIC_LABELS.get(rr_weak[0], rr_weak[0])}",
        f"Score de {pct(rr_weak[1])} — axe le plus sensible."
    ))
    if "scores_par_categorie" in rr:
        cat, val = min(rr["scores_par_categorie"].items(), key=lambda x: x[1])
        lines.append((
            f"Catégorie basse : {cat}",
            f"{pct(val)} — utile pour prioriser le dataset de régression."
        ))
    return lines


# ─── Sidebar ─────────────────────────────────────────────────────────────────
NAV_ITEMS = {
    "Synthèse":            "Synthese",
    "Classification":      "Classification",
    "RAG informationnel":  "RAG informationnel",
    "RAG réglementaire":   "RAG reglementaire",
    "Méthodologie":        "Methodologie",
}

def build_sidebar(clf, ri, rr) -> str:
    st.sidebar.markdown(f"""
    <div class="sidebar-logo">
        <div class="sidebar-mark">{svg_icon("shield", 20)}</div>
        <div>
            <div class="brand">ClearBot</div>
            <div class="sub">Rapport d'évaluation</div>
        </div>
    </div>""", unsafe_allow_html=True)

    choice = st.sidebar.radio("", list(NAV_ITEMS.keys()), label_visibility="collapsed")

    st.sidebar.divider()
    st.sidebar.markdown(
        f'<div class="sidebar-stat"><strong>Classification</strong> · {clf.get("total","—")} tests</div>'
        f'<div class="sidebar-stat"><strong>RAG info</strong> · {ri.get("total","—")} questions</div>'
        f'<div class="sidebar-stat"><strong>RAG régl.</strong> · {rr.get("total","—")} questions</div>',
        unsafe_allow_html=True
    )
    return NAV_ITEMS[choice]


# ─── Header (Synthèse uniquement) ────────────────────────────────────────────
def render_header(clf, ri, rr) -> None:
    hero(
        "Évaluation ClearBot",
        "Performances du classificateur, du RAG informationnel et du RAG réglementaire  "
        "· Performance Review",
    )
    cols = st.columns(4)
    with cols[0]:
        metric_card("Accuracy classification", pct(clf["accuracy"]), f"{clf['total']} tests", "target")
    with cols[1]:
        metric_card("F1 macro", pct(clf["f1_macro"]), "Équilibre précision / rappel", "scale")
    with cols[2]:
        metric_card("Score RAG informationnel", pct(ri["scores_moyens"]["score_global"]),
                    f"{ri['total']} questions", "search")
    with cols[3]:
        metric_card("Score RAG réglementaire", pct(rr["scores_moyens"]["score_global"]),
                    f"{rr['total']} questions", "shield")


# ─── Pages ───────────────────────────────────────────────────────────────────
def page_synthesis(clf, ri, rr) -> None:
    render_header(clf, ri, rr)
    page_title("Synthèse executive", "Synthèse", "spark")
    section_note(
        "Lecture rapide des performances globales, des forces et des points d'attention."
    )

    render_global_scores(clf, ri, rr)

    st.subheader("Points d'attention")
    cols = st.columns(4)
    for idx, (title, body) in enumerate(recommendation_lines(clf, ri, rr), start=1):
        with cols[idx - 1]:
            analysis_card(idx, title, body)

    st.markdown('<div class="chart-row-spacer"></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        render_score_bar_chart(
            "Métriques classification",
            {"accuracy": clf["accuracy"],
             "precision_macro": clf["precision_macro"],
             "recall_macro": clf["recall_macro"],
             "f1_macro": clf["f1_macro"]},
        )
    with c2:
        render_rag_comparison(ri, rr)


def page_classification(clf) -> None:
    page_title("Classification des tickets", "Classification", "target")
    section_note(
        "Capacité du système à orienter chaque message vers la bonne classe métier : "
        "Demande, Incident, Réclamation ou Ambigu."
    )
    c1, c2 = st.columns(2)
    with c1:
        render_classification_bars(clf)
    with c2:
        render_confusion_heatmap(clf)

    st.subheader("Performance par classe")
    df = classification_per_class_df(clf)
    st.dataframe(
        df.style.format({"Precision": "{:.1%}", "Rappel": "{:.1%}", "F1": "{:.1%}"}),
        use_container_width=True, hide_index=True,
    )

    st.subheader("Cas de test")
    details = classification_details_df(clf)
    only_errors = st.checkbox("Erreurs uniquement", value=False)
    shown = details
    if only_errors and "Correct" in details.columns:
        shown = details[details["Correct"] == False]  # noqa: E712
    st.dataframe(shown, use_container_width=True, hide_index=True)

    with st.expander("Comment lire ces métriques ?"):
        st.markdown("""
        - **Accuracy** : part totale des classifications correctes.
        - **Précision** : évite de sur-prédire une classe quand elle n'est pas la bonne.
        - **Rappel** : capacité à retrouver tous les cas d'une classe.
        - **F1** : compromis entre précision et rappel, souvent le meilleur indicateur par classe.
        - **Matrice de confusion** : montre les confusions exactes entre classes.
        """)


def page_rag_info(ri) -> None:
    page_title("RAG informationnel", "RAG", "search")
    section_note(
        "Répond aux questions générales et procédurales sur Maroclear. "
        "L'évaluation combine jugement LLM et mesures déterministes."
    )
    c1, c2 = st.columns(2)
    with c1:
        render_score_bar_chart(
            "Métriques",
            ri["scores_moyens"],
            exclude={"score_global"},
        )
    with c2:
        st.subheader("Scores détaillés")
        df = scores_dataframe(ri["scores_moyens"])
        st.dataframe(df[["Métrique", "Score", "Lecture"]], use_container_width=True, hide_index=True)

    render_worst_cases(ri, "Questions avec les scores les plus bas")
    render_rag_details(ri, "RAG informationnel", show_chunks=False)


def page_rag_regl(rr) -> None:
    page_title("RAG réglementaire", "RAG", "shield")
    section_note(
        "Évaluation sur des questions juridiques. La qualité des citations est ajoutée "
        "aux métriques communes pour contrôler la précision des références légales."
    )
    c1, c2 = st.columns(2)
    with c1:
        render_score_bar_chart(
            "Métriques",
            rr["scores_moyens"],
            exclude={"score_global"},
        )
    with c2:
        render_score_bar_chart(
            "Scores par catégorie",
            rr.get("scores_par_categorie", {}),
        )

    st.subheader("Scores détaillés")
    df = scores_dataframe(rr["scores_moyens"])
    st.dataframe(df[["Métrique", "Score", "Lecture"]], use_container_width=True, hide_index=True)

    if "scores_par_categorie" in rr:
        st.subheader("Catégories juridiques")
        cat_df = pd.DataFrame([
            {"Catégorie": k, "Score": v, "Lecture": score_label(v)}
            for k, v in rr["scores_par_categorie"].items()
        ]).sort_values("Score", ascending=False)
        st.dataframe(cat_df.style.format({"Score": "{:.1%}"}),
                     use_container_width=True, hide_index=True)

    render_worst_cases(rr, "Questions avec les scores les plus bas")
    render_rag_details(rr, "RAG réglementaire")


def render_rag_details(report: dict[str, Any], title: str, show_chunks: bool = True) -> None:
    st.subheader("Détail des questions")
    df = rag_details_df(report, show_chunks=show_chunks)
    if df.empty:
        st.warning("Aucun détail disponible dans le rapport.")
        return

    categories = sorted(df["Catégorie"].dropna().unique().tolist())
    c1, c2 = st.columns([2, 1])
    with c1:
        selected = st.multiselect(
            "Filtrer par catégorie", categories, default=categories,
            key=f"cat_{title}",
        )
    with c2:
        min_score = st.slider(
            "Score minimum", 0.0, 1.0, 0.0, 0.05,
            key=f"score_{title}",
        )

    shown = df[df["Catégorie"].isin(selected)]
    shown = shown[shown["Score global"].fillna(0) >= min_score]
    numeric_cols = [col for col in shown.columns if shown[col].dtype.kind in "if"]
    st.dataframe(
        shown.style.format({col: "{:.1%}" for col in numeric_cols if col != "Nb chunks"}),
        use_container_width=True, hide_index=True,
    )

    st.subheader("Inspection qualitative")
    sorted_details = sorted(report.get("details", []),
                            key=lambda x: x.get("score_global", 0))
    count = st.number_input(
        "Nombre de cas à afficher",
        min_value=1, max_value=max(1, len(sorted_details)),
        value=min(5, max(1, len(sorted_details))),
        key=f"count_{title}",
    )
    for item in sorted_details[:int(count)]:
        with st.expander(
            f"{item.get('id','—')}  ·  {item.get('categorie','—')}  ·  {pct(item.get('score_global'))}"
        ):
            st.markdown(f"**Question** : {item.get('question','—')}")
            st.markdown(f"**Réponse générée** : {item.get('answer','—')}")
            st.markdown(f"**Référence** : {item.get('reponse_reference','—')}")
            if item.get("sources"):
                st.markdown("**Sources**"); st.write(item["sources"])
            if item.get("justifications"):
                st.markdown("**Justifications**"); st.json(item["justifications"])


def page_methodology() -> None:
    page_title("Méthodologie & Définitions", "Méthodologie", "scale")
    section_note(
        "Cette page explique les métriques pour faciliter la lecture du rapport "
        "par une équipe technique, métier ou juridique."
    )
    st.subheader("Définitions")
    for name, explanation in METRIC_EXPLANATIONS.items():
        with st.expander(name):
            st.write(explanation)

    st.subheader("Grille de lecture")
    st.dataframe(
        pd.DataFrame([
            {"Intervalle": "≥ 90%", "Interprétation": "Excellent",      "Action": "Maintenir et surveiller"},
            {"Intervalle": "80–90%","Interprétation": "Bon",             "Action": "Optimisations ciblées"},
            {"Intervalle": "70–80%","Interprétation": "À surveiller",    "Action": "Analyser les erreurs"},
            {"Intervalle": "< 70%", "Interprétation": "Prioritaire",     "Action": "Revoir retrieval, prompt ou dataset"},
        ]),
        use_container_width=True, hide_index=True,
    )
    st.subheader("Limites de l'évaluation")
    st.markdown("""
    - Les scores LLM-as-judge dépendent du modèle juge et du prompt d'évaluation.
    - Un score global élevé ne remplace pas l'analyse des cas faibles.
    - Les données de test doivent rester représentatives des demandes réelles.
    - Le RAG réglementaire doit être relu avec une attention particulière aux citations.
    """)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    missing = [p for p in [CLASSIFICATION_PATH, RAG_INFO_PATH, RAG_REGL_PATH] if not p.exists()]
    if missing:
        st.error("Fichiers JSON manquants :")
        st.write([str(p) for p in missing])
        st.stop()

    clf = load_json(CLASSIFICATION_PATH)
    ri  = load_json(RAG_INFO_PATH)
    rr  = load_json(RAG_REGL_PATH)

    page = build_sidebar(clf, ri, rr)

    if page == "Synthese":
        page_synthesis(clf, ri, rr)
    elif page == "Classification":
        page_classification(clf)
    elif page == "RAG informationnel":
        page_rag_info(ri)
    elif page == "RAG reglementaire":
        page_rag_regl(rr)
    else:
        page_methodology()


if __name__ == "__main__":
    main()
