"""
Nettoyage et prétraitement des documents PDF avant chunking.
"""

import re
import unicodedata
from typing import List


class DocumentCleaner:
    """
    Nettoie le texte brut extrait d'un PDF :
    suppression des en-têtes/pieds de page, normalisation des espaces,
    normalisation des apostrophes et ligatures Unicode,
    corrections des erreurs OCR connues.
    """

    # ------------------------------------------------------------------
    # Ligatures Unicode → séquences ASCII
    # Ces caractères apparaissent quand le PDF encode ff/fi/fl/ffi/ffl
    # comme un seul glyphe Unicode au lieu de deux lettres séparées.
    # ------------------------------------------------------------------
    LIGATURE_MAP = {
        '\ufb00': 'ff',   # ﬀ
        '\ufb01': 'fi',   # ﬁ  ← "ﬁnancier", "qualiﬁés"
        '\ufb02': 'fl',   # ﬂ
        '\ufb03': 'ffi',  # ﬃ
        '\ufb04': 'ffl',  # ﬄ
        '\ufb05': 'st',   # ﬅ
        '\ufb06': 'st',   # ﬆ
        '\u0152': 'OE',   # Œ
        '\u0153': 'oe',   # œ
        '\u00e6': 'ae',   # æ
        '\u00c6': 'AE',   # Æ
    }

    # ------------------------------------------------------------------
    # Corrections OCR résiduelles (après ligatures)
    # La ligature ffi → "Nil" ou "Til" est un bug de certains extracteurs PDF
    # qui lisent le glyphe ligature comme un caractère latin majuscule + "il"
    # ------------------------------------------------------------------
    OCR_CORRECTIONS = {
        # aNilié / aTilié / aFilié → affilié  (toutes variantes observées)
        r'\ba[NTF]ili': 'affili',   # couvre affilié, affiliation, affilier…
    }

    def __init__(self, footer_patterns: List[str], header_patterns: List[str]):
        self.footer_patterns = footer_patterns
        self.header_patterns = header_patterns
        # Patterns génériques indépendants de la configuration
        self.noise_patterns = [
            r'^\s*\d+\s*$',             # Numéros de page isolés
            r'^[-_=]{3,}$',             # Lignes de séparation
            r'^\s*\.\s*\.\s*\.\s*$',    # Points de suite
        ]

    # ------------------------------------------------------------------
    # Étape 1 — Ligatures Unicode
    # ------------------------------------------------------------------
    def normalize_ligatures(self, text: str) -> str:
        """
        Remplace les ligatures Unicode typographiques par leur équivalent ASCII.
        Ex : 'ﬁnancier' → 'financier', 'qualiﬁés' → 'qualifiés'
        """
        for ligature, replacement in self.LIGATURE_MAP.items():
            text = text.replace(ligature, replacement)
        return text

    # ------------------------------------------------------------------
    # Étape 2 — Apostrophes et guillemets
    # ------------------------------------------------------------------
    @staticmethod
    def normalize_apostrophes(text: str) -> str:
        """
        Normalise toutes les variantes d'apostrophe/guillemet simple
        vers l'apostrophe droite ASCII (U+0027).

        Caractères traités :
          '  U+2019  RIGHT SINGLE QUOTATION MARK  (le plus fréquent en PDF)
          '  U+2018  LEFT  SINGLE QUOTATION MARK
          ‛  U+201B  SINGLE HIGH-REVERSED-9 QUOTATION MARK
          ´  U+00B4  ACUTE ACCENT (utilisé parfois comme apostrophe)
          `  U+0060  GRAVE ACCENT
          ʼ  U+02BC  MODIFIER LETTER APOSTROPHE
        """
        apostrophe_variants = [
            '\u2019',  # '
            '\u2018',  # '
            '\u201b',  # ‛
            '\u00b4',  # ´
            '\u0060',  # `
            '\u02bc',  # ʼ
        ]
        for variant in apostrophe_variants:
            text = text.replace(variant, "'")
        return text

    # ------------------------------------------------------------------
    # Étape 3 — Corrections OCR résiduelles
    # ------------------------------------------------------------------
    def apply_ocr_corrections(self, text: str) -> str:
        """Corrige les erreurs OCR connues (mauvais glyphes PDF → texte faux)."""
        for pattern, replacement in self.OCR_CORRECTIONS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    # ------------------------------------------------------------------
    # Pipeline principal
    # ------------------------------------------------------------------
    def clean_text(self, text: str) -> str:
        """
        Nettoie le texte dans cet ordre :
          1. Ligatures Unicode  (ﬁ → fi, ﬀ → ff …)
          2. Normalisation des apostrophes (' → ')
          3. Suppression en-têtes / pieds de page / bruit
          4. Suppressions spécifiques CDVM + pagination
          5. Normalisation des espaces et sauts de ligne
          6. Corrections OCR résiduelles (aNilié → affilié …)
        """
        # 1 — Ligatures
        text = self.normalize_ligatures(text)

        # 2 — Apostrophes
        text = self.normalize_apostrophes(text)

        # 3 — Filtrage ligne par ligne
        all_patterns = self.footer_patterns + self.header_patterns + self.noise_patterns
        cleaned = []
        for line in text.split('\n'):
            if any(re.search(p, line, re.IGNORECASE) for p in all_patterns):
                continue
            if line.strip():
                cleaned.append(line)
        text = '\n'.join(cleaned)

        # 4 — Suppressions spécifiques
        # Blocs de versioning multi-lignes (circulaires CDVM)
        text = re.sub(
            r'La circulaire du CDVM.*?(?:Modifiée|Edition).*?\d{4}',
            '', text, flags=re.IGNORECASE | re.DOTALL
        )
        # Mentions de pagination
        text = re.sub(r'Page\s+\d+\s+(?:sur|/)\s+\d+', '', text, flags=re.IGNORECASE)

        # 5 — Normalisation des espaces
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 6 — Corrections OCR résiduelles (après normalisation des espaces)
        text = self.apply_ocr_corrections(text)

        return text.strip()

    # ------------------------------------------------------------------
    # Détection de langue — inchangée
    # ------------------------------------------------------------------
    def detect_language(self, text: str) -> str:
        """
        Détecte la langue principale du document (fr / en).
        Utilise un scoring pondéré sur des mots-clés juridiques
        et les caractères accentués comme indicateur fort du français.
        """
        sample = text[:10000].lower()

        french_kw = {
            'article': 3, 'chapitre': 3, 'annexe': 3, 'loi': 3,
            'dahir': 5, 'règlement': 2, 'directive': 2, 'société': 2,
            'dépositaire': 3, 'dispositions': 2, 'conformément': 2, 'notamment': 2
        }
        english_kw = {
            'chapter': 3, 'annex': 3, 'law': 3, 'regulation': 3,
            'shall': 5, 'provisions': 2, 'accordance': 3,
            'pursuant': 3, 'thereof': 3, 'whereby': 2
        }

        fr_score = sum(w for k, w in french_kw.items() if k in sample)
        en_score = sum(w for k, w in english_kw.items() if k in sample)

        # Les caractères accentués sont un fort indicateur du français
        if len(re.findall(r'[àâäéèêëïîôùûüÿæœç]', sample)) > 10:
            fr_score += 10

        if fr_score > en_score * 1.5:
            return "fr"
        elif en_score > fr_score:
            return "en"
        return "fr"