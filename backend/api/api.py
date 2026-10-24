# api.py
import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime
from pathlib import Path

# Ajouter le dossier backend/ et api/ au path Python
sys.path.insert(0, str(Path(__file__).parent))        # backend/api/
sys.path.insert(0, str(Path(__file__).parent.parent))  # backend/

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from builder import build_orchestrator, load_config
from agents.conseiller_reglementaire.agent import ReglementaireAgent
from agents.auto_dispatcher.agent import AutoDispatcherAgent
from shared.core.message import AgentMessage
from shared.core.agent_context import AgentContext

app = FastAPI()
TEST_MODE = os.getenv("CLEARBOT_TEST_MODE", "").lower() in {"1", "true", "yes"}

SESSION_SECRET = os.getenv("SESSION_SECRET_KEY", "dev-maroclear-session-secret-change-me")

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="maroclear_session",
    same_site="lax",
    https_only=False,
    max_age=8 * 60 * 60,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


def _hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    )
    return digest.hex()


def _make_user(
    user_id: str,
    username: str,
    password: str,
    full_name: str,
    activity: str,
    institution: str,
    email: str,
    phone: str,
    role: str,
):
    salt = secrets.token_hex(16)
    return {
        "id": user_id,
        "username": username,
        "password_salt": salt,
        "password_hash": _hash_password(password, salt),
        "profile": {
            "id": user_id,
            "username": username,
            "reporterName": full_name,
            "reporterActivity": activity,
            "institution": institution,
            "reporterEmail": email,
            "reporterPhone": phone,
            "role": role,
        },
    }


USERS = {
    "asmae.hidra": _make_user(
        "u-aff-001",
        "asmae.hidra",
        os.getenv("DEMO_AFFILIE_PASSWORD", "maroclear123"),
        "HIDRA Asmae",
        "Banque Depositaire",
        "ATTIJARIWAFA BANK",
        "asmae.hidra@attijariwafa.example",
        "+212600000000",
        "Responsable support affilie",
    ),
    "adil.elbouzgui": _make_user(
        "u-aff-002",
        "adil.elbouzgui",
        os.getenv("DEMO_MANAGER_PASSWORD", "maroclear123"),
        "Adil EL BOUZGUI",
        "Banque Depositaire",
        "ATTIJARIWAFA BANK",
        "adil.elbouzgui@attijariwafa.example",
        "022224169",
        "Responsable",
    ),
}


class LoginRequest(BaseModel):
    username: str
    password: str
    remember: bool = False


class ChatSessionRequest(BaseModel):
    messages: list[dict] = []
    stage: str = "chatting"
    pendingData: dict | None = None


def _public_user(user):
    return user["profile"]


def _sanitize_messages(messages: list[dict]) -> list[dict]:
    cleaned = []
    for message in messages[-80:]:
        if not isinstance(message, dict):
            continue

        text = str(message.get("text") or message.get("content") or "").strip()
        if not text:
            continue

        sender = message.get("from")
        if sender not in ("user", "bot"):
            role = message.get("role")
            sender = "user" if role == "user" else "bot"

        cleaned.append({
            "id": message.get("id") or secrets.token_hex(8),
            "from": sender,
            "text": text[:4000],
            "time": message.get("time", ""),
            "type": message.get("type"),
            "classification": message.get("classification"),
            "priorite": message.get("priorite"),
            "agent_used": message.get("agent_used"),
            "needs_glpi": bool(message.get("needs_glpi", False)),
            "rag_sources": message.get("rag_sources") or [],
            "regl_sources": message.get("regl_sources") or [],
        })
    return cleaned


def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Non authentifie")

    for user in USERS.values():
        if user["id"] == user_id:
            return user

    request.session.clear()
    raise HTTPException(status_code=401, detail="Session invalide")


@app.post("/auth/login")
def login(req: LoginRequest, request: Request):
    username = req.username.strip().lower()
    user = USERS.get(username)

    if not user:
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    password_hash = _hash_password(req.password, user["password_salt"])
    if not hmac.compare_digest(password_hash, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    chat_session = request.session.get("clearbot_session")
    request.session.clear()
    request.session["user_id"] = user["id"]
    request.session["username"] = user["username"]
    if chat_session:
        request.session["clearbot_session"] = chat_session

    return {"user": _public_user(user)}


@app.get("/auth/me")
def me(user=Depends(get_current_user)):
    return {"user": _public_user(user)}


@app.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"status": "ok"}


@app.get("/chat-session")
def get_chat_session(request: Request):
    return request.session.get("clearbot_session", {
        "messages": [],
        "stage": "idle",
        "pendingData": None,
    })


@app.post("/chat-session")
def save_chat_session(req: ChatSessionRequest, request: Request):
    session_data = {
        "messages": _sanitize_messages(req.messages),
        "stage": req.stage or "chatting",
        "pendingData": req.pendingData,
    }
    request.session["clearbot_session"] = session_data
    return {"status": "ok", **session_data}


