import { useState } from "react";
import LOGO from "./assets/Logo_de_Maroclear (2).png";
import BG from "./assets/Image-11-web.jpg";

export default function MyMaroclear({ onLogin, onBack }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!username || !password) {
      setError("Veuillez remplir tous les champs.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      if (onLogin) {
        await onLogin({ username, password, remember });
      }
    } catch (err) {
      setError(err.message || "Connexion impossible.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 99999,
      backgroundImage: `url(${BG})`,
      backgroundSize: "cover", backgroundPosition: "center",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "'Archivo', sans-serif"
    }}>
      {/* Overlay */}
      <div style={{
        position: "absolute", inset: 0,
        background: "rgba(0,0,0,0.35)"
      }}/>

      {/* Card */}
      <div style={{
        position: "relative", zIndex: 1,
        background: "rgba(255,255,255,0.92)",
        backdropFilter: "blur(10px)",
        borderRadius: 12,
        padding: "48px 52px",
        width: 420,
        boxShadow: "0 20px 60px rgba(0,0,0,0.25)"
      }}>
        {/* Logo */}
        <div style={{ 
  display: "flex", 
  alignItems: "center", 
  justifyContent: "center",
  marginBottom: 20, 
  borderRadius: 5, 
  padding: "13px" 
}}>
  <img src={LOGO} alt="Maroclear" style={{ height: 80, objectFit: "contain", display: "block" }}/>
</div>

        {/* Title */}
        <h2 style={{ textAlign: "center", margin: "0 0 4px", fontSize: 22, fontWeight: 700, color: "#282e3c" }}>
          My Maroclear
        </h2>
        <p style={{ textAlign: "center", margin: "0 0 28px", fontSize: 13, color: "#6c757d" }}>
          Espace réservé
        </p>

        {/* Error */}
        {error && (
          <div style={{
            background: "#fde8e8", border: "1px solid #f5c6c6",
            borderRadius: 8, padding: "10px 14px",
            fontSize: 13, color: "#c0392b", marginBottom: 16
          }}>{error}</div>
        )}

        {/* Username */}
        <div style={{ position: "relative", marginBottom: 14 }}>
          <span style={{
            position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)",
            color: "#8cc63f", fontSize: 16
          }}><svg width="16" height="16" viewBox="0 0 24 24" fill="none">
  <circle cx="12" cy="8" r="4" stroke="#8cc63f" strokeWidth="2"/>
  <path d="M4 20c0-4.418 3.582-8 8-8s8 3.582 8 8" stroke="#8cc63f" strokeWidth="2" strokeLinecap="round"/>
</svg></span>
          <input
            type="text"
            placeholder="Nom d'utilisateur"
            value={username}
            onChange={e => setUsername(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleLogin()}
            style={{
              width: "100%", padding: "13px 14px 13px 42px",
              border: "1.5px solid #dee2e6", borderRadius: 8,
              fontSize: 14, color: "#282e3c", background: "white",
              boxSizing: "border-box", outline: "none",
              fontFamily: "inherit"
            }}
            onFocus={e => e.target.style.borderColor = "#f5821f"}
            onBlur={e => e.target.style.borderColor = "#dee2e6"}
          />
        </div>

        {/* Password */}
        <div style={{ position: "relative", marginBottom: 16 }}>
          <span style={{
            position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)",
            color: "#8cc63f", fontSize: 16
          }}><svg width="16" height="16" viewBox="0 0 24 24" fill="none">
  <rect x="5" y="11" width="14" height="10" rx="2" stroke="#8cc63f" strokeWidth="2"/>
  <path d="M8 11V7a4 4 0 018 0v4" stroke="#8cc63f" strokeWidth="2" strokeLinecap="round"/>
</svg></span>
          <input
            type="password"
            placeholder="Mot de passe"
            value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleLogin()}
            style={{
              width: "100%", padding: "13px 14px 13px 42px",
              border: "1.5px solid #dee2e6", borderRadius: 8,
              fontSize: 14, color: "#282e3c", background: "white",
              boxSizing: "border-box", outline: "none",
              fontFamily: "inherit"
            }}
            onFocus={e => e.target.style.borderColor = "#f5821f"}
            onBlur={e => e.target.style.borderColor = "#dee2e6"}
          />
        </div>

        {/* Remember me */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 22 }}>
          <input
            type="checkbox"
            id="remember"
            checked={remember}
            onChange={e => setRemember(e.target.checked)}
            style={{ accentColor: "#f5821f", width: 15, height: 15 }}
          />
          <label htmlFor="remember" style={{ fontSize: 13, color: "#282e3c", cursor: "pointer" }}>
            Se souvenir de moi
          </label>
        </div>

        {/* Login button */}
        <button
          onClick={handleLogin}
          disabled={loading}
          style={{
            width: "100%", padding: "14px",
            background: loading ? "#e9a96e" : "#f5821f",
            color: "white", border: "none", borderRadius: 8,
            fontSize: 15, fontWeight: 700, letterSpacing: 1.5,
            cursor: loading ? "default" : "pointer",
            fontFamily: "inherit", transition: "background 0.2s",
            marginBottom: 18
          }}
        >
          {loading ? "CONNEXION..." : "CONNEXION"}
        </button>

        {/* Forgot password */}
        <div style={{ textAlign: "center" }}>
          <span style={{ fontSize: 13, color: "#f5821f", cursor: "pointer", textDecoration: "underline" }}>
            Mot de passe oublié ?
          </span>
        </div>

        {/* Back */}
        <div style={{ textAlign: "center", marginTop: 16 }}>
          <span
            onClick={onBack}
            style={{ fontSize: 12, color: "#6c757d", cursor: "pointer" }}
          >
            ← Retour au site
          </span>
        </div>
      </div>
    </div>
  );
}
