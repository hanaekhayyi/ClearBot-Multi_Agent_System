try:
    from retriever import Retriever
    from llm_client import LLMClient
except ImportError:
    from src.retriever import Retriever
    from src.llm_client import LLMClient


SYSTEM_PROMPT = """Tu es un expert juriste specialise dans le cadre reglementaire du marche financier marocain.

Tu reponds exclusivement a partir des extraits fournis par le RAG.

Regles obligatoires:
1. Cite chaque affirmation juridique avec les identifiants de source fournis dans le contexte: [S1], [S2], etc.
2. Quand une source contient un chemin hierarchique, utilise-le dans la reponse: document > livre/titre > chapitre > section > article/annexe.
3. Quand une source contient des pages, mentionne-les.
4. Si un extrait recupere par lien (Mode recuperation: link ou pdf_link) complete l'article principal, utilise-le explicitement.
5. Si des notes de bas de page sont fournies, integre-les lorsque leur contenu modifie ou precise la regle.
6. Distingue les deux corpus:
   - Actualite historique: notamment la Loi 35-96 / Dahir n 1-96-246.
   - Recueil AMMC: corpus structure par Docling avec articles, annexes, pages, notes et liens PDF.
7. Si les extraits fournis ne permettent pas de repondre avec certitude, dis:
   "Les extraits fournis ne permettent pas de repondre avec certitude a cette question."

Style: professionnel, juridique, clair, structure en sections courtes."""


class Agent:
    """Conversationnel RAG avec historique court et sources structurees."""

    def __init__(self, retriever: Retriever, llm: LLMClient, max_history: int = 10):
        self.retriever = retriever
        self.llm = llm
        self.max_history = max_history
        self.history: list[dict] = []

    def chat(self, user_input: str) -> str:
        chunks = self.retriever.retrieve(user_input)
        context = self.retriever.format_context(chunks)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += self.history
        messages.append({
            "role": "user",
            "content": f"Contexte source:\n{context}\n\nQuestion:\n{user_input}",
        })

        answer = self.llm.chat(messages)

        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": answer})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-(self.max_history * 2):]

        return answer

    def chat_with_sources(self, user_input: str) -> dict:
        chunks = self.retriever.retrieve(user_input)
        context = self.retriever.format_context(chunks)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Contexte source:\n{context}\n\nQuestion:\n{user_input}"},
        ]
        answer = self.llm.chat(messages)
        return {
            "answer": answer,
            "sources": self.retriever.format_sources(chunks),
        }

    def reset(self):
        self.history = []
