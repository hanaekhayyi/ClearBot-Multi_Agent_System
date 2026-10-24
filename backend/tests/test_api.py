"""
test_api.py — Tests d'intégration pour les routes FastAPI.

Teste :
  - Authentification (login/logout)
  - Route /chat (routage orchestrateur)
  - Route /dispatch (envoi email)
  - Route /feedback (collecte avis)
  - Session management
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Crée un client de test FastAPI."""
    from api.api import app
    return TestClient(app)


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — Authentification
# ══════════════════════════════════════════════════════════════════════════════

class TestAuth:
    """Teste les routes d'authentification."""

    def test_login_success(self, client):
        response = client.post("/auth/login", json={
            "username": "asmae.hidra",
            "password": "maroclear123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["reporterName"] == "HIDRA Asmae"

    def test_login_wrong_password(self, client):
        response = client.post("/auth/login", json={
            "username": "asmae.hidra",
            "password": "wrong_password",
        })
        assert response.status_code == 401

    def test_login_unknown_user(self, client):
        response = client.post("/auth/login", json={
            "username": "unknown_user",
            "password": "test",
        })
        assert response.status_code == 401

    def test_me_without_login(self, client):
        # Nouveau client sans session
        from api.api import app
        fresh_client = TestClient(app)
        response = fresh_client.get("/auth/me")
        assert response.status_code == 401

    def test_me_after_login(self, client):
        # Login d'abord
        client.post("/auth/login", json={
            "username": "asmae.hidra",
            "password": "maroclear123",
        })
        response = client.get("/auth/me")
        assert response.status_code == 200
        assert response.json()["user"]["reporterName"] == "HIDRA Asmae"

    def test_logout(self, client):
        client.post("/auth/login", json={
            "username": "asmae.hidra",
            "password": "maroclear123",
        })
        response = client.post("/auth/logout")
        assert response.status_code == 200
        # Après logout, /auth/me doit échouer
        response = client.get("/auth/me")
        assert response.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — Route /chat
# ══════════════════════════════════════════════════════════════════════════════

class TestChat:
    """Teste la route /chat (orchestrateur)."""

    def test_chat_returns_response(self, client):
        # Login
        client.post("/auth/login", json={
            "username": "asmae.hidra",
            "password": "maroclear123",
        })
        response = client.post("/chat", json={
            "message": "qui es-tu ?",
            "context": "private",
        })
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "ClearBot" in data["response"]

    def test_chat_identity_public(self, client):
        response = client.post("/chat", json={
            "message": "qui es-tu ?",
            "context": "public",
        })
        assert response.status_code == 200
        data = response.json()
        assert "Maroclear" in data["response"]

    def test_chat_classification_route(self, client):
        client.post("/auth/login", json={
            "username": "asmae.hidra",
            "password": "maroclear123",
        })
        response = client.post("/chat", json={
            "message": "je n'arrive pas à accéder à TCS BaNCS",
            "context": "private",
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("agent_used") in ("ClassificationAgent", "SupportClassificationAgent")


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — Route /feedback
# ══════════════════════════════════════════════════════════════════════════════

class TestFeedback:
    """Teste la route /feedback."""

    def test_feedback_success(self, client):
        response = client.post("/feedback", json={
            "rating": 5,
            "comment": "Très utile !",
            "ticket_id": "TKT-TEST001",
        })
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_feedback_without_comment(self, client):
        response = client.post("/feedback", json={
            "rating": 3,
            "comment": "",
            "ticket_id": "",
        })
        assert response.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# TESTS — Session management
# ══════════════════════════════════════════════════════════════════════════════

class TestSession:
    """Teste la gestion des sessions de chat."""

    def test_get_empty_session(self, client):
        response = client.get("/chat-session")
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data

    def test_save_and_get_session(self, client):
        # Sauvegarder
        client.post("/chat-session", json={
            "messages": [{"id": "1", "from": "bot", "text": "Bonjour", "time": "10:00"}],
            "stage": "chatting",
            "pendingData": None,
        })
        # Récupérer
        response = client.get("/chat-session")
        data = response.json()
        assert len(data["messages"]) >= 1

    def test_delete_session(self, client):
        # Sauvegarder puis supprimer
        client.post("/chat-session", json={
            "messages": [{"id": "1", "from": "bot", "text": "Test", "time": "10:00"}],
            "stage": "chatting",
            "pendingData": None,
        })
        response = client.delete("/chat-session")
        assert response.status_code == 200
