"""
test_glpi.py — Tests unitaires pour le calcul de priorité GLPI.

Teste :
  - Matrice de priorité (service × gravité → P1/P2/P3/P4)
  - Détection de gravité par keywords
  - Fallback quand la gravité n'est pas détectée
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "agents" / "support_classification"))

import pytest
from services.glpi_service import compute_glpi, detect_gravite
from core.models import GlpiPriority


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — compute_glpi (matrice de priorité)
# ══════════════════════════════════════════════════════════════════════════════

class TestComputeGlpi:
    """Teste le calcul de priorité GLPI via la matrice service × gravité."""

    def test_technique_indisponible_is_p1(self):
        """Service Technique + plateforme indisponible = P1 Majeur."""
        glpi = compute_glpi("9", "la plateforme TCS BaNCS est indisponible")
        assert glpi.priorite == GlpiPriority.P1
        assert glpi.urgence == "Tres haute"
        assert glpi.impact == "Tres haut"

    def test_technique_lenteur_is_p1(self):
        """Service Technique + lenteur extrême = P1 Majeur."""
        glpi = compute_glpi("9", "lenteur extrême sur la plateforme")
        assert glpi.priorite == GlpiPriority.P1

    def test_bourse_blocage_general_is_p1(self):
        """Post-marché Bourse + blocage général = P1 Majeur."""
        glpi = compute_glpi("1", "blocage général du dénouement")
        assert glpi.priorite == GlpiPriority.P1

    def test_bourse_blocage_affilie_is_p2(self):
        """Post-marché Bourse + blocage d'un affilié = P2 Très haute."""
        glpi = compute_glpi("1", "nous ne pouvons pas saisir les opérations")
        assert glpi.priorite == GlpiPriority.P2

    def test_bourse_partiel_is_p3(self):
        """Post-marché Bourse + dysfonctionnement partiel = P3 Moyenne."""
        glpi = compute_glpi("1", "dysfonctionnement partiel contournable")
        assert glpi.priorite == GlpiPriority.P3

    def test_bourse_bug_affichage_is_p4(self):
        """Post-marché Bourse + bug d'affichage = P4 Basse."""
        glpi = compute_glpi("1", "bug affichage sur l'écran")
        assert glpi.priorite == GlpiPriority.P4

    def test_referentiel_impossible_is_p2(self):
        """Référentiel-Titres + impossibilité = P2 Très haute."""
        glpi = compute_glpi("5", "impossible de créer le code ISIN")
        assert glpi.priorite == GlpiPriority.P2

    def test_reporting_erreur_nongen_is_p1(self):
        """Reporting + non-génération documents = P1 Majeur."""
        glpi = compute_glpi("8", "non generation des documents comptables de fin de journée manquants")
        assert glpi.priorite == GlpiPriority.P1

    def test_technique_fichiers_vides_is_p1(self):
        """Service Technique + fichiers vides = P1 Majeur."""
        glpi = compute_glpi("9", "les fichiers reçus sont vides")
        assert glpi.priorite == GlpiPriority.P1

    def test_technique_batch_en_cours_is_p2(self):
        """Service Technique + batch en cours = P2 Très haute."""
        glpi = compute_glpi("9", "message d'erreur batch en cours")
        assert glpi.priorite == GlpiPriority.P2


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — detect_gravite
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectGravite:
    """Teste la détection de gravité par keywords."""

    def test_indisponible_detected(self):
        gravite, conf = detect_gravite("la plateforme est indisponible", "9")
        assert gravite == "indisponible"
        assert conf > 0.0

    def test_blocage_general_detected(self):
        gravite, conf = detect_gravite("blocage général du marché", "1")
        assert gravite == "blocage_general"

    def test_blocage_affilie_detected(self):
        gravite, conf = detect_gravite("nous ne pouvons pas saisir", "1")
        assert gravite == "blocage_affilie"

    def test_fichiers_vides_detected(self):
        gravite, conf = detect_gravite("les fichiers sont vides", "9")
        assert gravite == "fichiers_vides"

    def test_fallback_when_no_keyword(self):
        """Quand aucun keyword ne matche, retourne le fallback avec confiance basse."""
        gravite, conf = detect_gravite("bonjour j'ai un souci", "9")
        assert conf <= 0.5  # Confiance basse = fallback
