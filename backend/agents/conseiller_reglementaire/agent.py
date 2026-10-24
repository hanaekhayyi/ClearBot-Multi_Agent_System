"""
ReglementaireAgent
==================
Wrappeur du RAG réglementaire (projet RAG_CHUNKING_PROJECT / AGENT_CONVERSATIONNEL)
pour l'intégrer dans le système multi-agents Maroclear.

Ce fichier est à placer dans :
    AGENT_CONVERSATIONNEL/agents/reglementaire_agent.py

Il importe le Retriever et le LLMClient du projet RAG réglementaire
via des chemins configurables dans config.yaml.

Prérequis dans config.yaml (AGENT_CONVERSATIONNEL) :
    reglementaire:
      rag_project_path: "../RAG_CHUNKING_PROJECT"   # chemin relatif ou absolu
      settings_path: "config/settings.yaml"          # relatif au rag_project_path
      enabled: true
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.base.base_agent import BaseAgent
from shared.core.message import AgentMessage
from shared.core.agent_context import AgentContext
from shared.security import minimize_text_for_llm


# ─────────────────────────────────────────────────────────────────
# SYSTEM PROMPT JURIDIQUE (repris de agent.py du RAG réglementaire)
# ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es un expert juriste spécialisé dans le cadre réglementaire du marché financier marocain. Tu maîtrises l'ensemble du Recueil des textes législatifs et réglementaires du marché de capitaux, notamment :
- La Loi n° 35-96 (création du Dépositaire Central)
- La Loi n° 44-12 (Appel public à l'épargne)
- La Loi n° 19-14 (Bourse des valeurs)
- La Loi n° 17-95 (Sociétés anonymes)
- La Loi n° 41-05 (OPCVM)
- La Loi n° 70-14 (OPCI)
- La Loi n° 33-06 (Titrisation)
- Le Règlement Général de Maroclear
- Le Règlement Général de la Bourse des valeurs
- Les Circulaires de l'AMMC
- Les Décrets et Arrêtés d'application

Ton rôle est d'analyser les extraits fournis pour produire une réponse technique, rigoureuse et juridiquement sourcée.

Règles de réponse :

1. PRIMAUTÉ DU CONTEXTE — EXHAUSTIVITÉ
Réponds à partir des extraits fournis. Exploite TOUS les extraits pertinents, même s'ils proviennent de textes différents (Loi, Arrêté, Circulaire). Ne conclus JAMAIS qu'il n'existe pas d'autres dispositions si les extraits ne couvrent pas l'ensemble du corpus — indique plutôt "D'autres dispositions peuvent exister dans les textes non fournis."

2. HIÉRARCHIE NORMATIVE
Distingue systématiquement :
- Les Lois (Dahirs) : Normes supérieures fixant les principes.
- Les Décrets et Arrêtés : Normes d'application.
- Les Circulaires AMMC : Précisions techniques et procédurales.
- Les Règlements Généraux : Modalités opérationnelles.
En cas de divergence, la Loi prévaut sur le Règlement, qui prévaut sur la Circulaire.

3. CROISEMENT DES SOURCES
Lorsqu'une question touche plusieurs textes (ex: dispense de prospectus = Loi 44-12 Art. 8 + Circulaire AMMC Art. 1.27 + Arrêté 2560-95), croise systématiquement les extraits pour donner une réponse complète.

4. CITATION CANONIQUE
Chaque affirmation doit être suivie de sa source exacte :
Format : [Nom du Texte], Article [Numéro], page [N].
Utilise les métadonnées de hiérarchie (Livre > Titre > Chapitre > Section > Article).

5. ANALYSE EXHAUSTIVE
Si la question concerne des cas de figure (ex: "dans quels cas..."), liste TOUS les cas trouvés dans les extraits, en distinguant ceux issus de la Loi, des Arrêtés et des Circulaires.

6. ABSENCE D'INFORMATION
Si les extraits fournis ne contiennent pas tous les éléments nécessaires, réponds avec ce qui est disponible ET indique : "Note : d'autres dispositions peuvent exister dans les textes non inclus dans les extraits fournis."
Ne dis JAMAIS "aucun autre cas n'est mentionné" — dis plutôt "les extraits fournis mentionnent les cas suivants".

7. STYLE
Professionnel, neutre, structuré par sections juridiques claires. Utilise des tableaux pour les listes de cas. Cite les pages du Recueil quand disponibles."""


# ─────────────────────────────────────────────────────────────────
# AGENT
# ─────────────────────────────────────────────────────────────────