@app.delete("/chat-session")
def reset_chat_session(request: Request):
    request.session.pop("clearbot_session", None)
    # Reset le contexte de l'orchestrateur (classification session incluse)
    orchestrator.reset_context()
    return {"status": "ok"}

# ── Initialisation au démarrage ──────────────────────────────────
config       = load_config()
if TEST_MODE:
    class _TestContext:
        def __init__(self):
            self.session_data = {}

        def set_session_data(self, key, value):
            self.session_data[key] = value

    class _TestOrchestrator:
        def __init__(self):
            self.context = _TestContext()
            self.rag_agent = None

        def reset_context(self):
            self.context = _TestContext()

        def chat(self, message):
            normalized = (message or "").lower()
            if "qui es" in normalized:
                return {
                    "response": "Je suis ClearBot, l'assistant Maroclear.",
                    "agent_used": "TestOrchestrator",
                    "route": "identity",
                }
            if "tcs" in normalized or "bancs" in normalized:
                return {
                    "response": "Votre demande semble concerner un incident technique.",
                    "agent_used": "ClassificationAgent",
                    "route": "classification",
                    "classification": "INCIDENT",
                    "needs_glpi": True,
                }
            return {
                "response": "ClearBot a bien reçu votre demande.",
                "agent_used": "TestOrchestrator",
                "route": "test",
            }

    class _TestReglementaireAgent:
        def process(self, message, context):
            return AgentMessage.create_response(
                sender="ReglementaireAgent",
                content="Réponse réglementaire de test.",
                metadata={
                    "agent_used": "ReglementaireAgent",
                    "sources": [],
                    "retrieved_docs_count": 0,
                },
            )

        def reset(self):
            return None

    class _TestAutoDispatcher:
        def process_ticket(self, ticket_data, user=None):
            return {"status": "ok", "message": "Notification de test envoyée."}

    orchestrator = _TestOrchestrator()
    reglementaire_agent = _TestReglementaireAgent()
    regl_context = AgentContext()
    auto_dispatcher = _TestAutoDispatcher()
else:
    orchestrator = build_orchestrator(config)

    # Agent réglementaire
    reglementaire_agent = ReglementaireAgent(config)
    regl_context        = AgentContext()

    # Agent auto-dispatcher
    auto_dispatcher = AutoDispatcherAgent(config)

# ── Schémas de requête ───────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    context: str = "private"  # "public" ou "private"

# ── Route existante : agent général Maroclear ────────────────────
@app.post("/chat")
def chat(req: ChatRequest, request: Request):
    """
    Agent général : classification (incidents/demandes/réclamations)
    + RAG documentaire général Maroclear.
    """
    # Injecter le profil utilisateur dans le contexte de l'orchestrateur
    user_id = request.session.get("user_id")
    if user_id:
        for user in USERS.values():
            if user["id"] == user_id:
                orchestrator.context.set_session_data("user_profile", user["profile"])
                break

    # Stocker le contexte (public/private) pour l'orchestrateur
    orchestrator.context.set_session_data("app_context", req.context)

    try:
        result = orchestrator.chat(req.message)
        return result
    except Exception as exc:
        print(f"[ERREUR /chat] {type(exc).__name__}: {exc}")
        return {
            "response": (
                "Le service de generation de reponse est momentanement indisponible. "
                "Vous pouvez continuer a decrire votre demande, ou reessayer dans un instant."
            ),
            "agent_used": "orchestrator",
            "route": "error",
            "classification": "",
            "priorite": "",
            "statut": "",
            "service": "",
            "systeme": "",
            "needs_glpi": False,
            "rag_sources": [],
            "regl_sources": [],
            "error": str(exc),
        }

# ── Nouvelle route : RAG réglementaire ──────────────────────────
@app.post("/chat-reglementaire")
def chat_reglementaire(req: ChatRequest):
    """
    Agent spécialisé Loi 35-96 + Règlement Général Maroclear.
    Retourne une réponse juridique sourcée avec références d'articles.
    """
    message = AgentMessage.create_query(
        sender  = "user",
        content = req.message,
    )

    try:
        response = reglementaire_agent.process(message, regl_context)
    except Exception as exc:
        print(f"[ERREUR /chat-reglementaire] {type(exc).__name__}: {exc}")
        return {
            "response": (
                "Le module reglementaire est momentanement indisponible. "
                "Veuillez reessayer dans un instant."
            ),
            "agent_used": "ReglementaireAgent",
            "sources": [],
            "retrieved_docs_count": 0,
            "error": str(exc),
        }

    return {
        "response":             response.content,
        "agent_used":           response.metadata.get("agent_used", "ReglementaireAgent"),
        "sources":              response.metadata.get("sources", []),
        "retrieved_docs_count": response.metadata.get("retrieved_docs_count", 0),
    }

# ── Route utilitaire : reset historique réglementaire ───────────
@app.post("/reset-reglementaire")
def reset_reglementaire():
    """Efface l'historique de conversation de l'agent réglementaire."""
    reglementaire_agent.reset()
    return {"status": "ok", "message": "Historique réglementaire réinitialisé"}


