"""
Orchestrateur LangGraph pour ClearBot.

Cette implementation coexiste avec agents/orchestrateur/agent.py.
Elle garde les agents metier existants et utilise LangGraph uniquement
pour modeliser le workflow de routage.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TypedDict

from shared.base.base_agent import BaseAgent
from shared.core.agent_context import AgentContext
from shared.core.message import AgentMessage
from shared.security import contains_sensitive_data, minimize_text_for_llm
from agents.informationnel_procedural.agent import RAGAgent
from agents.support_classification.agent import SupportClassificationAgent as ClassificationAgent
from agents.conseiller_reglementaire.agent import ReglementaireAgent


class GraphState(TypedDict, total=False):
    message: AgentMessage
    route: str
    response: Optional[AgentMessage]


class LangGraphOrchestratorAgent(BaseAgent):
    """
    Orchestrateur central base sur LangGraph.

    Les agents existants restent inchanges. LangGraph sert seulement a
    declarer les etapes : reponse directe -> routage -> delegation -> fin.
    """

    DEFAULT_RESPONSE = (
        "Je n'ai pas pu identifier le type de votre demande. "
        "Pourriez-vous preciser s'il s'agit :\n"
        "- D'un incident technique (dysfonctionnement, blocage)\n"
        "- D'une demande de service (document, acces, information)\n"
        "- D'une reclamation (insatisfaction, litige)\n"
        "- D'une question sur les services ou procedures Maroclear\n"
        "- D'une question juridique (Loi 35-96, Reglement General)"
    )

    _IDENTITY_KEYWORDS = [
        "qui es-tu", "qui es tu", "tu es qui", "c'est quoi clearbot",
        "c est quoi clearbot", "comment tu t'appelles", "ton nom",
        "que fais-tu", "que fais tu", "tu fais quoi", "a quoi tu sers",
    ]

    _IDENTITY_RESPONSE_PUBLIC = (
        "Je suis **ClearBot**, l'assistant IA de Maroclear, le depositaire central des titres au Maroc.\n\n"
        "Je peux vous renseigner sur :\n"
        "- Les **services** de Maroclear (reglement-livraison, admission des titres, conservation, OST)\n"
        "- La **procedure d'affiliation**\n"
        "- Le **cadre reglementaire** (Loi 35-96, Reglement General)\n"
        "- Les **donnees de marche**\n\n"
        "Si vous etes affilie et souhaitez declarer un incident ou soumettre une demande, "
        "connectez-vous a votre espace **MyMaroclear**.\n\n"
        "Posez-moi votre question !"
    )

    _IDENTITY_RESPONSE_PRIVATE = (
        "Je suis **ClearBot**, l'assistant IA de votre espace MyMaroclear.\n\n"
        "Je peux vous aider a :\n"
        "- Declarer un **incident** technique (blocage, erreur, indisponibilite)\n"
        "- Soumettre une **demande** (information, reinitialisation, retransmission)\n"
        "- Formuler une **reclamation** (facture erronee, ecart de donnees)\n"
        "- Repondre a vos **questions** sur les services et procedures Maroclear\n\n"
        "Decrivez-moi votre besoin et je vous guiderai."
    )

    _CONNECTION_KEYWORDS = [
        "connexion", "connecter", "me connecter", "pas connecter",
        "mot de passe oublie", "mdp oublie", "oublie mot de passe",
        "comment se connecter", "comment me connecter",
        "acces mymaroclear", "acceder a mymaroclear",
        "mfa", "code mfa", "authentification",
        "compte bloque", "bloque mon compte",
    ]

    _CONNECTION_RESPONSE = (
        "Voici les etapes pour vous connecter a **MyMaroclear** :\n\n"
        "1. Accedez a la page de connexion MyMaroclear\n"
        "2. Saisissez vos identifiants (nom d'utilisateur et mot de passe), puis cliquez sur **Connexion**\n"
        "3. Vous recevrez un **code MFA** (authentification multi-facteurs). "
        "Entrez le code recu dans le champ de saisie pour finaliser la connexion\n"
        "4. Acceptez les conditions generales si elles s'affichent "
        "(premiere connexion ou nouvelle version)\n\n"
        "**En cas de probleme :**\n"
        "- **Mot de passe oublie** : cliquez sur le lien \"Mot de passe oublie\" "
        "sur la page de connexion. Vous recevrez un lien de reinitialisation par email.\n"
        "- **Compte bloque** : apres 3 tentatives echouees, un delai progressif est applique. "
        "Attendez quelques minutes avant de reessayer.\n"
        "- **Code MFA non recu** : verifiez votre boite email (et spam). "
        "Si le probleme persiste, contactez le support.\n\n"
        "Si vous avez besoin d'une reinitialisation de mot de passe ou d'un nouveau token, "
        "decrivez votre besoin et je preparerai une demande."
    )

    def __init__(
        self,
        config: Dict[str, Any],
        classification_agent: ClassificationAgent,
        rag_agent: RAGAgent,
        reglementaire_agent: ReglementaireAgent,
    ):
        super().__init__(agent_name="LangGraph_Orchestrator_Agent", config=config)
        self.classification_agent = classification_agent
        self.rag_agent = rag_agent
        self.reglementaire_agent = reglementaire_agent
        self.context = AgentContext()
        self._graph = self._build_graph()
        self.log("Orchestrateur LangGraph initialise")

    def _build_graph(self):
        try:
            from langgraph.graph import END, StateGraph
        except ImportError as exc:
            raise ImportError(
                "LangGraph n'est pas installe. Lancez: "
                "python -m pip install langgraph"
            ) from exc

        graph = StateGraph(GraphState)
        graph.add_node("direct", self._direct_node)
        graph.add_node("route", self._route_node)
        graph.add_node("reglementaire", self._reglementaire_node)
        graph.add_node("classification", self._classification_node)
        graph.add_node("rag", self._rag_node)
        graph.add_node("none", self._none_node)

        graph.set_entry_point("direct")
        graph.add_conditional_edges(
            "direct",
            lambda state: "done" if state.get("response") else "route",
            {"done": END, "route": "route"},
        )
        graph.add_conditional_edges(
            "route",
            lambda state: state.get("route", "none"),
            {
                "reglementaire": "reglementaire",
                "classification": "classification",
                "rag": "rag",
                "none": "none",
            },
        )
        graph.add_edge("reglementaire", END)
        graph.add_edge("classification", END)
        graph.add_edge("rag", END)
        graph.add_edge("none", END)
        return graph.compile()

    def can_handle(self, message: AgentMessage, context: AgentContext) -> bool:
        return True

    def process(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
        self.log(f"Message recu : {message.content[:80]}...")
        result = self._graph.invoke({"message": message, "route": "", "response": None})
        response = result.get("response")
        if response is None:
            return self._make_default_response()
        return response

    def _direct_node(self, state: GraphState) -> GraphState:
        message = state["message"]
        self.context.add_message(sender="user", content=message.content, role="user")
        response = self._check_direct_response(message)
        if response:
            self.context.add_message(sender=self.agent_name, content=response.content, role="assistant")
            return {"response": response}
        return {"response": None}

    def _route_node(self, state: GraphState) -> GraphState:
        route = self._decide_route(state["message"])
        self.log(f"Route choisie : {route}")
        return {"route": route}

    def _reglementaire_node(self, state: GraphState) -> GraphState:
        response = self._handle_reglementaire(state["message"])
        self._remember_response(response)
        return {"response": response}

    def _classification_node(self, state: GraphState) -> GraphState:
        response = self._handle_classification(state["message"])
        self._remember_response(response)
        return {"response": response}

    def _rag_node(self, state: GraphState) -> GraphState:
        response = self._handle_rag(state["message"])
        self._remember_response(response)
        return {"response": response}

    def _none_node(self, state: GraphState) -> GraphState:
        response = self._make_default_response()
        self._remember_response(response)
        return {"response": response}

    def _remember_response(self, response: AgentMessage) -> None:
        self.context.add_message(
            sender=response.sender_agent,
            content=response.content,
            role="assistant",
        )

    def _check_direct_response(self, message: AgentMessage) -> Optional[AgentMessage]:
        text = message.content.lower()
        app_context = self.context.get_session_data("app_context", "private")
        user_profile = self.context.get_session_data("user_profile", {})

        if app_context == "public" and contains_sensitive_data(message.content, user_profile):
            return AgentMessage.create_response(
                sender=self.agent_name,
                content=(
                    "Votre message semble contenir des informations personnelles ou liees a un dossier support. "
                    "Pour des raisons de confidentialite, veuillez poursuivre depuis votre espace authentifie."
                ),
                metadata={
                    "route": "direct",
                    "agent_used": "orchestrator",
                    "quick_replies": ["Se connecter a MyMaroclear"],
                    "needs_login": True,
                    "privacy_redirect": True,
                },
            )

        if any(kw in text for kw in self._IDENTITY_KEYWORDS):
            content = self._IDENTITY_RESPONSE_PUBLIC if app_context == "public" else self._IDENTITY_RESPONSE_PRIVATE
            return AgentMessage.create_response(
                sender=self.agent_name,
                content=content,
                metadata={"route": "direct", "agent_used": "orchestrator", "quick_replies": []},
            )

        if any(kw in text for kw in self._CONNECTION_KEYWORDS):
            incident_signals = ["erreur 500", "page blanche", "indisponible", "inaccessible", "panne"]
            if not any(signal in text for signal in incident_signals):
                return AgentMessage.create_response(
                    sender=self.agent_name,
                    content=self._CONNECTION_RESPONSE,
                    metadata={"route": "direct", "agent_used": "orchestrator", "quick_replies": []},
                )

        if app_context == "public":
            support_keywords = [
                "declarer", "incident", "reclamation", "demande",
                "probleme", "probleme", "panne", "bug", "bloque",
                "pas recu", "non recu", "errone", "facture",
            ]
            if any(kw in text for kw in support_keywords):
                return AgentMessage.create_response(
                    sender=self.agent_name,
                    content=(
                        "Pour declarer un incident, soumettre une demande ou formuler une reclamation, "
                        "vous devez vous connecter a votre espace prive **MyMaroclear**.\n\n"
                        "Une fois connecte, je pourrai vous guider dans la creation de votre dossier."
                    ),
                    metadata={
                        "route": "direct",
                        "agent_used": "orchestrator",
                        "quick_replies": ["Se connecter a MyMaroclear"],
                        "needs_login": True,
                    },
                )

        return None

    def _decide_route(self, message: AgentMessage) -> str:
        state = self.context.get_session_data("classif_state")
        if state and state not in ("classifying", "done", None):
            self.log("Session classification en cours -> route: classification")
            return "classification"

        try:
            user_profile = self.context.get_session_data("user_profile", {})
            route = self._llm_route(minimize_text_for_llm(message.content, user_profile))
            if route in ("reglementaire", "classification", "rag"):
                self.log(f"LLM Router -> {route}")
                return route
        except Exception as exc:
            self.log(f"LLM Router erreur ({exc}) -> fallback keywords", level="WARNING")

        return self._decide_route_keywords(message)

    def _llm_route(self, user_message: str) -> str:
        import os
        from openai import OpenAI

        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise ValueError("Pas de cle API")

        client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        router_prompt = """Tu es un routeur de messages pour le systeme multi-agents Maroclear.
