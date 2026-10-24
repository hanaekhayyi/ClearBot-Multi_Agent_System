"""
Tests unitaires des utilitaires RAG ne nécessitant ni modèle LLM ni base
vectorielle. Ces tests sécurisent le nettoyage documentaire, le chunking et
l'extraction de métadonnées juridiques.
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
REG_RAG_DIR = BACKEND_DIR / "agents" / "conseiller_reglementaire" / "rag"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(REG_RAG_DIR))


class TestAgentContext:
    def test_history_session_and_export(self):
        from shared.core.agent_context import AgentContext

        ctx = AgentContext()
        ctx.add_message("user", "Bonjour", role="user")
        ctx.add_message("bot", "Bonjour, comment puis-je aider ?")
        ctx.set_session_data("app_context", "private")

        assert len(ctx.get_history()) == 2
        assert len(ctx.get_history(last_n=1)) == 1
        assert ctx.get_session_data("app_context") == "private"
        assert ctx.get_session_data("missing", "default") == "default"
        exported = ctx.to_dict()
        assert exported["session_data"]["app_context"] == "private"


class TestSmartChunker:
    def test_detects_sectioned_document(self):
        from shared.rag.smart_chunker import SmartChunker, DocumentFormat

        text = "INTRODUCTION GENERALE\nLe dépositaire central assure ses missions.\n\nSERVICES OFFERTS\nMaroclear fournit plusieurs services."
        assert SmartChunker().detect_format(text) == DocumentFormat.SECTIONED

    def test_chunk_narrative_adds_metadata(self):
        from shared.rag.smart_chunker import SmartChunker, DocumentFormat

        text = "Phrase un. Phrase deux. Phrase trois. Phrase quatre."
        chunks = SmartChunker().chunk(
            text,
            source="test.pdf",
            force_format=DocumentFormat.NARRATIVE,
            chunk_size=28,
            overlap=2,
        )

        assert len(chunks) >= 2
        assert all(chunk["metadata"]["source"] == "test.pdf" for chunk in chunks)
        assert all(chunk["metadata"]["format"] == "narrative" for chunk in chunks)

    def test_chunk_glossary_colon_normalized_as_narrative(self):
        from shared.rag.smart_chunker import SmartChunker, DocumentFormat

        text = "Affilié: Participant admis aux services de Maroclear.\nTitre: Valeur mobilière inscrite en compte."
        chunks = SmartChunker().chunk(
            text,
            source="glossaire.pdf",
            force_format=DocumentFormat.GLOSSARY_COLON,
        )

        assert len(chunks) == 2
        assert chunks[0]["metadata"]["type"] == "narrative"
        assert "Affilié" in chunks[0]["content"]


class TestDocumentCleaner:
    def test_normalizes_ligatures_apostrophes_and_noise(self):
        from document_cleaner import DocumentCleaner

        cleaner = DocumentCleaner(
            footer_patterns=[r"^Maroclear - Document interne$"],
            header_patterns=[r"^CONFIDENTIEL$"],
        )
        raw = "CONFIDENTIEL\nﬁnancier d\u2019un aNilié\nPage 1 sur 3\nMaroclear - Document interne\n---"

        cleaned = cleaner.clean_text(raw)

        assert "financier d'un affilié" in cleaned
        assert "CONFIDENTIEL" not in cleaned
        assert "Page 1 sur 3" not in cleaned

    def test_detect_language_fr_and_en(self):
        from document_cleaner import DocumentCleaner

        cleaner = DocumentCleaner([], [])
        assert cleaner.detect_language("Article chapitre dahir règlement société dépositaire conformément à la loi") == "fr"
        assert cleaner.detect_language("Chapter regulation shall provisions accordance pursuant thereof") == "en"


class TestMetadataExtractor:
    def test_extract_article_number_variants(self):
        from metadata_extractor import MetadataExtractor

        assert MetadataExtractor.extract_article_number("Article premier : champ") == "Article premier"
        assert MetadataExtractor.extract_article_number("Article 8 - 1 : contrôle") == "Article 8-1"
        assert MetadataExtractor.extract_article_number("Art. 19 précise") == "Article 19"

    def test_detect_links_ranges_lists_and_self_reference(self):
        from metadata_extractor import MetadataExtractor

        text = (
            "Conformément au 2è alinéa de l'article 8 -1, aux articles 19, 20 et 21, "
            "et aux articles 30 à 32 du présent article."
        )
        links = MetadataExtractor.detect_links(text, current_article_id="article 8-1")

        assert "article 8-1" in links
        assert "article 19" in links
        assert "article 20" in links
        assert "article 21" in links
        assert "article 30" in links
        assert "article 31" in links
        assert "article 32" in links

    def test_extract_regulatory_metadata(self):
        from metadata_extractor import MetadataExtractor, DocumentCategorizer

        assert MetadataExtractor.extract_rule_id_dnssi("ACTIF-SUP-AMOV: règle") == "ACTIF-SUP-AMOV"
        assert MetadataExtractor.extract_consideration_pfmi("Considération essentielle CE 11.4") == "CE 11.4"
        assert MetadataExtractor.extract_annexe_reference("ANNEXE I.4.A") == "ANNEXE I.4.A"
        assert MetadataExtractor.extract_section("Section 2 : Modalités") == "Section 2 : Modalités"
        assert MetadataExtractor.extract_titre("TITRE I : DISPOSITIONS") == "TITRE I : DISPOSITIONS"
        assert MetadataExtractor.extract_chapter("CHAPITRE II : CONTROLE") == "CHAPITRE II : CONTROLE"
        assert MetadataExtractor.has_mathematical_formula("M_i = A \\times B")

        categorizer = DocumentCategorizer({"CATEGORY_A": ["loi"], "CATEGORY_B": ["dnssi"]})
        assert categorizer.categorize("loi_35_96.pdf") == "CATEGORY_A"
        assert categorizer.categorize("rapport_annuel.pdf") == "CATEGORY_D_RAPPORTS"