# ── Route directe : RAG informationnel (bypass orchestrateur) ────
@app.post("/chat-informationnel")
def chat_informationnel(req: ChatRequest):
    """
    Appel direct au RAGAgent informationnel — bypass le LLM router.
    Utilisé pour l'évaluation afin d'éviter la latence du routage LLM.
    """
    from shared.core.message import AgentMessage as _AgentMessage
    from shared.core.agent_context import AgentContext as _AgentContext

    message = _AgentMessage.create_query(sender="user", content=req.message)
    ctx     = _AgentContext()

    try:
        response = orchestrator.rag_agent.process(message, ctx)
        return {
            "response":             response.content,
            "agent_used":           "RAGAgent",
            "route":                "rag",
            "rag_sources":          response.metadata.get("sources", []),
            "retrieved_docs_count": response.metadata.get("retrieved_docs_count", 0),
        }
    except Exception as exc:
        print(f"[ERREUR /chat-informationnel] {type(exc).__name__}: {exc}")
        return {
            "response":             "Erreur lors de la génération de la réponse.",
            "agent_used":           "RAGAgent",
            "route":                "error",
            "rag_sources":          [],
            "retrieved_docs_count": 0,
            "error":                str(exc),
        }


# ── Route documents : servir les PDFs sources ────────────────────
from fastapi.responses import FileResponse

@app.get("/documents/{filename}")
def get_document(filename: str):
    """Sert un PDF ou Excel source pour consultation par l'affilie."""
    # Chercher dans tous les dossiers de documents
    search_paths = [
        Path(__file__).parent.parent / "agents" / "informationnel_procedural" / "data" / "documents",
        Path(__file__).parent.parent / "agents" / "conseiller_reglementaire" / "data" / "input",
        Path(__file__).parent.parent / "agents" / "conseiller_reglementaire" / "parsing",
    ]

    # Types de fichiers autorisés
    allowed_types = {
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
    }

    for folder in search_paths:
        file_path = folder / filename
        if file_path.exists() and file_path.suffix.lower() in allowed_types:
            return FileResponse(
                path=str(file_path),
                media_type=allowed_types[file_path.suffix.lower()],
                filename=filename,
            )

    raise HTTPException(status_code=404, detail="Document introuvable")


# ── Route feedback : evaluation de satisfaction ──────────────────
class FeedbackRequest(BaseModel):
    rating: int          # 1 a 5 etoiles
    comment: str = ""    # commentaire optionnel
    ticket_id: str = ""  # reference du ticket si disponible


FEEDBACK_FILE = Path(__file__).parent.parent / "data" / "feedbacks.json"


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest, request: Request):
    """Enregistre le feedback de l'affilie apres une interaction."""
    user_id = request.session.get("user_id", "anonymous")
    username = request.session.get("username", "anonymous")

    feedback_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "username": username,
        "rating": max(1, min(5, req.rating)),
        "comment": req.comment[:500],
        "ticket_id": req.ticket_id,
    }

    # Stocker dans un fichier JSON (append)
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    feedbacks = []
    if FEEDBACK_FILE.exists():
        try:
            feedbacks = json.loads(FEEDBACK_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            feedbacks = []

    feedbacks.append(feedback_entry)
    FEEDBACK_FILE.write_text(json.dumps(feedbacks, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"status": "ok", "message": "Merci pour votre retour."}


# ── Route dispatch : envoi email au dispatcher ───────────────────
class DispatchRequest(BaseModel):
    ticket_data: dict


@app.post("/dispatch")
def dispatch(req: DispatchRequest, user=Depends(get_current_user)):
    """
    Déclenché quand l'utilisateur soumet son formulaire.
    Envoie l'email de notification au dispatcher Maroclear.
    Requiert une session authentifiée.
    """
    # Injecter le profil utilisateur dans le ticket_data
    ticket_data = {
        **req.ticket_data,
        "reporterName":     user["profile"].get("reporterName", ""),
        "reporterActivity": user["profile"].get("reporterActivity", ""),
        "institution":      user["profile"].get("institution", ""),
        "reporterEmail":    user["profile"].get("reporterEmail", ""),
        "reporterPhone":    user["profile"].get("reporterPhone", ""),
    }

    message = AgentMessage.create_query(
        sender="user",
        content="dispatch",
        metadata={"ticket_data": ticket_data},
    )

    try:
        response = auto_dispatcher.dispatch(ticket_data)
        return {
            "status":           "ok" if response.metadata.get("email_sent") else "warning",
            "message":          response.content,
            "ticket_id":        response.metadata.get("ticket_id"),
            "email_sent":       response.metadata.get("email_sent", False),
            "dispatcher_email": response.metadata.get("dispatcher_email"),
            "error":            response.metadata.get("error", ""),
        }
    except Exception as exc:
        print(f"[ERREUR /dispatch] {type(exc).__name__}: {exc}")
        return {
            "status":     "error",
            "message":    "Erreur lors de l'envoi de la notification.",
            "email_sent": False,
            "error":      str(exc),
        }
