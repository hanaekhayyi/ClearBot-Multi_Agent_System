"""
Pipeline principal de chunking RAG - VERSION CORRIGÉE
====================================

Corrections apportées:
1. ✓ _map_lois_structure() : UNE SEULE PASSE TRIÉE au lieu de 4 boucles séparées
2. ✓ Suppression totale du context_map stateful (source d'incohérences)
3. ✓ ChunkMetadata simplifié : title/chapter/section canoniques (suppression titre/chapitre)
4. ✓ Pattern TITRE strict avec validation anti-faux-positifs
5. ✓ CategoryAChunker : détection et split des annexes mixtes
6. ✓ Bug CategoryCChunker.chunk() : utilisait article_text au lieu de annexe_chunk
7. ✓ Bug detect_links() appelé AVANT la boucle → déplacé dans la boucle
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.documents.elements import Table, ListItem
except ImportError:
    print("ATTENTION: Installez: pip install unstructured[pdf] --break-system-packages")

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    import tiktoken
except ImportError as e:
    print(f"ATTENTION: Installez: pip install langchain tiktoken --break-system-packages")
    print(f"Erreur: {e}")

from document_cleaner import DocumentCleaner
from metadata_extractor import MetadataExtractor, DocumentCategorizer

logger = logging.getLogger(__name__)


@dataclass
class ChunkMetadata:
    """Métadonnées enrichies d'un chunk - VERSION SIMPLIFIÉE"""
    source: str
    category: str
    section_title: Optional[str] = None
    reference_id: Optional[str] = None
    rule_id: Optional[str] = None
    # Hiérarchie canonique (avec titres complets)
    title: Optional[str] = None      # Ex: "TITRE I : LES PRINCIPES..."
    chapter: Optional[str] = None    # Ex: "Chapitre III : Le fonctionnement..."
    section: Optional[str] = None    # Ex: "Section 1 : Les principes généraux"
    article_id: Optional[str] = None
    links_to: List[str] = None
    language: str = "fr"
    chunk_type: str = "text"

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class ImprovedTokenizer:
    """Tokenizer précis utilisant tiktoken"""

    def __init__(self, encoding_name: str = "o200k_base"):
        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
            logger.info(f"✓ Tiktoken {encoding_name} chargé avec succès")
        except Exception as e:
            self.encoding = None
            logger.warning(f"Tiktoken non disponible ({type(e).__name__}: {e}), utilisation approximation")

    def count_tokens(self, text: str) -> int:
        if self.encoding:
            return len(self.encoding.encode(text))
        return int(len(text) / 3.5)


