"""
builder.py — Assemblage du système multi-agents Maroclear
Charge la config, instancie les composants (ChromaDB, embeddings, LLM)
et construit l'orchestrateur prêt à l'emploi.
"""

import yaml
import uuid
from pathlib import Path
from dotenv import load_dotenv

# Charger le .env du backend (contient OPENROUTER_API_KEY)
load_dotenv(Path(__file__).parent.parent / ".env")

# RAG Components (shared)
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.rag.document_loader import DocumentLoader
from shared.rag.smart_chunker import SmartChunker
from shared.rag.embeddings import LocalEmbeddings
from shared.rag.vector_store import LocalVectorStore
from shared.rag.retriever import Retriever

# LLM (shared)
from shared.llm.ollama_client import OllamaClient

# Agents
from agents.informationnel_procedural.agent import RAGAgent
from agents.support_classification.agent import SupportClassificationAgent as ClassificationAgent
from agents.conseiller_reglementaire.agent import ReglementaireAgent
from agents.orchestrateur.agent import OrchestratorAgent

# LangGraph est optionnel — import conditionnel
try:
    from agents.orchestrateur.langgraph_agent import LangGraphOrchestratorAgent
    _LANGGRAPH_AVAILABLE = True
except (ImportError, Exception):
    _LANGGRAPH_AVAILABLE = False

# Core (shared)
from shared.core.message import AgentMessage
from shared.core.agent_context import AgentContext


# =============================================================
# CHARGEMENT CONFIG
# =============================================================

def load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# =============================================================
# INDEXATION DES DOCUMENTS (RAG général — inchangé)
# =============================================================

def index_documents(config: dict):
    """Indexe les documents PDF + glossaire Excel dans ChromaDB."""

    print("\n" + "=" * 60)
    print("INDEXATION DES DOCUMENTS")
    print("=" * 60 + "\n")

    loader  = DocumentLoader(config["documents"]["sources_dir"])
    chunker = SmartChunker()

    all_chunks    = []
    all_metadatas = []
    all_ids       = []

    # Glossaire Excel
    glossary_path   = config["documents"].get(
        "glossary_xlsx", "data/documents/glossaire_maroclear.xlsx"
    )
    glossary_chunks = loader.load_glossary_xlsx(glossary_path)

    for idx, chunk in enumerate(glossary_chunks):
        all_chunks.append(chunk["content"])
        all_metadatas.append(chunk["metadata"])
        all_ids.append(f"glossaire_{idx}")

    print(f"  -> {len(glossary_chunks)} termes charges depuis le glossaire Excel\n")

    # Documents PDF
    documents = loader.load_all_documents()
    print(f"{len(documents)} document(s) PDF charge(s)\n")

    for doc in documents:
        print(f"  Chunking : {doc['filename']}...")
        raw_chunks = chunker.chunk(
            text       = doc["content"],
            source     = doc["filename"],
            chunk_size = config["rag"].get("chunk_size", 600),
            overlap    = config["rag"].get("chunk_overlap", 80),
        )
        for chunk_idx, chunk in enumerate(raw_chunks):
            all_chunks.append(chunk["content"])
            all_metadatas.append({
                **doc["metadata"],
                **chunk["metadata"],
                "chunk_index": chunk_idx,
                "doc_name":    doc["filename"],
            })
            all_ids.append(f"{uuid.uuid4()}_{doc['filename']}_chunk_{chunk_idx}")
        print(f"     -> {len(raw_chunks)} chunks")

    print(f"\nTotal : {len(all_chunks)} chunks")

    # Embeddings
    embeddings_model = LocalEmbeddings(config["embeddings"]["model"])
    embeddings = embeddings_model.embed_documents(
        all_chunks,
        batch_size=config["embeddings"]["batch_size"]
    )

    # Stockage ChromaDB
    vector_store = LocalVectorStore(
        persist_directory=config["vector_store"]["persist_directory"],
        collection_name=config["vector_store"]["collection_name"],
    )
    print("Nettoyage de la collection existante...")
    vector_store.clear_collection()
    vector_store.add_documents(
        texts=all_chunks,
        embeddings=embeddings,
        metadatas=all_metadatas,
        ids=all_ids,
    )

    print(f"\nVerification : {vector_store.get_collection_stats()}")
    print("\n" + "=" * 60)
    print("INDEXATION TERMINEE")
    print("=" * 60 + "\n")

    return vector_store, embeddings_model


# =============================================================
# CONSTRUCTION DE L'ORCHESTRATEUR
# =============================================================