Analyse le message de l'utilisateur et retourne UNIQUEMENT un mot parmi :
- "reglementaire" : question juridique, legale, sur les lois, articles, obligations, droits, procedures legales, cadre reglementaire du marche financier marocain
- "classification" : declaration d'incident technique, demande d'action/service, reclamation, probleme d'acces, fichier manquant, erreur systeme
- "rag" : question generale sur Maroclear (services, definitions, fonctionnement, c'est quoi, comment ca marche)

Regles :
- Si l'utilisateur signale un PROBLEME (blocage, erreur, panne, fichier vide, acces impossible) -> "classification"
- Si l'utilisateur DEMANDE une action (transmettre, reinitialiser, envoyer, prolonger) -> "classification"
- Si l'utilisateur pose une question sur la LOI, les ARTICLES, les OBLIGATIONS legales -> "reglementaire"
- Si l'utilisateur demande une DEFINITION ou une EXPLICATION generale -> "rag"
- En cas de doute entre rag et reglementaire, prefere "reglementaire"

Retourne UNIQUEMENT le mot, sans ponctuation ni explication."""

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b:free",
            messages=[
                {"role": "system", "content": router_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=15,
            temperature=0.0,
        )
        return response.choices[0].message.content.strip().lower().strip('"\'.,;: ')

    def _decide_route_keywords(self, message: AgentMessage) -> str:
        can_regl = self.reglementaire_agent.can_handle(message, self.context)
        can_classif = self.classification_agent.can_handle(message, self.context)
        can_rag = self.rag_agent.can_handle(message, self.context)
        self.log(f"Fallback keywords -> Regl={can_regl} | Classif={can_classif} | RAG={can_rag}")

        text = message.content.lower()
        support_keywords = [
            "probleme", "incident", "bug", "erreur", "bloque",
            "connexion", "connecter", "login", "mot de passe",
            "reclamation", "demande", "assistance", "ticket",
            "ne marche pas", "ne fonctionne pas", "impossible", "panne",
        ]
        has_support_intent = any(keyword in text for keyword in support_keywords)

        if can_regl and not (can_classif and has_support_intent):
            return "reglementaire"
        if can_classif:
            return "classification"
        if can_rag:
            return "rag"
        return "none"

    def _handle_reglementaire(self, message: AgentMessage) -> AgentMessage:
        self.log("Delegation -> ReglementaireAgent")
        response = self.reglementaire_agent.process(message, self.context)
        response.metadata["route"] = "reglementaire"
        response.metadata["agent_used"] = "ReglementaireAgent"
        return response

    def _handle_classification(self, message: AgentMessage) -> AgentMessage:
        self.log("Delegation -> ClassificationAgent")
        classif_response = self.classification_agent.process(message, self.context)
        needs_rag = classif_response.metadata.get("needs_rag", False)

        if needs_rag and self.rag_agent.can_handle(message, self.context):
            self.log("Classification -> needs_rag=True, complement RAGAgent")
            rag_response = self.rag_agent.process(message, self.context)
            return self._merge_responses(classif_response, rag_response)

        classif_response.metadata["route"] = "classification"
        classif_response.metadata["agent_used"] = "ClassificationAgent"
        return classif_response

    def _handle_rag(self, message: AgentMessage) -> AgentMessage:
        self.log("Delegation -> RAGAgent")
        response = self.rag_agent.process(message, self.context)
        response.metadata["route"] = "rag"
        response.metadata["agent_used"] = "RAGAgent"
        # Exposer les sources sous rag_sources pour cohérence avec chat()
        response.metadata["rag_sources"] = response.metadata.get("sources", [])
        return response

    def _merge_responses(self, classif_response: AgentMessage, rag_response: AgentMessage) -> AgentMessage:
        merged_content = (
            classif_response.content
            + "\n\n"
            + "=" * 50
            + "\nINFORMATIONS COMPLEMENTAIRES (Base documentaire Maroclear)\n"
            + "=" * 50
            + "\n\n"
            + rag_response.content
        )
        return AgentMessage.create_response(
            sender=self.agent_name,
            content=merged_content,
            metadata={
                **classif_response.metadata,
                "rag_sources": rag_response.metadata.get("sources", []),
                "rag_docs": rag_response.metadata.get("retrieved_docs_count", 0),
                "route": "classification+rag",
                "agent_used": "ClassificationAgent + RAGAgent",
            },
        )

    def _make_default_response(self) -> AgentMessage:
        return AgentMessage.create_response(
            sender=self.agent_name,
            content=self.DEFAULT_RESPONSE,
            metadata={"route": "none", "agent_used": "orchestrator"},
        )

    def chat(self, user_input: str) -> Dict[str, Any]:
        message = AgentMessage.create_query(sender="user", content=user_input)
        response = self.process(message, self.context)
        return {
            "response": response.content,
            "agent_used": response.metadata.get("agent_used", "unknown"),
            "route": response.metadata.get("route", "unknown"),
            "classification": response.metadata.get("classification", ""),
            "priorite": response.metadata.get("priorite", ""),
            "statut": response.metadata.get("statut", ""),
            "service": response.metadata.get("service", ""),
            "systeme": response.metadata.get("systeme", ""),
            "needs_glpi": response.metadata.get("needs_glpi", False),
            "rag_sources": response.metadata.get("rag_sources", []),
            "regl_sources": response.metadata.get("sources", []),
            "regl_sources_detailed": response.metadata.get("sources_detailed", []),
            "quick_replies": response.metadata.get("quick_replies", []),
            "form_data": response.metadata.get("form_data"),
        }

    def reset_context(self) -> None:
        self.context = AgentContext()
        self.reglementaire_agent.reset()
        self.log("Contexte reinitialise")

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "description": "Orchestrateur LangGraph du systeme multi-agents Maroclear",
            "backend": "langgraph",
            "routes": {
                "reglementaire": "Questions juridiques : Loi 35-96, Reglement General",
                "classification": "Incidents, demandes, reclamations des affilies",
                "rag": "Questions documentaires et metier sur Maroclear",
                "classification+rag": "Demandes necessitant classification ET documentation",
            },
            "agents": {
                "ReglementaireAgent": self.reglementaire_agent.get_capabilities(),
                "ClassificationAgent": self.classification_agent.get_capabilities(),
                "RAGAgent": self.rag_agent.get_capabilities(),
            },
        }
