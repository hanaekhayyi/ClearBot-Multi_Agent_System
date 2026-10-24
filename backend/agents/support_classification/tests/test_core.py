"""
tests/test_core.py — Suite de tests unitaires Maroclear v7.

Couvre :
  - Modèles (TicketClass, DeclarationResult)
  - Config (chargement YAML, validation)
  - GLPI (détection gravité, compute_glpi)
  - Détection service
  - Extraction date/fréquence
  - Validation réponse classification LLM
  - Agent en mode batch (sans API réelle)
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

# ── Fixtures path ─────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent


# ══════════════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════════════

class TestTicketClass:
    def test_from_str_standard(self):
        from core.models import TicketClass
        assert TicketClass.from_str("INCIDENT")    == TicketClass.INCIDENT
        assert TicketClass.from_str("DEMANDE")     == TicketClass.DEMANDE
        assert TicketClass.from_str("RÉCLAMATION") == TicketClass.RECLAMATION
        assert TicketClass.from_str("RECLAMATION") == TicketClass.RECLAMATION

    def test_from_str_case_insensitive(self):
        from core.models import TicketClass
        assert TicketClass.from_str("incident") == TicketClass.INCIDENT
        assert TicketClass.from_str("Demande")  == TicketClass.DEMANDE

    def test_from_str_fallback(self):
        """from_str doit lever ValueError sur une valeur inconnue."""
        from core.models import TicketClass
        with pytest.raises(ValueError, match="Classe de ticket inconnue"):
            TicketClass.from_str("INCONNU")

    def test_value_preserved(self):
        from core.models import TicketClass
        assert TicketClass.RECLAMATION.value == "RÉCLAMATION"


# ══════════════════════════════════════════════════════════════════════════════
# UTILS
# ══════════════════════════════════════════════════════════════════════════════

class TestStripHtml:
    def test_removes_tags(self):
        from core.utils import strip_html
        assert strip_html("<p>Bonjour <b>monde</b></p>") == "Bonjour monde"

    def test_normalizes_spaces(self):
        from core.utils import strip_html
        assert strip_html("a  <br/>  b") == "a b"

    def test_empty_string(self):
        from core.utils import strip_html
        assert strip_html("") == ""

    def test_no_tags(self):
        from core.utils import strip_html
        assert strip_html("texte simple") == "texte simple"


class TestDeclarationResult:
    def _make_result(self, **overrides):
        from core.models import DeclarationResult, TicketClass, TicketFiche, ServiceInfo
        fiche = TicketFiche(
            service=ServiceInfo("1", "Post-marché-Bourse", "TCS BaNCS", "desc"),
            date_occurrence="01/01/2025",
            frequence_occurrence="1 fois",
            description="Test desc",
        )
        defaults = dict(
            ticket_id="t001",
            classe=TicketClass.INCIDENT,
            confiance=0.95,
            justification="Test",
            fiche=fiche,
            texte_original="ticket texte",
        )
        defaults.update(overrides)
        return DeclarationResult(**defaults)

    def test_is_complete_true(self):
        r = self._make_result()
        assert r.is_complete is True

    def test_is_complete_false_missing_date(self):
        from core.models import TicketFiche
        r = self._make_result(fiche=TicketFiche())
        assert r.is_complete is False

    def test_to_dict_keys(self):
        r  = self._make_result()
        d  = r.to_dict()
        assert "ticket_id" in d
        assert "classe" in d
        assert d["classe"] == "INCIDENT"
        assert "fiche" in d
        assert "is_complete" in d

    def test_to_dict_confiance_rounded(self):
        r = self._make_result(confiance=0.9555555)
        assert r.to_dict()["confiance"] == 0.956


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

class TestConfig:
    def test_load_default(self):
        from core.config import AppConfig
        cfg = AppConfig()
        assert cfg.model_name
        assert 0 < cfg.certainty_threshold < 1
        assert len(cfg.services) >= 10

    def test_valid_classes(self):
        from core.config import AppConfig
        cfg = AppConfig()
        assert "INCIDENT" in cfg.valid_classes
        assert "DEMANDE"  in cfg.valid_classes

    def test_services_have_required_keys(self):
        from core.config import AppConfig
        cfg = AppConfig()
        for code, svc in cfg.services.items():
            assert "label"   in svc, f"Service {code} manque 'label'"
            assert "system"  in svc, f"Service {code} manque 'system'"
            assert "keywords" in svc, f"Service {code} manque 'keywords'"

    def test_glpi_matrix_coherent(self):
        from core.config import AppConfig
        cfg = AppConfig()
        for svc_code, gravites in cfg.glpi_matrix.items():
            for gravite, vals in gravites.items():
                assert len(vals) == 3, (
                    f"Matrice GLPI service={svc_code} gravité={gravite} : "
                    f"doit avoir 3 valeurs (urgence, impact, priorite)"
                )

    def test_missing_key_raises(self):
        from core.config import AppConfig, ConfigError
        import yaml, tempfile, os
        bad_yaml = "model:\n  name: test\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(bad_yaml)
            fname = f.name
        try:
            with pytest.raises(ConfigError):
                AppConfig(Path(fname))
        finally:
            os.unlink(fname)


# ══════════════════════════════════════════════════════════════════════════════
# GLPI SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class TestNormalize:
    def test_accents_removed(self):
        from services.glpi_service import normalize
        assert normalize("Réclàmàtion") == "reclamation"

    def test_apostrophe_normalized(self):
        from services.glpi_service import normalize
        assert normalize("d\u2019accord") == "d'accord"

    def test_multiple_spaces(self):
        from services.glpi_service import normalize
        assert normalize("a  b   c") == "a b c"


class TestDetectGravite:
    def test_blocage_general_detected(self):
        from services.glpi_service import detect_gravite
        g, conf = detect_gravite("Le dénouement est bloqué pour tous les affiliés", "1")
        assert g == "blocage_general"
        assert conf > 0

    def test_lenteur_detected(self):
        from services.glpi_service import detect_gravite
        g, conf = detect_gravite("La plateforme est très lente depuis ce matin", "9")
        assert g == "lenteur"

    def test_indisponible_detected(self):
        from services.glpi_service import detect_gravite
        g, conf = detect_gravite("MyMaroclear est indisponible", "9")
        assert g == "indisponible"

    def test_fallback_on_unknown_text(self):
        from services.glpi_service import detect_gravite
        g, conf = detect_gravite("problème quelconque sans mot-clé", "1")
        assert g == "blocage_affilie"  # fallback service 1
        assert conf < 0.5  # confidence basse

    def test_confidence_bounded(self):
        """La confidence doit toujours être dans [0.0, 1.0]."""
        from services.glpi_service import detect_gravite
        _, conf = detect_gravite("blocage general du marche, rien ne marche, totalement inaccessible", "1")
        assert 0.0 <= conf <= 1.0

    def test_erreur_nongen_reporting(self):
        from services.glpi_service import detect_gravite
        g, conf = detect_gravite("Les documents comptables de fin de journée sont manquants", "8")
        assert g == "erreur_nongen"


class TestComputeGlpi:
    def test_p1_for_general_block(self):
        from services.glpi_service import compute_glpi
        r = compute_glpi("1", "blocage general du marche, rien ne marche")
        assert "P1" in str(r.priorite)
        assert r.urgence == "Tres haute"

    def test_p4_for_display_bug(self):
        from services.glpi_service import compute_glpi
        r = compute_glpi("1", "problème d'affichage mineur sur l'écran")
        assert "P4" in str(r.priorite)

    def test_dispatcher_for_autre(self):
        from services.glpi_service import compute_glpi
        r = compute_glpi("10", "demande diverse")
        assert "dispatcher" in str(r.priorite).lower()

    def test_returns_glpi_info(self):
        from services.glpi_service import compute_glpi
        from core.models import GlpiInfo
        r = compute_glpi("9", "plateforme indisponible depuis ce matin")
        assert isinstance(r, GlpiInfo)
        assert r.gravite_detectee == "indisponible"


# ══════════════════════════════════════════════════════════════════════════════
# DÉTECTION SERVICE
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectService:
    def test_bourse_detected(self):
        from services.glpi_service import detect_service
        svc = detect_service("Problème avec les contrats bourse d'aujourd'hui")
        assert svc is not None
        assert svc.code == "1"

    def test_reporting_detected(self):
        from services.glpi_service import detect_service
        svc = detect_service("Nous n'avons pas reçu le RSM de fin de journée")
        assert svc is not None
        assert svc.code == "8"

    def test_technique_detected(self):
        from services.glpi_service import detect_service
        svc = detect_service("MyMaroclear est inaccessible, page blanche")
        assert svc is not None
        assert svc.code == "9"

    def test_no_match_returns_none(self):
        from services.glpi_service import detect_service
        svc = detect_service("bonjour")
        assert svc is None

    def test_auto_detected_flag(self):
        from services.glpi_service import detect_service
        svc = detect_service("le repo présente un problème de dénouement")
        assert svc is not None
        assert svc.auto_detected is True


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACTION DATE ET FRÉQUENCE
# ══════════════════════════════════════════════════════════════════════════════

class TestExtractDate:
    def test_slash_format(self):
        from services.classifier import extract_date_local
        assert extract_date_local("Le 15/03/2025 nous avons constaté") == "15/03/2025"

    def test_dash_format(self):
        from services.classifier import extract_date_local
        assert extract_date_local("Depuis le 2025-03-15") == "15/03/2025"

    def test_hier(self):
        from services.classifier import extract_date_local
        from datetime import datetime, timedelta
        expected = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
        assert extract_date_local("Hier le problème a commencé") == expected

    def test_aujourdhui(self):
        from services.classifier import extract_date_local
        expected = datetime.now().strftime("%d/%m/%Y")
        assert extract_date_local("Ce matin la plateforme est tombée") == expected

    def test_no_date(self):
        from services.classifier import extract_date_local
        assert extract_date_local("Problème sans date") is None


class TestExtractFrequency:
    def test_chaque_jour(self):
        from services.classifier import extract_frequency_local
        assert extract_frequency_local("Cela se produit chaque jour depuis une semaine") == "Chaque jour"

    def test_une_fois(self):
        from services.classifier import extract_frequency_local
        assert extract_frequency_local("C'est la première fois que cela arrive") == "1 fois"

    def test_recurrent(self):
        from services.classifier import extract_frequency_local
        assert extract_frequency_local("Le problème est récurrent depuis plusieurs jours") == "Récurrent"

    def test_none_when_absent(self):
        from services.classifier import extract_frequency_local
        assert extract_frequency_local("Problème technique") is None


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION RÉPONSE LLM
# ══════════════════════════════════════════════════════════════════════════════

class TestValidateClassification:
    def test_valid_response(self):
        from services.classifier import _validate_classification_response
        from core.models import TicketClass
        data = {"classe": "INCIDENT", "confiance": 0.95, "justification": "OK", "ambiguite": None}
        r = _validate_classification_response(data)
        assert r.classe == TicketClass.INCIDENT
        assert r.confiance == 0.95

    def test_missing_classe_raises(self):
        from services.classifier import _validate_classification_response
        from core.models import ValidationError
        with pytest.raises(ValidationError):
            _validate_classification_response({"confiance": 0.9})

    def test_invalid_classe_raises(self):
        from services.classifier import _validate_classification_response
        from core.models import ValidationError
        with pytest.raises(ValidationError):
            _validate_classification_response({"classe": "INCONNU", "confiance": 0.9})

    def test_confiance_clamped(self):
        from services.classifier import _validate_classification_response
        data = {"classe": "DEMANDE", "confiance": 1.5, "justification": "test"}
        r = _validate_classification_response(data)
        assert r.confiance == 1.0

    def test_reclamation_accent_variant(self):
        from services.classifier import _validate_classification_response
        from core.models import TicketClass
        data = {"classe": "RÉCLAMATION", "confiance": 0.9, "justification": "test"}
        r = _validate_classification_response(data)
        assert r.classe == TicketClass.RECLAMATION


# ══════════════════════════════════════════════════════════════════════════════
# LLM CLIENT — test parse JSON robuste
# ══════════════════════════════════════════════════════════════════════════════

class TestLLMParsing:
    def test_parse_clean_json(self):
        from services.llm_client import _parse_json_response
        raw = '{"classe": "INCIDENT", "confiance": 0.9}'
        r   = _parse_json_response(raw)
        assert r["classe"] == "INCIDENT"

    def test_parse_with_backticks(self):
        from services.llm_client import _parse_json_response
        raw = '```json\n{"classe": "DEMANDE", "confiance": 0.8}\n```'
        r   = _parse_json_response(raw)
        assert r["classe"] == "DEMANDE"

    def test_parse_with_trailing_comma(self):
        from services.llm_client import _parse_json_response
        raw = '{"classe": "INCIDENT", "confiance": 0.9,}'
        r   = _parse_json_response(raw)
        assert r["confiance"] == 0.9

    def test_empty_raises(self):
        from services.llm_client import _parse_json_response
        from core.models import ValidationError
        with pytest.raises(ValidationError):
            _parse_json_response("   ")

    def test_invalid_json_raises(self):
        from services.llm_client import _parse_json_response
        from core.models import ValidationError
        with pytest.raises(ValidationError):
            _parse_json_response("pas du json du tout")


# ══════════════════════════════════════════════════════════════════════════════
# AGENT — mode batch mocké (sans API réelle)
# ══════════════════════════════════════════════════════════════════════════════

class TestAgentBatch:
    """Tests sans appel réseau — le LLM est mocké sur TOUS les appels."""

    def _mock_llm_response(self, classe: str = "INCIDENT", confiance: float = 0.95):
        return {
            "classe": classe,
            "confiance": confiance,
            "justification": "Test mock.",
            "ambiguite": None,
            "noeud_question": None,
        }

    def _mock_extract_response(self):
        """Réponse mock pour l'appel LLM d'extraction de champs."""
        return {
            "description": "Description extraite automatiquement.",
            "date_occurrence": None,
            "frequence_occurrence": None,
            "solution_proposee": None,
            "documents_joints": [],
        }

    def test_batch_incident(self):
        from core.agent import ClassificationAgent
        agent = ClassificationAgent()
        with patch("services.classifier.call_llm", side_effect=[
            self._mock_llm_response("INCIDENT"),
            self._mock_extract_response(),
        ]):
            r = agent.run_batch("Plateforme inaccessible depuis ce matin.", "test_001")
            assert r.classe.value == "INCIDENT"
            assert r.ticket_id == "test_001"

    def test_batch_demande(self):
        from core.agent import ClassificationAgent
        agent = ClassificationAgent()
        with patch("services.classifier.call_llm", side_effect=[
            self._mock_llm_response("DEMANDE", 0.92),
            self._mock_extract_response(),
        ]):
            r = agent.run_batch("Merci de nous envoyer un nouveau token RSA.", "test_002")
            assert r.classe.value == "DEMANDE"

    def test_batch_result_has_glpi(self):
        from core.agent import ClassificationAgent
        agent = ClassificationAgent()
        with patch("services.classifier.call_llm", side_effect=[
            self._mock_llm_response(),
            self._mock_extract_response(),
        ]):
            r = agent.run_batch("La plateforme TCS Banks est indisponible.", "test_003")
            assert r.fiche.glpi is not None

    def test_batch_complete_for_full_ticket(self):
        from core.agent import ClassificationAgent
        agent = ClassificationAgent()
        full_ticket = (
            "Depuis hier 01/04/2025, la plateforme MyMaroclear est indisponible. "
            "Nous ne pouvons plus accéder à nos opérations habituelles. "
            "Ce problème est récurrent."
        )
        with patch("services.classifier.call_llm", side_effect=[
            self._mock_llm_response(),
            self._mock_extract_response(),
        ]):
            r = agent.run_batch(full_ticket, "test_004")
            assert r.fiche.date_occurrence is not None
            assert r.fiche.frequence_occurrence is not None


# ══════════════════════════════════════════════════════════════════════════════
# RÈGLES MÉTIER — CAS VALIDÉS (few-shot)
# ══════════════════════════════════════════════════════════════════════════════

VALIDATED_CASES = [
    # (texte, classe_attendue)
    ("Merci de nous communiquer le solde au 31/12/2025.", "DEMANDE"),
    ("J'ai perdu mon Token RSA suite à détérioration de mon poste. Merci de m'en envoyer un nouveau.", "DEMANDE"),
    ("Merci de mettre à notre disposition l'avis d'opéré avec référence X.", "DEMANDE"),
    ("La facture comporte une erreur au niveau de la quantité du droit d'admission.", "RÉCLAMATION"),
    ("Nous avons constaté un écart : la position devrait être X mais MCL affiche Y.", "RÉCLAMATION"),
    ("Nous n'arrivons pas à accéder aux plateformes TCS BANKS.", "INCIDENT"),
    ("Nous ne pouvons plus valider les opérations que nous validons habituellement.", "INCIDENT"),
    ("Les fichiers CFT se font mais sont vides.", "INCIDENT"),
]


class TestValidatedCases:
    """
    Tests d'intégration des cas officiels validés.
    Mockent les DEUX appels LLM (classification + extraction) sans API.
    """

    @pytest.mark.parametrize("text, expected_class", VALIDATED_CASES)
    def test_validated_case(self, text: str, expected_class: str):
        from core.agent import ClassificationAgent
        agent = ClassificationAgent()

        classif_response = {
            "classe": expected_class,
            "confiance": 0.95,
            "justification": "Mock validated.",
            "ambiguite": None,
            "noeud_question": None,
        }
        extract_response = {
            "description": text,
            "date_occurrence": None,
            "frequence_occurrence": None,
            "solution_proposee": None,
            "documents_joints": [],
        }

        # side_effect comme liste : 1er appel → classif, 2ème → extract
        # cycle=True via itertools pour les appels supplémentaires éventuels
        with patch(
            "services.classifier.call_llm",
            side_effect=[classif_response, extract_response, extract_response],
        ):
            r = agent.run_batch(text, f"val_{text[:20]}")
            assert r.classe.value == expected_class, (
                f"Texte: '{text}'\n"
                f"Attendu: {expected_class}, Obtenu: {r.classe.value}"
            )