class DocumentPreprocessor:
    """
    Prétraite les documents AVANT le chunking.
    Extrait la structure hiérarchique complète (Titre > Chapitre > Section > Article).
    VERSION CORRIGÉE : UNE SEULE PASSE TRIÉE
    """

    def __init__(self):
        self.structure_map = {}

    def build_structure_map(self, text: str, category: str) -> Dict[int, Dict]:
        if category == 'CATEGORY_A_LOIS':
            return self._map_lois_structure(text)
        elif category == 'CATEGORY_B_DIRECTIVES':
            return self._map_directives_structure(text)
        elif category == 'CATEGORY_C_ANNEXES':
            return self._map_annexes_structure(text)
        return {}

    @staticmethod
    def _is_valid_title_name(title_name: str) -> bool:
        """Valide qu'un titre n'est pas du corps de texte mal matché"""
        if not title_name or len(title_name) > 120:
            return False
        
        # Rejeter si contient des mots typiques du corps de texte
        false_positive_keywords = [
            'loi n°', 'précitée', 'article', 'dispose', 
            'modifié', 'complété', 'conformément', 'notamment'
        ]
        title_lower = title_name.lower()
        return not any(keyword in title_lower for keyword in false_positive_keywords)

    def _map_lois_structure(self, text: str) -> Dict:
        """
        CORRECTION MAJEURE : UNE SEULE PASSE TRIÉE PAR POSITION
        Au lieu de 4 boucles séparées qui perdent le contexte
        """
        structure = {}
        matches = []
        
        # Collecte de TOUS les éléments structurels avec leur position
        
        # TITRES - Pattern flexible : accepte avec ou sans deux-points
        # Format 1 : "TITRE I : LES PRINCIPES..."
        # Format 2 : "TITRE II\nDE L'INSCRIPTION..." ou "TITRE II DE L'INSCRIPTION..."
        for match in re.finditer(
            r'(?:^|\n)(TITRE\s+(?:PREMIER|[IVX]+))(?:\s*[:\-]\s*([^\n]+)|(?:\s+|\n)([^\n]+))?',
            text, re.IGNORECASE | re.MULTILINE
        ):
            title = match.group(1).strip()
            # L'intitulé peut être dans group(2) (format avec :) ou group(3) (format sans :)
            title_name = (match.group(2) or match.group(3) or "").strip()
            
            # Si title_name est vide ou trop court, chercher la ligne suivante
            if not title_name or len(title_name) < 5:
                # Chercher le texte après le titre sur les 2 lignes suivantes
                pos_after_title = match.end()
                next_lines = text[pos_after_title:pos_after_title+200].split('\n')[:2]
                for line in next_lines:
                    line_clean = line.strip()
                    if line_clean and len(line_clean) > 5 and not line_clean.startswith('Article'):
                        title_name = line_clean
                        break
            
            if self._is_valid_title_name(title_name):
                matches.append({
                    'pos': match.start(),
                    'type': 'title',
                    'title': title,
                    'title_name': title_name
                })

        # CHAPITRES - Pattern flexible : gère retours à la ligne
        # Format 1 : "Chapitre I : Les principes..."
        # Format 2 : "Chapitre\npremier :\nDISPOSITIONS..." (multi-lignes)
        for match in re.finditer(
            r'(?:^|\n)(Chapitre)\s+(?:PREMIER|[IVX]+|\d+)',
            text, re.IGNORECASE | re.MULTILINE
        ):
            # Extraire le numéro qui peut être juste après ou sur la ligne suivante
            pos_start = match.start()
            pos_end = match.end()
            
            # Chercher le numéro/label du chapitre
            chapter_num_match = re.search(
                r'Chapitre\s+(PREMIER|[IVX]+|\d+)',
                text[pos_start:pos_start+100],
                re.IGNORECASE
            )
            
            if not chapter_num_match:
                continue
                
            chapter_num = chapter_num_match.group(1).strip()
            chapter_label = f"Chapitre {chapter_num}"
            
            # Chercher le titre après le numéro (peut être sur ligne suivante)
            after_num = pos_start + chapter_num_match.end()
            title_match = re.search(
                r'[\:\-\.\–\—]\s*([^\n]+)',
                text[after_num:after_num+200]
            )
            
            chapter_name = ""
            if title_match:
                chapter_name = title_match.group(1).strip()
            else:
                # Fallback : chercher sur les 2 lignes suivantes
                next_lines = text[after_num:after_num+200].split('\n')[:3]
                for line in next_lines:
                    line_clean = line.strip()
                    if line_clean and len(line_clean) > 5 and not line_clean.startswith('Article'):
                        chapter_name = line_clean
                        break
            
            if chapter_name and len(chapter_name) < 250:
                matches.append({
                    'pos': pos_start,
                    'type': 'chapter',
                    'chapter': chapter_label,
                    'chapter_name': chapter_name
                })

        # SECTIONS - Pattern flexible : accepte :, -, ., –, — comme séparateurs
        # Format 1 : "Section 1 : Les principes..."
        # Format 2 : "Section 2. – Qualité des données..." (point + tiret cadratin)
        for match in re.finditer(
            r'(?:^|\n)(Section\s+(?:\d+|[IVX]+|première?))\s*[\:\-\.\–\—]\s*([^\n]+)',
            text, re.IGNORECASE | re.MULTILINE
        ):
            section_name = match.group(2).strip()
            if section_name and len(section_name) < 250:  # Augmenté pour capturer les sections à long intitulé
                matches.append({
                    'pos': match.start(),
                    'type': 'section',
                    'section': match.group(1).strip(),
                    'section_name': section_name
                })

        # ARTICLES
        for match in re.finditer(
            r'(?:^|\n)Article\s+(?:premier|\d+(?:\s*[-–]\s*\d+)?(?:\s+(?:bis|ter|quater))?)\s*:',
            text, re.IGNORECASE | re.MULTILINE
        ):
            article_label = MetadataExtractor.extract_article_number(match.group(0)) or "Article ?"
            matches.append({
                'pos': match.start(),
                'type': 'article',
                'article': article_label
            })

        # TRI PAR POSITION : clé de la correction
        matches.sort(key=lambda m: m['pos'])

        # CONSTRUCTION DE LA STRUCTURE AVEC CONTEXTE MAINTENU
        current_title = None
        current_title_full = None
        current_chapter = None
        current_chapter_full = None
        current_section = None
        current_section_full = None

        for item in matches:
            pos = item['pos']
            item_type = item['type']

            if item_type == 'title':
                # Reset cascade : nouveau titre → reset tout
                current_title = item['title']
                title_name = item['title_name']
                current_title_full = f"{current_title} : {title_name}" if title_name else current_title
                current_chapter = None
                current_chapter_full = None
                current_section = None
                current_section_full = None
                
                structure[pos] = {
                    'type': 'title',
                    'title': current_title,
                    'title_name': title_name,
                    'title_full': current_title_full
                }

            elif item_type == 'chapter':
                # Reset sections sous ce chapitre
                current_chapter = item['chapter']
                chapter_name = item['chapter_name']
                current_chapter_full = f"{current_chapter} : {chapter_name}" if chapter_name else current_chapter
                current_section = None
                current_section_full = None
                
                structure[pos] = {
                    'type': 'chapter',
                    'chapter': current_chapter,
                    'chapter_name': chapter_name,
                    'chapter_full': current_chapter_full,
                    'parent_title': current_title,
                    'parent_title_full': current_title_full
                }

            elif item_type == 'section':
                current_section = item['section']
                section_name = item['section_name']
                current_section_full = f"{current_section} : {section_name}" if section_name else current_section
                
                structure[pos] = {
                    'type': 'section',
                    'section': current_section,
                    'section_name': section_name,
                    'section_full': current_section_full,
                    'parent_chapter': current_chapter,
                    'parent_chapter_full': current_chapter_full,
                    'parent_title': current_title,
                    'parent_title_full': current_title_full
                }

            elif item_type == 'article':
                structure[pos] = {
                    'type': 'article',
                    'article': item['article'],
                    'parent_section': current_section,
                    'parent_section_full': current_section_full,
                    'parent_chapter': current_chapter,
                    'parent_chapter_full': current_chapter_full,
                    'parent_title': current_title,
                    'parent_title_full': current_title_full
                }

        return structure

    def _map_directives_structure(self, text: str) -> Dict:
        """Mappe la structure des directives (DNSSI, PFMI)."""
        structure = {}

        # DNSSI: codes de règles (ex: ACTIF-SUP-AMOV)
        for match in re.finditer(r'\n([A-Z]{3,}(?:-[A-Z]{3,}){1,3})\s*:\s*([^\n]+)', text):
            pos = match.start()
            structure[pos] = {
                'type': 'rule',
                'rule_id': match.group(1),
                'rule_title': match.group(2).strip()
            }

        # PFMI: considérations essentielles (ex: 11.4)
        for match in re.finditer(r'\nConsidération\s+essentielle\s+(\d+\.\d+)', text, re.IGNORECASE):
            pos = match.start()
            structure[pos] = {
                'type': 'consideration',
                'consideration': f"CE {match.group(1)}"
            }

        return structure

    def _map_annexes_structure(self, text: str) -> Dict:
        """Mappe la structure des annexes."""
        structure = {}

        for match in re.finditer(
            r'\n(ANNEXE\s+[IVX]+\.?\d*(?:\.[A-Z])?)\s*[:\-]?\s*([^\n]*)',
            text, re.IGNORECASE
        ):
            pos = match.start()
            structure[pos] = {
                'type': 'annexe',
                'annexe': match.group(1).strip(),
                'annexe_title': match.group(2).strip()
            }

        return structure

    def get_context_at_position(self, position: int, structure_map: Dict) -> Dict:
        """Récupère le contexte hiérarchique à une position donnée"""
        context = {
            'title': None,
            'title_full': None,
            'chapter': None,
            'chapter_full': None,
            'section': None,
            'section_full': None,
            'article': None,
            'rule_id': None,
        }

        relevant_positions = sorted(
            [pos for pos in structure_map if pos <= position],
            reverse=True
        )

        for pos in relevant_positions:
            element = structure_map[pos]
            etype = element.get('type')

            if etype == 'title' and not context['title']:
                context['title'] = element.get('title')
                context['title_full'] = element.get('title_full')
            elif etype == 'chapter' and not context['chapter']:
                context['chapter'] = element.get('chapter')
                context['chapter_full'] = element.get('chapter_full')
            elif etype == 'section' and not context['section']:
                context['section'] = element.get('section')
                context['section_full'] = element.get('section_full')
            elif etype == 'article' and not context['article']:
                context['article'] = element.get('article')
            elif etype == 'rule' and not context['rule_id']:
                context['rule_id'] = element.get('rule_id')

        return context


