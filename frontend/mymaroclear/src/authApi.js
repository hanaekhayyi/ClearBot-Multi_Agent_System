const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000";
const LOGIN_URL = process.env.REACT_APP_LOGIN_URL || "http://localhost:5173/my-maroclear.html";

export async function getCurrentUser() {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Non authentifie");
  }

  return response.json();
}

export async function logout() {
  await fetch(`${API_BASE_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export async function getChatSession() {
  const response = await fetch(`${API_BASE_URL}/chat-session`, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Historique indisponible");
  }

  return response.json();
}

export async function saveChatSession({ messages, stage = "chatting", pendingData = null }) {
  await fetch(`${API_BASE_URL}/chat-session`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, stage, pendingData }),
  });
}

export async function resetChatSession() {
  await fetch(`${API_BASE_URL}/chat-session`, {
    method: "DELETE",
    credentials: "include",
  });
}

export function redirectToLogin() {
  window.location.href = LOGIN_URL;
}

export function redirectToPublicPortal() {
  window.location.href = process.env.REACT_APP_PUBLIC_PORTAL_URL || "http://localhost:5173";
}