def build_orchestrator(config: dict, vector_store=None, embeddings_model=None):
    """
    Instancie les quatre agents et retourne l'orchestrateur pret a l'emploi.
    Agents : ClassificationAgent, RAGAgent, ReglementaireAgent, OrchestratorAgent
    """

    # ── RAG général ──────────────────────────────────────────
    if not vector_store:
        vector_store = LocalVectorStore(
            persist_directory=config["vector_store"]["persist_directory"],
            collection_name=config["vector_store"]["collection_name"],
        )

    if not embeddings_model:
        embeddings_model = LocalEmbeddings(config["embeddings"]["model"])

    retriever = Retriever(
        vector_store=vector_store,
        embeddings=embeddings_model,
        top_k=config["rag"].get("top_k", 8),
        similarity_threshold=config["rag"].get("similarity_threshold", 0.4),
    )

    # ── Client LLM partagé ───────────────────────────────────
    import os
    llm_config = config["llm"]
    api_key = llm_config.get("api_key") or os.environ.get("OPENROUTER_API_KEY", "")
    llm_client = OllamaClient(
        model=llm_config["model"],
        temperature=llm_config.get("temperature", 0.1),
        api_key=api_key,
        base_url=llm_config.get("base_url", "https://openrouter.ai/api/v1"),
        max_tokens=llm_config.get("max_tokens", 1024),
    )

    # ── Instanciation des agents ─────────────────────────────
    rag_agent = RAGAgent(
        config=config,
        retriever=retriever,
        llm_client=llm_client,
    )

    classification_agent = ClassificationAgent(
        config=config,
    )

    # ReglementaireAgent — charge son propre Retriever + LLMClient
    # depuis RAG_CHUNKING_PROJECT via config["reglementaire"]
    reglementaire_agent = ReglementaireAgent(config=config)

    # ── Orchestrateur ────────────────────────────────────────
    import os
    orchestrator_backend = os.environ.get(
        "ORCHESTRATOR_BACKEND",
        config.get("multi_agent", {}).get("orchestrator_backend", "classic"),
    )
    orchestrator_cls = (
        LangGraphOrchestratorAgent
        if orchestrator_backend == "langgraph"
        else OrchestratorAgent
    )

    orchestrator = orchestrator_cls(
        config=config,
        classification_agent=classification_agent,
        rag_agent=rag_agent,
        reglementaire_agent=reglementaire_agent,
    )

    return orchestrator


# =============================================================
# BOUCLE DE CONVERSATION INTERACTIVE
# =============================================================

def run_interactive(orchestrator: OrchestratorAgent):

    print("\n" + "=" * 60)
    print("  MAROCLEAR - Systeme Multi-Agents")
    print("  Agents : Classification + RAG + Reglementaire")
    print("=" * 60)
    print("  Commandes : 'quitter' | 'reset' | 'status' | 'capacites'")
    print("=" * 60 + "\n")

    print("Bonjour ! Je suis l'assistant Maroclear.")
    print("Je peux vous aider avec :")
    print("  - Un incident technique (blocage, dysfonctionnement)")
    print("  - Une demande de service (document, acces, PIN...)")
    print("  - Une reclamation")
    print("  - Une question sur les services ou procedures Maroclear")
    print("  - Une question juridique (Loi 35-96, Reglement General)\n")

    while True:
        try:
            user_input = input("Vous : ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nSession terminee.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quitter", "exit", "quit"):
            print("\nMerci d'avoir utilise l'assistant Maroclear. Au revoir !")
            break

        if user_input.lower() == "reset":
            orchestrator.reset_context()
            print("\nConversation reinitalisee.\n")
            continue

        if user_input.lower() == "status":
            history = orchestrator.context.get_history()
            print(f"\nStatut de la session :")
            print(f"  Messages echanges : {len(history)}")
            print(f"  Dernier agent     : {orchestrator.context.current_agent or 'aucun'}\n")
            continue

        if user_input.lower() == "capacites":
            caps = orchestrator.get_capabilities()
            print(f"\nCapacites de l'orchestrateur :")
            for route, desc in caps["routes"].items():
                print(f"  [{route}] {desc}")
            print()
            continue

        print()
        result = orchestrator.chat(user_input)

        print(f"Assistant [{result['agent_used']}] :\n")
        print(result["response"])

        if result["classification"]:
            print("\n" + "-" * 40)
            print(f"  Agent utilise  : {result['agent_used']}")
            print(f"  Classification : {result['classification']}")
            if result["priorite"]:
                print(f"  Priorite       : {result['priorite']}")
            if result["statut"]:
                print(f"  Statut         : {result['statut']}")
            if result["needs_glpi"]:
                print(f"  Ticket GLPI    : A creer")
            if result["rag_sources"]:
                print(f"  Sources RAG    : {result['rag_sources']}")
            print("-" * 40)

        # Afficher les sources réglementaires si disponibles
        if result.get("regl_sources"):
            print("\n" + "-" * 40)
            print(f"  Agent utilise  : {result['agent_used']}")
            print(f"  Sources legales: {result['regl_sources']}")
            print("-" * 40)

        print()


# =============================================================
# POINT D'ENTREE
# =============================================================

def main():
    config = load_config()

    print("\n" + "=" * 60)
    print("  MAROCLEAR - SYSTEME MULTI-AGENTS")
    print("=" * 60)
    print("\nQue voulez-vous faire ?")
    print("  1. Indexer les documents")
    print("  2. Lancer la conversation (documents deja indexes)")
    print("  3. Indexer ET lancer la conversation")

    choice = input("\nVotre choix (1/2/3) : ").strip()

    if choice == "1":
        index_documents(config)
    elif choice == "2":
        orchestrator = build_orchestrator(config)
        run_interactive(orchestrator)
    elif choice == "3":
        vector_store, embeddings_model = index_documents(config)
        orchestrator = build_orchestrator(config, vector_store, embeddings_model)
        run_interactive(orchestrator)
    else:
        print("Choix invalide.")


if __name__ == "__main__":
    main()