class ProtectedBlockDetector:
    """Détecte les blocs qui ne doivent jamais être coupés."""

    @staticmethod
    def detect_formula_block(text: str) -> List[Tuple[int, int]]:
        blocks = []
        math_patterns = [r'\$[^$]+\$', r'\\sum', r'\\frac\{[^}]+\}\{[^}]+\}', r'M_i', r'P\s*=\s*']
        for pattern in math_patterns:
            for match in re.finditer(pattern, text):
                start = text.rfind('\n\n', 0, match.start())
                end = text.find('\n\n', match.end())
                blocks.append((0 if start == -1 else start, len(text) if end == -1 else end))
        return blocks

    @staticmethod
    def detect_table_block(elements: List) -> List[Tuple[int, int, str]]:
        return [(i, i, str(e)) for i, e in enumerate(elements) if isinstance(e, Table)]

    @staticmethod
    def is_position_in_protected_block(position: int, blocks: List[Tuple[int, int]]) -> bool:
        return any(start <= position <= end for start, end in blocks)


class CategoryCChunker:
    """
    Chunker pour Catégorie C: Annexes.
    Hard split atomique par ANNEXE, sans remplissage.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int, tokenizer: ImprovedTokenizer):
        self.chunk_size = chunk_size
        self.chunk_overlap = 0
        self.tokenizer = tokenizer
        self.min_chunk_length = 20

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=0,
            length_function=tokenizer.count_tokens,
            separators=[
                "<!-- TABLE_END -->",
                "\nANNEXE",
                "\nArticle",
                "\n\n## ",
                "\n\n# ",
                "\n\n",
                "\n-",
                "\n",
                ". ",
                " ",
                ""
            ]
        )

    def _hard_split_by_annexes_atomic(self, text: str) -> List[Tuple[str, str, int]]:
        annexes = []
        pattern = r'(?:^|\n)(?:ANNEXE|Annexe)\s+(?:AU\s+REGLEMENT\s+GENERAL|([IVX]+\.?\d+(?:\.[A-Z])?)|(\d+)(?:\s*[-–]\s*(\d+))?)\s*:?'
        matches = sorted(re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE), key=lambda m: m.start())

        if not matches:
            if len(text.strip()) >= self.min_chunk_length:
                annexes.append((text, "INTRO", 0))
            return annexes

        if matches[0].start() > 0:
            intro_text = text[:matches[0].start()]
            if len(intro_text.strip()) >= self.min_chunk_length:
                annexes.append((intro_text, "INTRO", 0))

        for i, match in enumerate(matches):
            match_text = match.group(0)
            annexe_label = "ANNEXE ?"

            # Détecter "ANNEXE AU REGLEMENT GENERAL"
            if "AU REGLEMENT" in match_text.upper():
                annexe_label = "ANNEXE AU REGLEMENT GENERAL"
            else:
                # Autres formats d'annexes
                annexe_num_pattern = r'(?:ANNEXE|Annexe)\s+((?:[IVX]+\.?\d+(?:\.[A-Z])?)|(?:\d+(?:\s*[-–]\s*\d+)?))'
                annexe_match = re.search(annexe_num_pattern, match_text, re.IGNORECASE)
                if annexe_match:
                    annexe_label = f"ANNEXE {annexe_match.group(1).strip()}"

            annexe_start = match.start()
            annexe_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            annexe_text = text[annexe_start:annexe_end].rstrip()

            if len(annexe_text.strip()) >= self.min_chunk_length:
                annexes.append((annexe_text, annexe_label, annexe_start))

        return annexes

    def _respect_table_boundaries(self, text: str, max_tokens: int) -> List[str]:
        """Découpe le texte en respectant les balises TABLE_START/TABLE_END."""
        chunks = []
        current_pos = 0

        while current_pos < len(text):
            table_start = text.find('<!-- TABLE_START -->', current_pos)

            if table_start == -1:
                remaining = text[current_pos:]
                if len(remaining.strip()) >= self.min_chunk_length:
                    chunks.append(remaining)
                break

            before_table = text[current_pos:table_start]
            if len(before_table.strip()) >= self.min_chunk_length:
                chunks.append(before_table)

            table_end_marker = '<!-- TABLE_END -->'
            table_end = text.find(table_end_marker, table_start)

            if table_end > table_start:
                table_with_markers = text[table_start:table_end + len(table_end_marker)]
                chunks.append(table_with_markers)
                current_pos = table_end + len(table_end_marker)
            else:
                chunks.append(text[table_start:])
                break

        return chunks

    def _is_list_section(self, text: str) -> bool:
        """Détecte si la section est principalement une liste/formulaire."""
        list_markers = [r'^\s*[-•*]\s', r'^\s*\d+\.\s', r'\[x?\]', r'Formulaire|Form|Liste']
        text_sample = text[:500]
        matches = sum(len(re.findall(marker, text_sample, re.MULTILINE)) for marker in list_markers)
        return matches >= 3

    def chunk(self, text: str, source: str, language: str,
              preprocessor: DocumentPreprocessor) -> List[Document]:
        """
        Hard split par annexes avec contexte hiérarchique.
        Chaque annexe = chunk indépendant.
        Respecte les balises TABLE_START/TABLE_END.
        CORRIGÉ : plus de context_map
        """
        chunks = []
        structure_map = preprocessor.build_structure_map(text, 'CATEGORY_C_ANNEXES')
        annexe_segments = self._hard_split_by_annexes_atomic(text)

        for annexe_text, annexe_ref, position in annexe_segments:
            if len(annexe_text.strip()) < self.min_chunk_length:
                continue

            context = preprocessor.get_context_at_position(position, structure_map)
            chunk_type = 'list' if self._is_list_section(annexe_text) else 'text'
            token_count = self.tokenizer.count_tokens(annexe_text)

            if token_count <= 600:
                metadata = ChunkMetadata(
                    source=source,
                    category='CATEGORY_C_ANNEXES',
                    reference_id=annexe_ref,
                    language=language,
                    chunk_type=chunk_type,
                    section=context.get('section_full') or context.get('section')
                )
                chunks.append(Document(page_content=annexe_text, metadata=metadata.to_dict()))
            else:
                # CORRIGÉ: on utilise annexe_text, annexe_ref et annexe_chunk
                annexe_sub_chunks = self._respect_table_boundaries(annexe_text, 600)
                for annexe_chunk in annexe_sub_chunks:
                    if len(annexe_chunk.strip()) < self.min_chunk_length:
                        continue
                    metadata = ChunkMetadata(
                        source=source,
                        category='CATEGORY_C_ANNEXES',
                        reference_id=annexe_ref,
                        language=language,
                        chunk_type=chunk_type,
                        section=context.get('section_full') or context.get('section')
                    )
                    chunks.append(Document(page_content=annexe_chunk, metadata=metadata.to_dict()))

        return chunks


class CategoryAChunker:
    """
    Chunker pour Catégorie A: Lois et Dahirs.
    Hard split atomique par article (regex), sans remplissage.
    VERSION CORRIGÉE : détection et split des annexes mixtes
    """

    def __init__(self, chunk_size: int, chunk_overlap: int, tokenizer: ImprovedTokenizer):
        self.chunk_size = chunk_size
        self.chunk_overlap = 0
        self.tokenizer = tokenizer
        self.min_chunk_length = 20

        self.emergency_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=0,
            length_function=tokenizer.count_tokens,
            separators=["\nArticle", "\n\n", "\n-", "\n", ". ", " ", ""]
        )

    @staticmethod
    def _normalize_article_boundaries(text: str) -> str:
        """
        Force un saut de ligne avant chaque occurrence de 'Article N :'
        qui apparaît en milieu de texte (après un point ou espace).
        Garantit que le split par article fonctionne même sur les PDF
        dont le texte est extrait sans retours à la ligne.
        """
        return re.sub(
            r'(?<!\n)(Article\s+(?:\d+(?:\s*[-–]\s*\d+)?|premier|1(?:er)?)\s*(?:bis|ter|quater)?\s*:)',
            r'\n\1',
            text
        )

    def _split_loi_and_annexes(self, text: str) -> Tuple[str, Optional[str]]:
        """
        NOUVEAU : Détecte et sépare les annexes du corps de loi.
        Retourne (texte_loi, texte_annexes)
        """
        annexe_pattern = r'\n(ANNEXE\s+AU\s+REGLEMENT\s+GENERAL|ANNEXE\s+[IVX]+)'
        match = re.search(annexe_pattern, text, re.IGNORECASE)
        
        if match:
            split_pos = match.start()
            loi_text = text[:split_pos].rstrip()
            annexe_text = text[split_pos:].strip()
            logger.info(f"  → Détection annexe à position {split_pos}")
            return loi_text, annexe_text
        
        return text, None

    def _hard_split_by_articles_atomic(self, text: str) -> List[Tuple[str, str, int]]:
        """
        Split le texte par articles.
        Supporte: Article 1, Article 1er, Article premier, Article 8-1, Article 5 bis.
        FORMAT FLEXIBLE : avec ou sans deux-points
        - "Article 1 : Le dépositaire..."
        - "Article 2\n1- La présente loi..."
        """
        articles = []
        # Pattern flexible : deux-points optionnel
        # Détecte aussi les articles après un point milieu de ligne
        pattern = r'(?:^|\n|(?<=\.\s))(?:Article|Art\.)\s+(?:(\d+)(?:\s*[-–]\s*(\d+))?|premier|1(?:er)?)\s*(?:bis|ter|quater)?\s*:?'
        matches = sorted(re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE), key=lambda m: m.start())

        if not matches:
            if len(text.strip()) >= self.min_chunk_length:
                articles.append((text, "PREAMBLE", 0))
            return articles

        # Préambule avant le premier article
        if matches[0].start() > 0:
            pre_text = text[:matches[0].start()]
            if len(pre_text.strip()) >= self.min_chunk_length:
                articles.append((pre_text, "PREAMBLE", 0))

        for i, match in enumerate(matches):
            match_text = match.group(0).strip()
            article_label = "Article ?"

            # Extraire le numéro/label de l'article
            article_num_pattern = r'(?:Article|Art\.)\s+(?:(premier|1(?:er)?)|(\d+)(?:\s*[-–]\s*(\d+))?)\s*(?:bis|ter|quater)?'
            article_match = re.search(article_num_pattern, match_text, re.IGNORECASE)
            if article_match:
                if article_match.group(1):  # "premier" ou "1er"
                    article_label = "Article premier"
                elif article_match.group(3):  # Article avec tiret (ex: 8-1)
                    article_label = f"Article {article_match.group(2)}-{article_match.group(3)}"
                elif article_match.group(2):  # Article simple (ex: 2)
                    article_label = f"Article {article_match.group(2)}"
            
            # Vérifier si "bis", "ter", "quater" suit
            if re.search(r'\s+(bis|ter|quater)\s*:?$', match_text, re.IGNORECASE):
                modifier = re.search(r'\s+(bis|ter|quater)', match_text, re.IGNORECASE).group(1)
                article_label = f"{article_label} {modifier}"

            article_start = match.start()
            article_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            article_text = text[article_start:article_end].rstrip()

            if len(article_text.strip()) >= self.min_chunk_length:
                articles.append((article_text, article_label, article_start))

        return articles

    def chunk(self, text: str, source: str, language: str,
              preprocessor: DocumentPreprocessor) -> List[Document]:
        """
        Chunking Catégorie A avec contexte hiérarchique (titre, chapitre, section).
        CORRECTION : plus de context_map, uniquement structure_map
        """
        chunks = []
        
        # NOUVEAU : détecter et séparer les annexes
        loi_text, annexe_text = self._split_loi_and_annexes(text)
        
        # Traiter la partie loi
        structure_map = preprocessor.build_structure_map(loi_text, 'CATEGORY_A_LOIS')
        loi_text = self._normalize_article_boundaries(loi_text)
        article_segments = self._hard_split_by_articles_atomic(loi_text)

        for article_text, article_label, position in article_segments:
            if len(article_text.strip()) < self.min_chunk_length:
                continue

            context = preprocessor.get_context_at_position(position, structure_map)

            # Affiner le label avec l'extracteur
            extracted_article = MetadataExtractor.extract_article_number(article_text)
            if extracted_article:
                article_label = extracted_article

            # CORRIGÉ: detect_links appelé ICI dans la boucle, sur article_text courant
            links = MetadataExtractor.detect_links(article_text)
            # Supprimer l'auto-référence : l'article ne doit pas se lister lui-même
            if article_label:
                self_num = re.search(r'\d+[\d\-]*', article_label)
                if self_num:
                    self_ref = f"article {self_num.group()}"
                    links = [l for l in links if l.lower() != self_ref.lower()]

            token_count = self.tokenizer.count_tokens(article_text)

            if token_count <= 600:
                metadata = ChunkMetadata(
                    source=source,
                    category='CATEGORY_A_LOIS',
                    language=language,
                    reference_id=article_label,
                    title=context.get('title_full') or context.get('title'),
                    chapter=context.get('chapter_full') or context.get('chapter'),
                    section=context.get('section_full') or context.get('section'),
                    chunk_type='text',
                    links_to=links if links else None
                )
                chunks.append(Document(page_content=article_text, metadata=metadata.to_dict()))
            else:
                # Fallback: article trop long
                article_chunks = self.emergency_splitter.split_text(article_text)
                for article_chunk in article_chunks:
                    if len(article_chunk.strip()) < self.min_chunk_length:
                        continue
                    sub_links = MetadataExtractor.detect_links(article_chunk)
                    # Supprimer l'auto-référence
                    if article_label:
                        self_num = re.search(r'\d+[\d\-]*', article_label)
                        if self_num:
                            self_ref = f"article {self_num.group()}"
                            sub_links = [l for l in sub_links if l.lower() != self_ref.lower()]
                    metadata = ChunkMetadata(
                        source=source,
                        category='CATEGORY_A_LOIS',
                        language=language,
                        reference_id=article_label,
                        title=context.get('title_full') or context.get('title'),
                        chapter=context.get('chapter_full') or context.get('chapter'),
                        section=context.get('section_full') or context.get('section'),
                        chunk_type='text',
                        links_to=sub_links if sub_links else None
                    )
                    chunks.append(Document(page_content=article_chunk, metadata=metadata.to_dict()))

        # NOUVEAU : Traiter les annexes séparément si présentes
        if annexe_text:
            logger.info(f"  → Chunking des annexes ({len(annexe_text)} chars)")
            # Utiliser CategoryCChunker pour les annexes (classe définie plus haut dans le fichier)
            annexe_chunker = CategoryCChunker(self.chunk_size, self.chunk_overlap, self.tokenizer)
            annexe_chunks = annexe_chunker.chunk(
                annexe_text, 
                source, 
                language, 
                preprocessor
            )
            chunks.extend(annexe_chunks)

        return chunks


class CategoryBChunker:
    """
    Chunker pour Catégorie B: Directives (DNSSI, PFMI).
    Découpage par règles/considérations avec leurs codes.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int, tokenizer: ImprovedTokenizer):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tokenizer

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=tokenizer.count_tokens,
            separators=[
                "\nConsidération essentielle ",
                "\nObjectif ",
                "\nArticle",
                "\n\n## ",
                "\n\n# ",
                "\n\n",
                "\n-",
                "\n",
                ". ",
                " ",
                ""
            ]
        )

    def chunk(self, text: str, source: str, language: str,
              preprocessor: DocumentPreprocessor) -> List[Document]:
        """Chunking Catégorie B avec contexte hiérarchique"""
        chunks = []
        is_dnssi = 'DNSSI' in source or 'Directive' in source
        is_pfmi = 'PFMI' in source

        structure_map = preprocessor.build_structure_map(text, 'CATEGORY_B_DIRECTIVES')

        if is_dnssi:
            chunks = self._chunk_dnssi(text, source, language, structure_map, preprocessor)
        elif is_pfmi:
            chunks = self._chunk_pfmi(text, source, language, structure_map, preprocessor)
        else:
            for sub_text in self.text_splitter.split_text(text):
                metadata = ChunkMetadata(source=source, category='CATEGORY_B_DIRECTIVES', language=language)
                chunks.append(Document(page_content=sub_text, metadata=metadata.to_dict()))

        return chunks

    def _chunk_dnssi(self, text: str, source: str, language: str,
                     structure_map: Dict, preprocessor: DocumentPreprocessor) -> List[Document]:
        chunks = []
        matches = list(re.finditer(r'\n([A-Z]{3,}(?:-[A-Z]{3,}){1,3})\s*:\s*([^\n]+)', text))

        for i, match in enumerate(matches):
            rule_id = match.group(1)
            rule_title = match.group(2).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            rule_content = text[start:end].strip()
            context = preprocessor.get_context_at_position(start, structure_map)

            metadata = ChunkMetadata(
                source=source,
                category='CATEGORY_B_DIRECTIVES',
                rule_id=rule_id,
                section_title=rule_title,
                chapter=context.get('chapter_full') or context.get('chapter'),
                language=language
            )

            if self.tokenizer.count_tokens(rule_content) > self.chunk_size:
                for j, sub_chunk in enumerate(self.text_splitter.split_text(rule_content)):
                    sub_meta = metadata.to_dict()
                    sub_meta['reference_id'] = f"{rule_id}_part{j+1}"
                    chunks.append(Document(page_content=sub_chunk, metadata=sub_meta))
            else:
                chunks.append(Document(page_content=rule_content, metadata=metadata.to_dict()))

        return chunks

    def _chunk_pfmi(self, text: str, source: str, language: str,
                    structure_map: Dict, preprocessor: DocumentPreprocessor) -> List[Document]:
        chunks = []
        matches = list(re.finditer(r'(Considération\s+essentielle\s+\d+\.\d+)', text, re.IGNORECASE))

        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            consideration_content = text[start:end].strip()
            consideration_id = MetadataExtractor.extract_consideration_pfmi(match.group(1))

            metadata = ChunkMetadata(
                source=source,
                category='CATEGORY_B_DIRECTIVES',
                reference_id=consideration_id,
                language=language
            )
            chunks.append(Document(page_content=consideration_content, metadata=metadata.to_dict()))

        return chunks


