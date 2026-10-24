"""
Agent RAG principal - Répond aux questions métier sur Maroclear
"""

from typing import Dict, Any, List
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.base.base_agent import BaseAgent
from shared.core.message import AgentMessage, MessageType
from shared.core.agent_context import AgentContext
from shared.rag.retriever import Retriever
from shared.llm.ollama_client import OllamaClient
from shared.security import minimize_text_for_llm


class RAGAgent(BaseAgent):
    """Agent de questions/réponses basé sur RAG"""

    def __init__(self, config: Dict[str, Any], retriever: Retriever, llm_client: OllamaClient):
        super().__init__(agent_name="RAG_Agent", config=config)
        self.retriever  = retriever
        self.llm_client = llm_client
        self.log("Agent RAG initialisé")

    # =========================================================
    # ROUTING
    # =========================================================

    def can_handle(self, message: AgentMessage, context: AgentContext) -> bool:
        query_lower = message.content.lower()

        # Ne PAS intercepter les messages clairement orientés support/classification
        support_signals = [
            "bloque", "erreur", "panne", "bug", "impossible",
            "ne fonctionne pas", "ne marche pas", "indisponible",
            "pas recu", "non recu", "facture", "reclamation",
            "reinitialisation", "mot de passe", "token",
            "batch en cours", "pending",
        ]
        if any(kw in query_lower for kw in support_signals):
            return False

        rag_keywords = [
            "c'est quoi", "c est quoi", "qu'est-ce", "qu est-ce",
            "quelle est", "quel est", "quels sont",
            "définition", "definition", "expliquer", "signifie", "veut dire",
            "comment fonctionne", "pourquoi", "role", "rôle", "mission",
            "maroclear", "dépositaire", "depositaire",
            "bourse", "titre", "opcvm", "service", "post-marché",
            "dénouement", "denouement", "conservation",
            "affilie", "affilié", "affiliation",
        ]
        question_starters = [
            "qu'est-ce", "qu est-ce", "c'est quoi", "c est quoi",
        ]

        return (
            any(kw in query_lower for kw in rag_keywords)
            or any(query_lower.startswith(s) for s in question_starters)
        )

    # =========================================================
    # TRAITEMENT
    # =========================================================

    def process(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
        self.log(f"Traitement : {message.content[:100]}...")

        # ── Recherche prioritaire dans le glossaire pour les questions de définition ──
        glossary_boost = self._get_glossary_term(message.content)

        retrieved_docs = self.retriever.retrieve(message.content)

        # Injecter le chunk glossaire en tête s'il n'est pas déjà présent
        if glossary_boost:
            already_present = any(
                doc.get("metadata", {}).get("term", "").lower() == glossary_boost["metadata"]["term"].lower()
                for doc in retrieved_docs
            )
            if not already_present:
                retrieved_docs.insert(0, glossary_boost)
                self.log(f"Glossaire boosté : {glossary_boost['metadata']['term']}")

        retrieved_docs = self.retriever.retrieve(message.content)

        if not retrieved_docs:
            return AgentMessage.create_response(
                sender=self.agent_name,
                content=(
                    "Je n'ai pas trouvé d'informations pertinentes "
                    "dans la base de connaissances Maroclear. "
                    "Pouvez-vous reformuler votre question ?"
                ),
                metadata={"retrieved_docs_count": 0, "sources": []}
            )

        context_text = self._build_context(
            retrieved_docs,
            query=message.content,
        )

        response_text = self.llm_client.generate_rag_response(
            query=minimize_text_for_llm(message.content, context.get_session_data("user_profile", {})),
            context=context_text,
        )

        sources = list(dict.fromkeys(
            doc['metadata'].get('source', 'unknown') for doc in retrieved_docs
        ))

        return AgentMessage.create_response(
            sender=self.agent_name,
            content=response_text,
            metadata={
                "retrieved_docs_count": len(retrieved_docs),
                "sources": sources,
            }
        )

    # =========================================================
    # CONSTRUCTION DU CONTEXTE
    # =========================================================

    def _is_affiliation_query(self, query: str) -> bool:
        query_lower = query.lower()
        return any(
            keyword in query_lower
            for keyword in ("affilie", "affilié", "affiliation", "devenir affili")
        )

    def _build_context(self, retrieved_docs: List[Dict], query: str = "") -> str:
        """
        Construit le contexte transmis au LLM.

        Améliorations par rapport à l'ancienne version :
        - Les entrées du glossaire sont placées EN PREMIER (définitions exactes)
        - Chaque extrait est clairement labellisé avec son type et son score
        - Les doublons de contenu sont éliminés
        """
        # Séparer glossaire et documents PDF
        glossaire_docs = [d for d in retrieved_docs if d['metadata'].get('type') == 'glossaire']
        other_docs     = [d for d in retrieved_docs if d['metadata'].get('type') != 'glossaire']

        parts = []

        # ── Définitions du glossaire en tête ─────────────────────────────────
        if glossaire_docs:
            parts.append("=== DÉFINITIONS DU GLOSSAIRE ===")
            seen = set()
            for doc in glossaire_docs:
                content = doc['content'].strip()
                if content in seen:
                    continue
                seen.add(content)
                term = doc['metadata'].get('term', '')
                parts.append(f"• {content}")

        # ── Extraits des documents PDF ────────────────────────────────────────
        if other_docs:
            parts.append("\n=== EXTRAITS DES DOCUMENTS ===")
            seen = set()
            for i, doc in enumerate(other_docs, 1):
                content = doc['content'].strip()
                if content in seen:
                    continue
                seen.add(content)
                source = doc['metadata'].get('source', 'Document')
                score  = doc.get('score', 0)
                parts.append(f"[Extrait {i} — {source} — pertinence: {score:.2f}]\n{content}")

        if self._is_affiliation_query(query):
            parts.append(
                "\n=== COMPLEMENT OPERATIONNEL AFFILIATION ===\n"
                "Instruction: ce complement doit etre ajoute aux informations extraites des documents. "
                "Il ne remplace pas les etapes documentaires recuperees par le RAG; il precise le point "
                "d'entree operationnel de la demande.\n"
                "Pour initier une demande d'affiliation, le demandeur doit envoyer un email a "
                "support@maroclear.com en expliquant qu'il souhaite devenir affilie Maroclear. "
                "Le support repond ensuite avec un lien provisoire vers MyMaroclear afin de "
                "permettre le depot des documents necessaires au dossier d'affiliation."
            )

        result = "\n\n".join(parts)
        print(f"\n{'='*40}\nCONTEXTE ENVOYÉ AU LLM:\n{result}\n{'='*40}\n")  # DEBUG
        return result


    # =========================================================
    # CAPACITÉS
    # =========================================================

    def _get_glossary_term(self, query: str) -> dict | None:
        """
        Détecte si la question demande la définition d'un terme du glossaire
        et retourne directement le chunk correspondant via filtre ChromaDB.
        """
        import re
        query_lower = query.lower().strip().rstrip("?")

        # Patterns de questions de définition
        definition_patterns = [
            r"qu['\s]est[- ]ce qu['\s](?:un|une|le|la|les|l['\s])?(.+)",
            r"(?:définition|définir|définissez)[- ](?:de[- ])?(?:un|une|le|la|l['\s])?(.+)",
            r"(?:c['\s]est quoi|kesako)[- ](?:un|une|le|la|l['\s])?(.+)",
            r"(?:que signifie|que veut dire)[- ](?:un|une|le|la|l['\s])?(.+)",
            r"(?:différence entre|distinction entre)[^?]*?(?:le|la|la gestion au|au)?\s*(.+?)\s+et\s+",
        ]

        extracted_term = None
        for pattern in definition_patterns:
            match = re.search(pattern, query_lower)
            if match:
                extracted_term = match.group(1).strip().rstrip("?").strip()
                break

        if not extracted_term:
            return None

        # Chercher dans ChromaDB par filtre sur la métadonnée "type" = "glossaire"
        try:
            results = self.retriever.vector_store.collection.get(
                where={"type": "glossaire"},
                include=["documents", "metadatas"],
            )
            if not results or not results.get("documents"):
                return None

            # Chercher le terme le plus proche (correspondance partielle)
            extracted_lower = extracted_term.lower()
            best_match = None
            best_score = 0

            for doc, meta in zip(results["documents"], results["metadatas"]):
                term = meta.get("term", "").lower()
                # Score : correspondance exacte > contient > est contenu
                if term == extracted_lower:
                    best_match = (doc, meta)
                    break
                elif extracted_lower in term or term in extracted_lower:
                    score = len(term) if term in extracted_lower else len(extracted_lower)
                    if score > best_score:
                        best_score = score
                        best_match = (doc, meta)

            if best_match:
                return {
                    "content":  best_match[0],
                    "metadata": best_match[1],
                    "score":    1.0,  # priorité maximale
                    "id":       f"glossaire_{best_match[1].get('term', '')}",
                }
        except Exception as e:
            self.log(f"Erreur glossaire boost : {e}", level="WARNING")

        return None

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "agent_name":  self.agent_name,
            "description": "Répond aux questions métier sur Maroclear",
            "handles": [
                "Questions sur Maroclear (activités, services)",
                "Procédure d'affiliation",
                "Définitions du glossaire",
                "Questions générales métier",
            ],
            "knowledge_base_stats": self.retriever.vector_store.get_collection_stats(),
        }