class ReglementaireAgent(BaseAgent):
    """
    Agent spécialisé dans le droit réglementaire Maroclear.
    Utilise le Retriever hybride (vectoriel + BM25) du projet RAG réglementaire
    et un LLMClient configuré via settings.yaml du même projet.

    Mots-clés de routage : questions sur la Loi 35-96, le Règlement Général,
    les articles, affiliés, teneurs de comptes, sanctions, procédures légales.
    """

    # Mots-clés qui déclenchent cet agent (used in can_handle)
    KEYWORDS = [
    # Références légales explicites
    "loi 35-96", "loi35-96", "loi 44-12", "loi 19-14", "loi 17-95",
    "loi 41-05", "loi 70-14", "loi 33-06", "loi 35-94",
    "dahir", "règlement général", "reglement general",
    "alinéa", "alinea",
    "teneur de comptes", "valeurs admises",
    "dépositaire central", "depositaire central",
    "sanction", "disciplinaire", "habilitation", "agrément", "agrement",
    "réglementaire", "reglementaire", "juridique", "légal", "legal",
    "procédure légale", "procedure legale", "plan comptable",
    "circulaire", "texte de loi", "circulaire ammc",

    # Formulations naturelles avec "loi"
    "selon la loi", "dans la loi", "d'après la loi",
    "par la loi", "prévu par la loi", "défini par la loi", "stipulé par",
    "disposition légale", "cadre légal", "cadre legal",
    "cadre réglementaire", "cadre reglementaire",

    # Termes métier réglementaires
    "intermédiaire financier", "intermediaire financier",
    "inscription en compte", "valeurs mobilières", "valeurs mobilieres",
    "organisme de placement", "société de bourse", "societe de bourse",
    "bank al-maghrib", "trésorerie générale", "tresorerie generale",
    "caisse de dépôt", "caisse de depot",
    "appel public à l'épargne", "appel public a l'epargne",
    "prospectus", "investisseur qualifié", "investisseur qualifie",

    # Intent de recherche légale
    "entités citées", "entites citees", "liste exhaustive",
    "mentionné dans la loi", "mentionne dans la loi",
    "définition légale", "definition legale",
    "quelles sont les obligations", "quels sont les droits",
    "dans quels cas", "conditions légales", "conditions legales",
]

    def __init__(self, config: Dict[str, Any]):
        super().__init__(agent_name="ReglementaireAgent", config=config)

        regl_cfg = config.get("reglementaire", {})

        if not regl_cfg.get("enabled", True):
            self.log("ReglementaireAgent désactivé dans config.yaml")
            self._enabled = False
            return

        self._enabled = True

        # ── Résoudre le chemin vers le pipeline RAG réglementaire ──
        # Les chemins relatifs dans config.yaml doivent être basés sur backend/
        backend_root     = Path(__file__).resolve().parents[2]
        rag_project_path = Path(regl_cfg.get("rag_project_path", "agents/conseiller_reglementaire"))
        if not rag_project_path.is_absolute():
            rag_project_path = (backend_root / rag_project_path).resolve()
        else:
            rag_project_path = rag_project_path.resolve()

        settings_rel     = regl_cfg.get("settings_path", "data/settings.yaml")
        settings_path    = rag_project_path / settings_rel

        if not rag_project_path.exists():
            raise FileNotFoundError(
                f"ReglementaireAgent : dossier RAG introuvable → {rag_project_path}\n"
                f"Vérifiez 'reglementaire.rag_project_path' dans config.yaml"
            )

        # Dans la nouvelle structure, les sources sont dans rag/ (et non src/)
        src_path = rag_project_path / "rag"
        if not src_path.exists():
            # Fallback : ancienne structure avec src/
            src_path = rag_project_path / "src"

        # ── Charger settings.yaml du RAG réglementaire ──
        with open(settings_path, "r", encoding="utf-8") as f:
            rag_settings = yaml.safe_load(f)

        # ── Imports directs par chemin (évite __init__.py et ses dépendances inutiles) ──
        import importlib.util

        def _load(name, filepath):
            spec = importlib.util.spec_from_file_location(name, filepath)
            mod  = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod          # enregistrer AVANT exec pour les imports circulaires
            spec.loader.exec_module(mod)
            return mod

        _load("rag.llm_client",  src_path / "llm_client.py")
        _load("rag.embedder",    src_path / "embedder.py")
        _load("rag.vector_store",src_path / "vector_store.py")
        _load("rag.retriever",   src_path / "retriever.py")

        # Alias pour la suite du code
        LLMClient    = sys.modules["rag.llm_client"].LLMClient
        Embedder     = sys.modules["rag.embedder"].Embedder
        VectorStore  = sys.modules["rag.vector_store"].VectorStore
        Retriever    = sys.modules["rag.retriever"].Retriever

        # ── Résoudre le chemin ChromaDB en absolu ──
        chroma_dir = (rag_project_path / rag_settings["vector_store"]["persist_dir"]).resolve()

        # Instancier les composants
        embedder     = Embedder(
            model_name = rag_settings["embedding"]["model"],
            use_fp16   = rag_settings["embedding"]["use_fp16"],
        )
        vector_store = VectorStore(
            persist_dir     = str(chroma_dir),
            collection_name = rag_settings["vector_store"]["collection_name"],
            embedder        = embedder,
        )
        # Reranker config
        reranker_cfg = rag_settings.get("reranker", {})
        reranker_model = reranker_cfg.get("model") if reranker_cfg.get("enabled") else None
        reranker_top_k = reranker_cfg.get("top_k", 10)

        interactive_n_results = regl_cfg.get("interactive_n_results")
        interactive_reranker_top_k = regl_cfg.get("interactive_reranker_top_k")
        interactive_max_tokens = regl_cfg.get("interactive_max_tokens")
        self._context_chars_per_chunk = int(regl_cfg.get("interactive_context_chars_per_chunk", 2500))

        self._retriever = Retriever(
            vector_store   = vector_store,
            embedder       = embedder,
            n_results      = int(interactive_n_results or rag_settings["vector_store"]["n_results"]),
            reranker_model = reranker_model,
            reranker_top_k = int(interactive_reranker_top_k or reranker_top_k),
        )
        self._llm = LLMClient(
            api_key     = rag_settings["llm"]["api_key"],
            model       = rag_settings["llm"]["model"],
            max_tokens  = int(interactive_max_tokens or rag_settings["llm"]["max_tokens"]),
            temperature = rag_settings["llm"]["temperature"],
        )

        # Historique de conversation (multi-tours)
        self._history: list[dict] = []
        self._max_history: int    = regl_cfg.get("max_history", 10)

        self.log(f"ReglementaireAgent prêt — ChromaDB : {chroma_dir}")

    # ─────────────────────────────────────────────────────────────
    # ROUTING
    # ─────────────────────────────────────────────────────────────

    def can_handle(self, message: AgentMessage, context: AgentContext) -> bool:
        """
        Détection intelligente des questions réglementaires.
        Combine : mots-clés explicites + patterns de questions juridiques + détection d'intent.
        """
        if not self._enabled:
            return False
        text = message.content.lower()

        # 1. Mots-clés explicites (haute confiance)
        explicit_keywords = [
            "loi 35-96", "loi 44-12", "loi 19-14", "loi 17-95", "loi 41-05",
            "loi 70-14", "loi 33-06", "loi 35-94", "loi 94-21", "loi 26-03",
            "dahir", "circulaire ammc", "circulaire 03/19", "circulaire n",
            "règlement général", "reglement general",
            "dépositaire central", "depositaire central",
            "appel public", "prospectus", "investisseur qualifié", "investisseur qualifie",
            "cadre réglementaire", "cadre reglementaire", "cadre légal", "cadre legal",
            "texte de loi", "disposition légale", "disposition legale",
            "sanction disciplinaire", "habilitation",
        ]
        if any(kw in text for kw in explicit_keywords):
            return True

        # 2. Patterns de questions juridiques (intent)
        legal_patterns = [
            "selon la loi", "d'après la loi", "prévu par la loi", "prevu par la loi",
            "en vertu de", "conformément à", "conformement a",
            "quelles sont les obligations", "quels sont les droits",
            "dans quels cas", "conditions légales", "conditions legales",
            "qui est autorisé", "qui est autorise", "qui peut",
            "est-il obligatoire", "est il obligatoire",
            "quelle est la procédure", "quelle est la procedure",
            "quelles entités", "quelles entites",
            "dispense de", "exemption de", "dérogation", "derogation",
            "inscription en compte", "valeurs mobilières", "valeurs mobilieres",
            "teneur de comptes", "plan comptable titres",
            "opération sur titres", "operation sur titres",
            "titrisation", "opcvm", "opci", "fpct", "fpcc",
        ]
        if any(p in text for p in legal_patterns):
            return True

        # 3. Combinaison question + terme métier (détection d'intent)
        question_words = ["quel", "quelle", "quels", "quelles", "comment", "pourquoi",
                          "qui", "dans quel", "sous quelle", "à quelle", "a quelle"]
        legal_terms = ["loi", "article", "obligation", "droit", "affilié", "affilie",
                       "émetteur", "emetteur", "ammc", "maroclear", "bourse",
                       "titre", "valeur", "capital", "action", "obligation",
                       "admission", "codification", "conservation", "règlement", "reglement",
                       "pension", "repo", "transfert", "dénouement", "denouement",
                       "intermédiaire", "intermediaire", "mandat"]
        has_question = any(q in text for q in question_words)
        has_legal_term = any(t in text for t in legal_terms)

        # Si c'est une question + terme métier ET pas un message de support
        if has_question and has_legal_term:
            support_signals = [
                "bloque", "erreur", "panne", "bug", "impossible",
                "ne fonctionne pas", "ne marche pas", "indisponible",
                "pas recu", "non recu", "facture erron", "reclamation",
                "reinitialisation", "mot de passe", "token rsa",
                "batch en cours", "pending", "page blanche",
            ]
            if not any(s in text for s in support_signals):
                return True

        return False

    # ─────────────────────────────────────────────────────────────
    # TRAITEMENT
    # ─────────────────────────────────────────────────────────────

    def process(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
        """Récupère les chunks pertinents et génère une réponse juridique."""
        if not self._enabled:
            return AgentMessage.create_response(
                sender   = self.agent_name,
                content  = "Le module réglementaire n'est pas activé.",
                metadata = {"agent_used": self.agent_name, "route": "reglementaire"},
            )

        user_input = message.content
        llm_user_input = minimize_text_for_llm(
            user_input,
            context.get_session_data("user_profile", {}) if context else {},
        )

        # ── Retrieval hybride ──
        chunks  = self._retriever.retrieve(user_input)
        context_text = self._retriever.format_context(
            chunks,
            max_chars_per_chunk=self._context_chars_per_chunk,
        )

        # ── LOG : chunks récupérés ──
        print(f"\n{'='*60}")
        print(f"[ReglementaireAgent] Question : {user_input[:80]}...")
        print(f"[ReglementaireAgent] Chunks récupérés : {len(chunks)}")
        for idx, c in enumerate(chunks):
            meta = c.get("metadata", {})
            print(f"  [{idx+1}] {meta.get('reference_id', '?')} | {meta.get('source', '?')[:60]} | p.{meta.get('page_start', '?')}")
        print(f"{'='*60}\n")

        # ── Construction des messages LLM ──
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if self._max_history > 0:
            messages += self._history
        messages.append({
            "role":    "user",
            "content": f"Contexte :\n{context_text}\n\nQuestion : {llm_user_input}",
        })

        # ── Appel LLM ──
        answer = self._llm.chat(messages)

        # ── Mise à jour de l'historique (question brute, pas le contexte) ──
        self._history.append({"role": "user",      "content": llm_user_input})
        self._history.append({"role": "assistant",  "content": answer})
        if len(self._history) > self._max_history * 2:
            self._history = self._history[-(self._max_history * 2):]

        # ── Sources pour le frontend (enrichies avec hiérarchie + page) ──
        sources_detailed = []
        seen = set()
        for c in chunks:
            meta = c.get("metadata", {})
            source = meta.get("source") or meta.get("document", "")
            hierarchy = meta.get("hierarchy", "")
            ref_id = meta.get("reference_id", "")
            page_start = meta.get("page_start")
            # Clé de déduplication
            key = f"{source}|{ref_id}|{page_start}"
            if key in seen or not source:
                continue
            seen.add(key)
            sources_detailed.append({
                "document": source,
                "article": ref_id,
                "hierarchy": hierarchy,
                "page": page_start,
                "livre": meta.get("livre", ""),
                "corpus": meta.get("corpus", ""),
            })

        # Liste simple (compatibilité) — noms de documents uniques
        sources_simple = list({s["document"] for s in sources_detailed})

        return AgentMessage.create_response(
            sender   = self.agent_name,
            content  = answer,
            metadata = {
                "agent_used":          self.agent_name,
                "route":               "reglementaire",
                "sources":             sources_simple,
                "sources_detailed":    sources_detailed,
                "retrieved_docs_count": len(chunks),
            },
        )

    def reset(self):
        """Efface l'historique de conversation."""
        self._history = []

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "agent_name":  self.agent_name,
            "description": "Questions juridiques : Loi 35-96, Règlement Général Maroclear",
            "enabled":     self._enabled,
            "keywords":    self.KEYWORDS[:8],
        }
