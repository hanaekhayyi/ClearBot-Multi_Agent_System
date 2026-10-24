"""
Configuration centralisée du pipeline de chunking.
"""

from pathlib import Path


class Config:
    """Paramètres du pipeline : chemins, chunking, nettoyage, catégories, références."""

    # Chemins
    PROJECT_ROOT = Path(__file__).parent.parent
    INPUT_DIR    = PROJECT_ROOT / "data" / "input"
    OUTPUT_DIR   = PROJECT_ROOT / "data" / "output"
    OUTPUT_FILE  = OUTPUT_DIR / "chunks_output.json"
    LOG_FILE     = OUTPUT_DIR / "processing_log.txt"

    # Paramètres de chunking
    # CHUNK_OVERLAP = 0 : évite les doublons et mélanges entre articles
    CHUNK_SIZE    = 400
    CHUNK_OVERLAP = 0
    ENCODING_NAME = "cl100k_base"

    # Patterns de nettoyage des documents
    FOOTER_PATTERNS = [
        r"La circulaire du CDVM[\s\-]+Version.*?(?:Modifiée|Edition).*?\d{4}",
        r"Page\s+\d+\s+(?:sur|/)\s+\d+",
        r"^[-_=]+$",
        r"^\s*\d+\s*$",
    ]
    HEADER_PATTERNS = [
        r"^Royaume du Maroc.*?Ministère",
        r"^AUTORITE MAROCAINE DU MARCHE DES CAPITAUX",
    ]

    # Catégories de documents — basées sur des mots-clés dans le nom de fichier
    CATEGORIES = {
        'CATEGORY_A_LOIS':        ['Dahir', 'Loi', 'LOI', 'loi_nø', 'Loi_N_'],
        'CATEGORY_B_DIRECTIVES':  ['Directive', 'DNSSI', 'PFMI', 'cadre_dinformation'],
        'CATEGORY_C_ANNEXES':     ['Annexes_Livre', 'ANNEXE'],
        'CATEGORY_D_RAPPORTS':    ['Règles_de_fonctionnement', 'REGLEMENT', 'MCL_ART'],
    }

    # Formules juridiques utilisées pour détecter les références croisées (detect_links).
    # Ces expressions précèdent systématiquement un numéro d'article dans les textes légaux.
    REF_KEYWORDS = [
        r"visé[es]*\s+à\s+l['\s]+article",
        r"mentionné[es]*\s+à\s+l['\s]+article",
        r"prévu[es]*\s+à\s+l['\s]+article",
        r"conformément\s+aux\s+dispositions\s+de\s+l['\s]+article",
        r"sous\s+réserve\s+des\s+dispositions\s+de\s+l['\s]+article",
        r"dans\s+les\s+conditions\s+fixées\s+à\s+l['\s]+article",
    ]

    def __init__(self):
        """Crée les dossiers de sortie si absents."""
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)