class RAGChunkingPipeline:
    """Pipeline principal de chunking RAG."""

    def __init__(self, config):
        self.config = config
        self.cleaner = DocumentCleaner(
            footer_patterns=config.FOOTER_PATTERNS,
            header_patterns=config.HEADER_PATTERNS
        )
        self.categorizer = DocumentCategorizer(config.CATEGORIES)
        self.tokenizer = ImprovedTokenizer(config.ENCODING_NAME)
        self.preprocessor = DocumentPreprocessor()
        self.block_detector = ProtectedBlockDetector()

        self.chunkers = {
            'CATEGORY_A_LOIS': CategoryAChunker(config.CHUNK_SIZE, config.CHUNK_OVERLAP, self.tokenizer),
            'CATEGORY_B_DIRECTIVES': CategoryBChunker(config.CHUNK_SIZE, config.CHUNK_OVERLAP, self.tokenizer),
            'CATEGORY_C_ANNEXES': CategoryCChunker(config.CHUNK_SIZE, config.CHUNK_OVERLAP, self.tokenizer),
            'CATEGORY_D_RAPPORTS': CategoryAChunker(config.CHUNK_SIZE, config.CHUNK_OVERLAP, self.tokenizer)
        }

    def process_pdf(self, pdf_path: str) -> List[Document]:
        """
        Traite un PDF : extraction → nettoyage → catégorisation → chunking.
        Le titre formel du document est extrait et utilisé comme source
        pour permettre une citation précise dans les réponses du RAG.
        """
        logger.info(f"TRAITEMENT: {Path(pdf_path).name}")
        filename = Path(pdf_path).name

        try:
            logger.info("  - Extraction PDF (hi_res)...")
            elements = partition_pdf(
                filename=pdf_path,
                strategy="fast",
                include_page_breaks=False
            )

            text_parts = []
            for element in elements:
                element_text = str(element)
                if isinstance(element, Table):
                    table_md = self._table_to_markdown(element_text)
                    text_parts.append(f"\n<!-- TABLE_START -->\n{table_md}\n<!-- TABLE_END -->\n")
                elif isinstance(element, ListItem):
                    text_parts.append(f"- {element_text}")
                else:
                    text_parts.append(element_text)

            text = "\n\n".join(text_parts)

            logger.info("  - Nettoyage...")
            text = self.cleaner.clean_text(text)

            language = self.cleaner.detect_language(text)
            category = self.categorizer.categorize(filename)

            # Extraction du titre formel (ex: "DAHIR N° 1-96-246 DU 09 JANVIER 1997...")
            # C'est ce titre qui apparaîtra dans les citations des réponses du RAG.
            doc_title = self._extract_document_title(text, filename)
            logger.info(f"  - Titre : {doc_title[:80]}...")
            logger.info(f"  - Categorie: {category}, Langue: {language}")

            formula_blocks = self.block_detector.detect_formula_block(text)
            if formula_blocks:
                logger.info(f"  - {len(formula_blocks)} formules détectées (protégées)")

            logger.info("  - Chunking intelligent...")
            chunker = self.chunkers[category]
            # doc_title remplace filename comme source : les chunks auront le vrai titre du document
            chunks = chunker.chunk(text, doc_title, language, self.preprocessor)

            logger.info(f"  OK {len(chunks)} chunks créés")
            return chunks

        except Exception as e:
            logger.error(f"  ERREUR: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _table_to_markdown(self, table_text: str) -> str:
        return table_text

    def process_directory(self, directory_path: str, output_path: str = None) -> List[Document]:
        directory = Path(directory_path)
        pdf_files = list(directory.glob("*.pdf"))

        logger.info(f"\nDEBUT Traitement de {len(pdf_files)} fichiers")
        logger.info("=" * 80)

        all_chunks = []
        for pdf_file in pdf_files:
            chunks = self.process_pdf(str(pdf_file))
            all_chunks.extend(chunks)

        logger.info("\n" + "=" * 80)
        logger.info(f"OK Total: {len(all_chunks)} chunks")

        if output_path:
            self.save_chunks(all_chunks, output_path)

        return all_chunks

    def save_chunks(self, chunks: List[Document], output_path: str):
        """
        Sauvegarde les chunks en JSON.
        Les IDs sont construits à partir du nom du fichier source pour
        garantir l'unicité même lors de traitements multi-documents.
        Format : chunk_<stem_du_fichier>_<index>
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Compteur par source pour construire des IDs uniques
        source_counters = {}
        chunks_data = []

        for chunk in chunks:
            # Utiliser le nom du PDF source comme préfixe d'ID
            raw_source = chunk.metadata.get('source', 'unknown')
            # Extraire un identifiant court depuis le titre ou le nom de fichier
            source_key = re.sub(r'[^a-zA-Z0-9]', '_', raw_source[:40]).strip('_').lower()
            source_counters[source_key] = source_counters.get(source_key, 0)

            chunk_id = f"chunk_{source_key}_{source_counters[source_key]:06d}"
            source_counters[source_key] += 1

            chunks_data.append({
                'id':          chunk_id,
                'content':     chunk.page_content,
                'metadata':    chunk.metadata,
                'token_count': self.tokenizer.count_tokens(chunk.page_content)
            })

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)

        logger.info(f"SAUVEGARDE: {output_file}")
        self._print_stats(chunks)
    def _print_stats(self, chunks: List[Document]):
        print("\n" + "=" * 80)
        print("STATISTIQUES")
        print("=" * 80)

        if not chunks:
            print("\nAUCUN CHUNK - Vérifiez Poppler")
            return

        categories = {}
        for chunk in chunks:
            cat = chunk.metadata.get('category', 'UNKNOWN')
            categories[cat] = categories.get(cat, 0) + 1

        print("\nPar catégorie:")
        for cat, count in sorted(categories.items()):
            print(f"  - {cat}: {count} chunks")

        with_ref = sum(1 for c in chunks if c.metadata.get('reference_id'))
        print(f"\nAvec reference_id: {with_ref}/{len(chunks)} ({with_ref/len(chunks)*100:.1f}%)")

        with_title = sum(1 for c in chunks if c.metadata.get('title'))
        print(f"Avec title:        {with_title}/{len(chunks)} ({with_title/len(chunks)*100:.1f}%)")

        with_chapter = sum(1 for c in chunks if c.metadata.get('chapter'))
        print(f"Avec chapter:      {with_chapter}/{len(chunks)} ({with_chapter/len(chunks)*100:.1f}%)")

        with_section = sum(1 for c in chunks if c.metadata.get('section'))
        print(f"Avec section:      {with_section}/{len(chunks)} ({with_section/len(chunks)*100:.1f}%)")

        with_links = sum(1 for c in chunks if c.metadata.get('links_to'))
        print(f"Avec links_to:     {with_links}/{len(chunks)} ({with_links/len(chunks)*100:.1f}%)")

        with_rule = sum(1 for c in chunks if c.metadata.get('rule_id'))
        if with_rule:
            print(f"Avec rule_id (DNSSI): {with_rule}")

        avg_length = sum(len(c.page_content) for c in chunks) / len(chunks)
        print(f"\nLongueur moyenne: {avg_length:.0f} caractères")
        print("=" * 80 + "\n")
    @staticmethod
    def _extract_document_title(text: str, filename: str) -> str:
        """
        Extrait le titre formel du document depuis les premières lignes du texte.
        Les documents juridiques marocains débutent toujours par leur intitulé
        complet en majuscules avant le premier article.
        Retourne le nom de fichier (sans extension) si aucun titre n'est trouvé.
        """
        title_lines = []
        for line in text[:2000].split('\n'):
            line = line.strip()
            if not line or len(line) < 10:
                continue
            # Arrêt dès qu'on atteint le corps du document
            if re.match(r'^(Article|LOUANGE|Que l\'on sache|Vu la Constitution)', line, re.IGNORECASE):
                break
            title_lines.append(line)
            if len(title_lines) >= 6:
                break

        if title_lines:
            return ' '.join(title_lines)
        return Path(filename).stem    