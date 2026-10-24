const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const PRIVATE_APP_URL = import.meta.env.VITE_PRIVATE_APP_URL || "http://localhost:3000";

export async function login(username, password, remember) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, remember }),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Identifiants invalides.");
  }

  return response.json();
}

export function redirectToPrivateApp() {
  window.location.href = PRIVATE_APP_URL;
}
