"""
Extraction des métadonnées spécifiques aux documents juridiques.

CORRECTIFS v2 (vs version initiale) :
  - detect_links : 5 bugs corrigés (voir détail dans la docstring de la méthode)
  - extract_article_number : inchangé (déjà correct)
"""

import re
from typing import Optional, List
from config import Config

# ---------------------------------------------------------------------------
# Constante partagée : pattern du numéro d'article canonique
# Couvre : 1, 19-1, 8-1, premier  (pas "1er" seul — géré dans extract_article_number)
# ---------------------------------------------------------------------------
_ART_NUM = r"(?:\d+(?:\s*[-–]\s*\d+)?|\bpremier\b)"


def _normalize_link(raw_num: str) -> str:
    """
    Normalise un identifiant d'article brut en forme canonique.
      "8 -1"  -> "article 8-1"
      " 19 "  -> "article 19"
      "premier" -> "article premier"
    """
    cleaned = re.sub(r'\s*[-–]\s*', '-', raw_num.strip()).lower()
    return f"article {cleaned}"


class MetadataExtractor:
    """Extrait les métadonnées structurelles selon le type de document."""

    # ------------------------------------------------------------------
    # extract_article_number — inchangé, déjà correct
    # ------------------------------------------------------------------
    @staticmethod
    def extract_article_number(text: str) -> Optional[str]:
        """
        Extrait le numéro d'article depuis le texte d'un chunk.
        Supporte : Article 1, Article 1er, Article premier,
                   Article 8-1, Article 23 bis.
        """
        patterns = [
            (r'\bArticle\s+(premier|1er|1ère)',
             lambda m: f"Article {m.group(1).lower().replace('ère','er')}"),
            (r'\bArt\.\s+(premier|1er)',
             lambda m: f"Article {m.group(1).lower()}"),
            (r'\bArticle\s+(\d+)\s*[-–]\s*(\d+)',
             lambda m: f"Article {m.group(1)}-{m.group(2)}"),
            (r'\bArticle\s+(\d+)\s+(bis|ter|quater|quinquies)',
             lambda m: f"Article {m.group(1)} {m.group(2)}"),
            (r'\bArticle\s+(\d+)\b',
             lambda m: f"Article {m.group(1)}"),
            (r'\bArt\.\s+(\d+)\b',
             lambda m: f"Article {m.group(1)}"),
        ]
        for pattern, formatter in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return formatter(match)
        return None

    # ------------------------------------------------------------------
    # detect_links — version corrigée
    # ------------------------------------------------------------------
    @staticmethod
    def detect_links(text: str, current_article_id: Optional[str] = None) -> List[str]:
        """
        Détecte les références croisées vers d'autres articles dans un chunk.

        BUGS CORRIGÉS PAR RAPPORT À LA VERSION INITIALE :
        ───────────────────────────────────────────────────
        BUG 1 — Plage "articles X à Y" non gérée
            Ancien : seul le premier article de la plage était capturé.
            Nouveau : expansion complète si l'écart est ≤ 30 articles
                      (ex. "articles 19 à 21" → ['article 19','article 20','article 21']),
                      sinon les deux bornes sont retournées.

        BUG 2 — "article premier" ignoré dans les références
            Ancien : la regex \d+ ne capturait pas le mot "premier".
            Nouveau : _ART_NUM accepte "premier" comme identifiant valide.

        BUG 3 — "paragraphe" ignoré (seulement "alinéa" était géré)
            Ancien : "le 3ème paragraphe de l'article 29" → non détecté.
            Nouveau : le pattern accepte indifféremment "alinéa" ou "paragraphe".

        BUG 4 — Suffixe ordinal "è" manquant (seuls er/e/ème étaient couverts)
            Ancien : "au 2è alinéa" → non détecté via le chemin alinéa.
            Nouveau : ajout de "è" dans le groupe optionnel des suffixes ordinaux.

        BUG 5 — Identifiants avec espace avant tiret non normalisés
            Ancien : "l'article 8 -1" → retournait "article 8 -1" (avec espace).
            Nouveau : _normalize_link() supprime les espaces autour des tirets
                      → "article 8-1" (forme canonique).

        NOUVELLE FONCTIONNALITÉ — Auto-référence "présent article"
            Si current_article_id est fourni et que le texte contient "présent article",
            l'identifiant de l'article courant est ajouté aux liens détectés.

        Paramètres
        ----------
        text : str
            Texte du chunk à analyser.
        current_article_id : str, optionnel
            Identifiant canonique de l'article auquel ce chunk appartient
            (ex. "article premier", "article 8-1"). Nécessaire pour résoudre
            les auto-références "présent article / ledit article".

        Retourne
        --------
        List[str]
            Liste triée et dédupliquée des identifiants détectés,
            sous la forme canonique "article N" (minuscule).
        """
        links: List[str] = []

        # ── 1. Alinéa / paragraphe ordinal ────────────────────────────────────
        # Couvre :
        #   "au 1er alinéa de l'article X"
        #   "au 2è  alinéa de l'article X"     ← BUG 4 corrigé (è)
        #   "au 3ème paragraphe de l'article X" ← BUG 3 corrigé (paragraphe)
        for num in re.findall(
            r"\d+(?:er|e|è|ème)?\s+(?:alinéa|paragraphe)"
            r"\s+de\s+l[''´`]?\s*article\s+(" + _ART_NUM + r")",
            text, flags=re.IGNORECASE
        ):
            links.append(_normalize_link(num))

        # ── 2. Référence singulière directe : "l'article X" ───────────────────
        # Couvre "article premier" grâce à _ART_NUM    ← BUG 2 corrigé
        for num in re.findall(
            r"l[''´`\s]article\s+(" + _ART_NUM + r")",
            text, flags=re.IGNORECASE
        ):
            links.append(_normalize_link(num))

        # ── 3. Plage : "articles X à Y" ───────────────────────────────────────
        # BUG 1 corrigé : expansion si écart ≤ 30, sinon bornes seulement
        for m in re.finditer(
            r"articles\s+(\d+(?:\s*[-–]\s*\d+)?)\s+à\s+(\d+(?:\s*[-–]\s*\d+)?)",
            text, flags=re.IGNORECASE
        ):
            try:
                start = int(re.search(r'\d+', m.group(1)).group())
                end   = int(re.search(r'\d+', m.group(2)).group())
                if 0 < end - start <= 30:
                    for n in range(start, end + 1):
                        links.append(f"article {n}")
                else:
                    # Trop grande plage : on retourne uniquement les bornes
                    links.append(_normalize_link(m.group(1)))
                    links.append(_normalize_link(m.group(2)))
            except (ValueError, AttributeError):
                pass

        # ── 4. Liste / pluriel : "articles X, Y et Z" ─────────────────────────
        # Séparateurs supportés : virgule, point-virgule, "et"
        for m in re.finditer(
            r"(?:les|aux|des)\s+articles\s+"
            r"(\d+(?:\s*[-–]\s*\d+)?"
            r"(?:(?:[,;]\s*|\s+et\s+)\d+(?:\s*[-–]\s*\d+)?)*)",
            text, flags=re.IGNORECASE
        ):
            for num in re.findall(r'\d+(?:\s*[-–]\s*\d+)?', m.group(1)):
                links.append(_normalize_link(num))

        # ── 5. Auto-référence "présent article" ───────────────────────────────
        if current_article_id and re.search(
            r'\bprésent\s+article\b', text, re.IGNORECASE
        ):
            links.append(current_article_id.lower())

        # ── Déduplication + tri ───────────────────────────────────────────────
        return sorted(set(links))

    # ------------------------------------------------------------------
    # Méthodes inchangées
    # ------------------------------------------------------------------

    @staticmethod
    def extract_rule_id_dnssi(text: str) -> Optional[str]:
        """
        Extrait le code de règle DNSSI (ex: ACTIF-SUP-AMOV).
        Cherche en priorité en début de ligne.
        """
        match = re.search(
            r'^\s*([A-Z]{3,}(?:-[A-Z]{3,}){1,3})\s*[:\(\-]',
            text, re.MULTILINE
        )
        if match:
            return match.group(1)
        match = re.search(r'\b([A-Z]{3,}(?:-[A-Z]{3,}){1,3})\b', text)
        return match.group(1) if match else None

    @staticmethod
    def extract_consideration_pfmi(text: str) -> Optional[str]:
        """
        Extrait la référence de considération essentielle PFMI (ex: CE 11.4).
        """
        patterns = [
            r'\bConsidération\s+essentielle\s+CE\s+(\d+\.\d+)',
            r'Considération\s+essentielle\s+(\d+\.\d+)',
            r'\b(CE)\s+(\d+\.\d+)\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                return f"CE {groups[-1]}"
        return None

    @staticmethod
    def extract_annexe_reference(text: str) -> Optional[str]:
        """
        Extrait la référence d'annexe.
        Supporte : ANNEXE I.4.A, Annexe II.2, ANNEXE 1, ANNEXE I-4.
        """
        patterns = [
            (r'(?:ANNEXE|Annexe)\s+([IVX]+\.?\d+(?:\.[A-Z])?)',
             lambda m: f"ANNEXE {m.group(1)}"),
            (r'(?:ANNEXE|Annexe)\s+(\d+)\s*[-–]\s*(\d+)',
             lambda m: f"ANNEXE {m.group(1)}-{m.group(2)}"),
            (r'(?:ANNEXE|Annexe)\s+(\d+)\b',
             lambda m: f"ANNEXE {m.group(1)}"),
            (r'\b(?:ANNEXE|Annexe)\s+([A-Z0-9\-\.]+)',
             lambda m: f"ANNEXE {m.group(1)}"),
        ]
        for pattern, formatter in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return formatter(match)
        return None

    @staticmethod
    def extract_section(text: str) -> Optional[str]:
        """
        Extrait l'en-tête de section.
        Supporte les numéros arabes, romains et "première".
        """
        match = re.search(
            r'(Section\s+(?:\d+|[IVX]+|première?))\s*[:\-]?\s*([^\n]*)',
            text, re.IGNORECASE
        )
        if match:
            section_num  = match.group(1).strip()
            section_name = match.group(2).strip()
            return f"{section_num} : {section_name}" if section_name else section_num
        return None

    @staticmethod
    def extract_titre(text: str) -> Optional[str]:
        """
        Extrait le TITRE juridique (niveau hiérarchique le plus haut).
        Format attendu : TITRE I : INTITULE
        """
        pattern = r'(TITRE\s+[IVX]+)\s*[:–]?\s*([^\n]+)'
        match   = re.search(pattern, text, re.IGNORECASE)
        if match:
            titre_num  = match.group(1).strip()
            titre_name = match.group(2).strip()
            return f"{titre_num} : {titre_name}"
        return None

    @staticmethod
    def extract_chapter(text: str) -> Optional[str]:
        """
        Extrait le CHAPITRE (niveau hiérarchique intermédiaire).
        Format attendu : CHAPITRE II : INTITULE
        """
        pattern = r'(CHAPITRE\s+[IVX]+)\s*[:–]?\s*([^\n]+)'
        match   = re.search(pattern, text, re.IGNORECASE)
        if match:
            chapter_num  = match.group(1).strip()
            chapter_name = match.group(2).strip()
            return f"{chapter_num} : {chapter_name}"
        return None

    @staticmethod
    def has_mathematical_formula(text: str) -> bool:
        """Détecte la présence de formules mathématiques."""
        math_symbols = [r'\$', r'\\sum', r'\\frac', r'M_i', r'\\times', r'\\int']
        return any(re.search(s, text) for s in math_symbols)


class DocumentCategorizer:
    """Catégorise automatiquement les documents à partir de leur nom de fichier."""

    def __init__(self, categories_config: dict):
        self.categories = categories_config

    def categorize(self, filename: str) -> str:
        """
        Retourne le code de catégorie correspondant au nom de fichier.
        Retourne CATEGORY_D_RAPPORTS si aucune catégorie ne correspond.
        """
        for category, keywords in self.categories.items():
            if any(keyword in filename for keyword in keywords):
                return category
        return 'CATEGORY_D_RAPPORTS'