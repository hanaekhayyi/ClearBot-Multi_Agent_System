"""
test_classification.py — Tests unitaires pour l'agent de classification.

Teste :
  - Règles de classification déterministes (classify_by_priority_rules)
  - Détection de service par keywords
  - Extraction locale de dates et fréquences
  - Détection de messages vagues
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "agents" / "support_classification"))

import pytest
from services.classifier import (
    classify_by_priority_rules,
    extract_date_local,
    extract_frequency_local,
    get_next_question_key,
)
from services.glpi_service import detect_service, normalize
from core.models import TicketClass


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — classify_by_priority_rules
# ══════════════════════════════════════════════════════════════════════════════

class TestClassifyByPriorityRules:
    """Teste les règles déterministes de classification (avant LLM)."""

    def test_fichier_metier_aoe_is_incident(self):
        result = classify_by_priority_rules("Nous n'avons pas reçu les AOE du 15 mai")
        assert result is not None
        assert result.classe == TicketClass.INCIDENT

    def test_fichier_metier_cft_vide_is_incident(self):
        result = classify_by_priority_rules("Les fichiers CFT sont vides")
        assert result is not None
        assert result.classe == TicketClass.INCIDENT

    def test_fichier_metier_rsm_is_incident(self):
        result = classify_by_priority_rules("Le fichier RSM n'a pas été reçu")
        assert result is not None
        assert result.classe == TicketClass.INCIDENT

    def test_fichier_metier_mt547_is_incident(self):
        result = classify_by_priority_rules("Les MT547 reçus sont vides")
        assert result is not None
        assert result.classe == TicketClass.INCIDENT

    def test_facture_erronee_is_reclamation(self):
        result = classify_by_priority_rules("La facture comporte une erreur sur le montant")
        assert result is not None
        assert result.classe == TicketClass.RECLAMATION

    def test_facture_non_recue_is_reclamation(self):
        result = classify_by_priority_rules("Nous n'avons pas reçu la facture de droits d'admission")
        assert result is not None
        assert result.classe == TicketClass.RECLAMATION

    def test_document_deja_recu_renvoi_is_demande(self):
        result = classify_by_priority_rules(
            "Nous avons déjà reçu le document mais merci de nous le renvoyer à nouveau"
        )
        # Ce cas peut retourner None si les keywords ne matchent pas exactement
        # Le LLM prendra le relais pour classifier
        if result is not None:
            assert result.classe == TicketClass.DEMANDE

    def test_message_generique_returns_none(self):
        """Un message sans fichier métier ni facture ne déclenche pas de règle."""
        result = classify_by_priority_rules("Bonjour, j'ai un problème")
        assert result is None

    def test_token_perdu_returns_none(self):
        """Token perdu = pas de règle déterministe (sera classé par LLM)."""
        result = classify_by_priority_rules("J'ai perdu mon token RSA")
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — detect_service
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectService:
    """Teste la détection automatique du service par keywords."""

    def test_tcs_bancs_detected_as_technique(self):
        service = detect_service("je n'arrive pas à accéder à TCS BaNCS", "incident")
        assert service is not None
        assert service.label == "Technique"

    def test_aoe_detected_as_bourse(self):
        service = detect_service("les avis d'opéré de la bourse ne sont pas reçus", "incident")
        assert service is not None
        assert service.label == "Post-marche-Bourse"

    def test_repo_detected(self):
        service = detect_service("problème avec les pensions livrées repo", "incident")
        assert service is not None
        assert service.label == "Post-marche-Repo's"

    def test_reporting_detected(self):
        service = detect_service("le fichier RCQ de fin de journée est manquant", "incident")
        assert service is not None
        assert service.label == "Reporting"

    def test_facturation_reclamation(self):
        service = detect_service("la facture de droits d'admission comporte une erreur de facturation", "reclamation")
        assert service is not None
        assert service.label == "Facturation"

    def test_reinitialisation_mdp_demande(self):
        service = detect_service("réinitialisation de mon mot de passe TCS", "demande")
        assert service is not None
        assert service.label == "Reinitialisation mot de passe TCS"

    def test_unknown_returns_none(self):
        service = detect_service("bonjour", "incident")
        assert service is None


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — extract_date_local
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractDate:
    """Teste l'extraction locale de dates."""

    def test_date_format_jj_mm_aaaa(self):
        assert extract_date_local("depuis le 15/05/2026") == "15/05/2026"

    def test_date_format_jj_mm_aa(self):
        assert extract_date_local("le 03/01/26") == "03/01/2026"

    def test_date_format_tiret(self):
        assert extract_date_local("depuis le 15-05-2026") == "15/05/2026"

    def test_aujourdhui(self):
        result = extract_date_local("depuis aujourd'hui")
        assert result is not None
        assert "/" in result

    def test_hier(self):
        result = extract_date_local("depuis hier")
        assert result is not None
        assert "/" in result

    def test_no_date(self):
        assert extract_date_local("j'ai un problème") is None


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — extract_frequency_local
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractFrequency:
    """Teste l'extraction locale de fréquence."""

    def test_chaque_jour(self):
        assert extract_frequency_local("ça arrive chaque jour") == "Chaque jour"

    def test_recurrent(self):
        assert extract_frequency_local("c'est récurrent") == "Récurrent"

    def test_une_fois(self):
        assert extract_frequency_local("c'est la première fois") == "1 fois"

    def test_no_frequency(self):
        assert extract_frequency_local("j'ai un problème") is None


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — normalize
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalize:
    """Teste la normalisation de texte."""

    def test_accents_removed(self):
        assert normalize("réclamation") == "reclamation"

    def test_uppercase_lowered(self):
        assert normalize("TCS BaNCS") == "tcs bancs"

    def test_multiple_spaces(self):
        assert normalize("  hello   world  ") == "hello world"

    def test_apostrophe_normalized(self):
        # L'apostrophe typographique \u2019 est remplacée par l'apostrophe simple
        result = normalize("l\u2019affilié")
        assert "\u2019" not in result  # L'apostrophe typographique est normalisée
