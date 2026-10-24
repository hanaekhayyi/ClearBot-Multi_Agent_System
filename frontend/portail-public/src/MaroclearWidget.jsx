import { useState, useRef, useEffect, useCallback } from "react";

const C = {
  orange:      "#f5821f",
  orangeDark:  "#c46819",
  orangeLight: "#fde6d2",
  green:       "#8cc63f",
  dark:        "#282e3c",
  darkMid:     "#495057",
  white:       "#FFFFFF",
  lightGray:   "#f7f7f8",
  midGray:     "#e9ecef",
  border:      "#dee2e6",
  textGray:    "#6c757d",
  textDark:    "#282e3c",
};


const CONTEXT_BUTTONS = {
  welcome_public: [
    { label: "Qu'est-ce que Maroclear ?", text: "Qu'est-ce que Maroclear ?" },
    { label: "Devenir affilié", text: "Comment devenir affilié à Maroclear ?" },
    { label: "Accéder à My Maroclear", text: "Comment accéder à My Maroclear ?" },
  ],
  after_incident: [
    { label: "Statut de mon ticket", text: "Quel est le statut de mon ticket ?" },
    { label: "Autre problème", text: "J'ai un autre problème à signaler" },
  ],
  connection_issue: [
    { label: "Mot de passe oublié", text: "J'ai oublié mon mot de passe" },
    { label: "Compte bloqué", text: "Mon compte est bloqué" },
  ],
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const MY_MAROCLEAR_LOGIN_URL = "/my-maroclear.html";

const PRIVATE_SPACE_REDIRECT_TEXT = `Pour déclarer un problème ou un incident, vous devez vous connecter à votre espace privé MyMaroclear.

Une fois connecté, vous pourrez créer une déclaration avec les informations nécessaires : objet, service concerné, système impacté, description et pièces jointes.

Je peux toutefois répondre ici à vos questions générales sur Maroclear.`;

const PRIVATE_SPACE_BUTTONS = [
  { label: "Se connecter à MyMaroclear", text: "Se connecter à MyMaroclear", action: "login" },
];

function normalizeText(text) {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function isPrivateIssueDeclaration(text) {
  const normalized = normalizeText(text);
  const issueKeywords = [
    "j ai un probleme",
    "jai un probleme",
    "probleme",
    "problemee",
    "problemme",
    "incident",
    "panne",
    "bug",
    "erreur",
    "bloque",
    "bloquee",
    "ne marche pas",
    "ne fonctionne pas",
    "impossible",
    "reclamation",
    "reclamer",
    "declarer",
    "signaler",
  ];

  const generalQuestionStarters = [
    "qu est-ce",
    "c est quoi",
    "comment acceder",
    "comment devenir",
    "quel est",
    "quels sont",
    "quelle est",
  ];

  if (generalQuestionStarters.some((starter) => normalized.startsWith(starter))) {
    return false;
  }

  return issueKeywords.some((keyword) => normalized.includes(keyword));
}

function openMyMaroclearLogin() {
  window.open(MY_MAROCLEAR_LOGIN_URL, "_blank", "noopener,noreferrer");
}

async function loadChatSession() {
  const response = await fetch(`${API_BASE_URL}/chat-session`, {
    credentials: "include",
  });
  if (!response.ok) return { messages: [] };
  return response.json();
}

async function saveChatSession(messages) {
  await fetch(`${API_BASE_URL}/chat-session`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, stage: "chatting", pendingData: null }),
  });
}

async function resetChatSession() {
  await fetch(`${API_BASE_URL}/chat-session`, {
    method: "DELETE",
    credentials: "include",
  });
}

function nowTime() {
  return new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

function formatText(text) {
  // Tableaux markdown → HTML table
  const lines = text.split("\n");
  let inTable = false;
  let tableHtml = "";
  const processed = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const isTableRow = /^\|(.+)\|$/.test(line.trim());
    const isSeparator = /^\|[\s\-:|]+\|$/.test(line.trim());

    if (isTableRow && !isSeparator) {
      if (!inTable) { inTable = true; tableHtml = '<table style="width:100%;border-collapse:collapse;font-size:12px;margin:8px 0;">'; }
      const cells = line.trim().slice(1, -1).split("|").map(c => c.trim());
      const tag = tableHtml.includes("<tr>") ? "td" : "th";
      tableHtml += "<tr>" + cells.map(c =>
        `<${tag} style="border:1px solid #e0e0e0;padding:4px 8px;text-align:left;${tag === 'th' ? 'background:#f5f5f5;font-weight:600;' : ''}">${c}</${tag}>`
      ).join("") + "</tr>";
    } else if (isSeparator) {
      continue;
    } else {
      if (inTable) { tableHtml += "</table>"; processed.push(tableHtml); tableHtml = ""; inTable = false; }
      processed.push(line);
    }
  }
  if (inTable) { tableHtml += "</table>"; processed.push(tableHtml); }

  return processed.join("\n")
    .replace(/^### (.+)$/gm, '<div style="font-size:13px;font-weight:700;margin:12px 0 4px;color:#1a1a1a;">$1</div>')
    .replace(/^## (.+)$/gm, '<div style="font-size:14px;font-weight:700;margin:14px 0 6px;color:#1a1a1a;">$1</div>')
    .replace(/^---$/gm, '<hr style="border:none;border-top:1px solid #e5e5e5;margin:10px 0;"/>')
    .replace(/^> \*(.+?)\*$/gm, '<div style="border-left:3px solid #f5821f;padding:4px 10px;margin:6px 0;font-style:italic;font-size:12px;color:#555;background:#fef9f4;">$1</div>')
    .replace(/^> (.+)$/gm, '<div style="border-left:3px solid #ddd;padding:4px 10px;margin:6px 0;font-size:12px;color:#555;">$1</div>')
    .replace(/^\d+\.\s+(.+)$/gm, '<div style="padding-left:16px;margin:2px 0;">• $1</div>')
    .replace(/^[-*]\s+(.+)$/gm, '<div style="padding-left:16px;margin:2px 0;">• $1</div>')
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.*?)`/g, `<code style="background:#f0f0f0;padding:1px 5px;border-radius:4px;font-size:12px;font-family:monospace">$1</code>`)
    .replace(/\n/g, "<br/>");
}

function Avatar({ isUser }) {
  if (isUser) return (
    <div style={{
      width: 28, height: 28, borderRadius: "50%",
      background: C.dark, display: "flex", alignItems: "center",
      justifyContent: "center", flexShrink: 0,
      fontSize: 11, color: "white", fontWeight: 700
    }}>A</div>
  );
  return (
    <div style={{
      width: 28, height: 28, borderRadius: "50%",
      background: `linear-gradient(135deg, ${C.orange}, ${C.orangeDark})`,
      display: "flex", alignItems: "center", justifyContent: "center",
      flexShrink: 0
    }}>
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="8" r="3.5" stroke="white" strokeWidth="2"/>
        <path d="M5 20c0-3.866 3.134-7 7-7s7 3.134 7 7" stroke="white" strokeWidth="2" strokeLinecap="round"/>
        <circle cx="19" cy="6" r="2.5" fill={C.green}/>
      </svg>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", gap: 7, alignItems: "flex-end", marginBottom: 10 }}>
      <Avatar />
      <div style={{
        background: C.white, border: `1px solid ${C.border}`,
        borderRadius: "0 12px 12px 12px",
        padding: "10px 14px", display: "flex", gap: 4, alignItems: "center",
      }}>
        {[0,1,2].map(i => (
          <div key={i} style={{
            width: 5, height: 5, borderRadius: "50%",
            background: C.orange, opacity: 0.7,
            animation: `mcBounce 1.2s ease-in-out ${i * 0.2}s infinite`
          }}/>
        ))}
      </div>
    </div>
  );
}

function RefreshIcon({ size = 14, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M20 6v5h-5" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M4 18v-5h5" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M18.5 9A7 7 0 0 0 6.3 6.8L4 9" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M5.5 15A7 7 0 0 0 17.7 17.2L20 15" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

function CloseIcon({ size = 13, color = "currentColor" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M18 6 6 18" stroke={color} strokeWidth="2.4" strokeLinecap="round"/>
      <path d="m6 6 12 12" stroke={color} strokeWidth="2.4" strokeLinecap="round"/>
    </svg>
  );
}

function Message({ msg }) {
  const isUser = msg.from === "user";

  if (msg.type === "system") return (
    <div style={{ textAlign: "center", margin: "10px 0" }}>
      <span style={{ fontSize: 11, color: C.textGray, background: C.midGray, borderRadius: 20, padding: "3px 12px" }}>
        {msg.text}
      </span>
    </div>
  );

  // Badges classification
  const badges = [];
  if (msg.classification === "INCIDENT")
    badges.push({ label: "INCIDENT", color: "#c0392b", bg: "#fde8e8" });
  else if (msg.classification === "DEMANDE")
    badges.push({ label: "DEMANDE", color: "#2980b9", bg: "#e8f4fd" });
  else if (msg.classification === "RECLAMATION")
    badges.push({ label: "RÉCLAMATION", color: "#8e44ad", bg: "#f5e8fd" });

  if (msg.priorite === "P1") badges.push({ label: "P1 URGENT", color: "#c0392b", bg: "#fde8e8" });
  else if (msg.priorite === "P2") badges.push({ label: "P2", color: "#e67e22", bg: "#fef3e8" });
  else if (msg.priorite === "P3") badges.push({ label: "P3", color: "#d4ac0d", bg: "#fefde8" });
  else if (msg.priorite === "P4") badges.push({ label: "P4", color: "#27ae60", bg: "#eafde8" });

  if (msg.rag_sources?.length > 0)
    badges.push({ label: "📄 Sources RAG", color: "#2c5ab5", bg: "#e8f0fe" });

  if (msg.agent_used === "ReglementaireAgent")
    badges.push({ label: "⚖️ Réglementaire", color: "#5b2d8e", bg: "#f0e8fd" });

  return (
    <div style={{
      display: "flex", gap: 7,
      flexDirection: isUser ? "row-reverse" : "row",
      alignItems: "flex-end", marginBottom: 8,
      animation: "mcFade 0.25s ease"
    }}>
      <Avatar isUser={isUser} />
      <div style={{ maxWidth: "80%", display: "flex", flexDirection: "column", alignItems: isUser ? "flex-end" : "flex-start" }}>
        
        {/* Badges (seulement pour le bot) */}
        {!isUser && badges.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 5 }}>
            {badges.map((b, i) => (
              <span key={i} style={{
                background: b.bg, color: b.color,
                borderRadius: 10, padding: "2px 8px",
                fontSize: 10, fontWeight: 700, letterSpacing: "0.05em"
              }}>{b.label}</span>
            ))}
          </div>
        )}

        {/* Bulle message */}
        <div style={{
          background: isUser ? `linear-gradient(135deg, ${C.orange}, ${C.orangeDark})` : C.white,
          color: isUser ? "white" : C.textDark,
          border: isUser ? "none" : `1px solid ${C.border}`,
          borderRadius: isUser ? "12px 0 12px 12px" : "0 12px 12px 12px",
          padding: "9px 13px", fontSize: 13, lineHeight: 1.65,
          boxShadow: isUser ? `0 2px 10px rgba(245,130,31,0.25)` : "0 1px 4px rgba(0,0,0,0.05)"
        }} dangerouslySetInnerHTML={{ __html: formatText(msg.text) }} />

        {/* Ticket GLPI */}
        {msg.needs_glpi && (
          <div style={{
            marginTop: 5, padding: "4px 10px",
            background: "#fef3e8", borderRadius: 6,
            fontSize: 11, color: "#e67e22", fontWeight: 600
          }}>
            ⚠️ Un ticket GLPI doit être créé
          </div>
        )}

        {/* Sources légales (RAG réglementaire) */}
        {/* Sources légales (RAG réglementaire) */}
        {(msg.regl_sources_detailed?.length > 0 || msg.regl_sources?.length > 0) && (
          <div style={{ marginTop: 8 }}>
            <div
              onClick={(e) => {
                const panel = e.currentTarget.nextElementSibling;
                panel.style.display = panel.style.display === "none" ? "block" : "none";
              }}
              style={{
                display: "inline-flex", alignItems: "center", gap: 5,
                background: "#f5f0ff", border: "1px solid #d4c0ff",
                borderRadius: 6, padding: "5px 10px",
                fontSize: 11, color: "#6b3fa0",
                fontWeight: 600, cursor: "pointer",
                userSelect: "none",
              }}
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <path d="M14 2v6h6"/>
              </svg>
              Afficher les sources ({msg.regl_sources_detailed?.length || msg.regl_sources?.length})
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6 9l6 6 6-6"/>
              </svg>
            </div>
            <div style={{ display: "none", marginTop: 6 }}>
              {msg.regl_sources_detailed?.length > 0 ? (
                msg.regl_sources_detailed.map((src, i) => (
                  <div key={i} style={{
                    background: "#faf8ff", border: "1px solid #ede5ff",
                    borderRadius: 6, padding: "8px 10px", marginBottom: 4,
                    fontSize: 11, color: "#4a3080", lineHeight: 1.5,
                  }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                        <span style={{ fontWeight: 700 }}>⚖️</span>
                        <span style={{ fontWeight: 600 }}>{src.article || "—"}</span>
                      </div>
                      {src.page && <span style={{ color: "#888", fontSize: 10, flexShrink: 0 }}>p. {src.page}</span>}
                    </div>
                    {src.hierarchy && (
                      <div style={{ color: "#7c6b9e", marginTop: 3, fontSize: 10, paddingLeft: 22 }}>
                        {src.hierarchy.split(" > ").map((part, j) => (
                          <span key={j}>
                            {j > 0 && <span style={{ margin: "0 3px", color: "#bbb" }}>›</span>}
                            <span>{part.length > 50 ? part.slice(0, 50) + "…" : part}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                msg.regl_sources.map((source, i) => (
                  <div key={i} style={{
                    background: "#faf8ff", border: "1px solid #ede5ff",
                    borderRadius: 6, padding: "6px 10px", marginBottom: 4,
                    fontSize: 11, color: "#4a3080", lineHeight: 1.4,
                    display: "flex", alignItems: "flex-start", gap: 6,
                  }}>
                    <span style={{ color: "#6b3fa0", fontWeight: 700, flexShrink: 0 }}>⚖️</span>
                    <span>{source}</span>
                  </div>
                ))
              )}
            </div>
            {(() => {
              const pdfSources = new Set();
              if (msg.regl_sources_detailed?.length > 0) {
                msg.regl_sources_detailed.forEach(src => {
                  const corpus = src.corpus || "";
                  if (corpus === "actualite_historique") {
                    pdfSources.add(JSON.stringify({ name: "Actualités Historique Maroclear", file: "ACTUALIT%C3%89S%20HISTORIQUE.pdf" }));
                  } else if (corpus === "ammc_recueil_docling") {
                    pdfSources.add(JSON.stringify({ name: "Recueil AMMC (Mars 2026)", file: "Recueil_AMMC_VF_%20Mars%202026.pdf" }));
                  } else {
                    const doc = src.document || "";
                    if (doc.includes("Loi") || doc.includes("Arrêté") || doc.includes("Circulaire") || doc.includes("Règlement") || doc.includes("Décret") || doc.includes("DAHIR")) {
                      pdfSources.add(JSON.stringify({ name: "Recueil AMMC (Mars 2026)", file: "Recueil_AMMC_VF_%20Mars%202026.pdf" }));
                    }
                  }
                });
              }
              if (msg.regl_sources?.length > 0) {
                msg.regl_sources.forEach(src => {
                  if (src.includes("glossaire")) {
                    pdfSources.add(JSON.stringify({ name: "Glossaire Maroclear", file: "glossaire_maroclear.xlsx" }));
                  } else if (src.includes("Règles de fonctionnement") || src.includes("DO_RAP")) {
                    pdfSources.add(JSON.stringify({ name: "Règles de fonctionnement de Maroclear", file: "DO_RAP_R%C3%A8gles%20de%20fonctionnement%20de%20Maroclear_20190601_V2.2.pdf" }));
                  } else if (src.includes("Sans_titre") || src.includes("cf85a1c4")) {
                    pdfSources.add(JSON.stringify({ name: "Document institutionnel Maroclear", file: "cf85a1c4-63ef-4720-bc70-ebfe9a370888_Sans_titre.pdf" }));
                  } else if (src.includes("ACTUALIT")) {
                    pdfSources.add(JSON.stringify({ name: "Actualités Historique Maroclear", file: "ACTUALIT%C3%89S%20HISTORIQUE.pdf" }));
                  } else if (src.includes("Loi") || src.includes("Arrêté") || src.includes("Circulaire") || src.includes("DAHIR")) {
                    pdfSources.add(JSON.stringify({ name: "Recueil AMMC (Mars 2026)", file: "Recueil_AMMC_VF_%20Mars%202026.pdf" }));
                  }
                });
              }
              const unique = [...pdfSources].map(s => JSON.parse(s));
              if (unique.length === 0) return null;
              return unique.map((src, i) => (
                <a key={i}
                  href={`http://localhost:8000/documents/${src.file}`}
                  target="_blank" rel="noopener noreferrer"
                  style={{
                    display: "inline-flex", alignItems: "center", gap: 5,
                    background: "#eef6ff", border: "1px solid #c0d8f0",
                    borderRadius: 6, padding: "5px 10px", marginTop: 6, marginRight: 4,
                    fontSize: 11, color: "#185fa5", textDecoration: "none",
                    fontWeight: 600,
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <path d="M14 2v6h6"/>
                    <path d="M12 18v-6"/>
                    <path d="M9 15l3 3 3-3"/>
                  </svg>
                  {src.name}
                </a>
              ));
            })()}
          </div>
        )}

        <span style={{ fontSize: 10, color: C.textGray, marginTop: 3 }}>{msg.time}</span>
      </div>
    </div>
  );
}
function FeedbackPanel({ onSubmit }) {
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = () => {
    if (rating === 0) return;
    onSubmit({ rating, comment });
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div style={{
        background: "#f0f7ff", border: "1px solid #c0d8f0",
        borderRadius: 10, padding: "12px 14px", marginBottom: 8,
        textAlign: "center", animation: "mcFade 0.3s ease",
      }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#185fa5" }}>Merci pour votre retour !</div>
        <div style={{ fontSize: 11, color: C.textGray, marginTop: 4 }}>Votre avis nous aide à améliorer ClearBot.</div>
      </div>
    );
  }

  return (
    <div style={{
      background: C.white, border: `1px solid ${C.border}`,
      borderRadius: 10, padding: "12px 14px", marginBottom: 8,
      animation: "mcFade 0.3s ease",
    }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: C.textDark, marginBottom: 8 }}>
        Cette réponse vous a-t-elle aidé ?
      </div>
      <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
        {[1, 2, 3, 4, 5].map(star => (
          <span
            key={star}
            onClick={() => setRating(star)}
            onMouseEnter={() => setHover(star)}
            onMouseLeave={() => setHover(0)}
            style={{
              cursor: "pointer", fontSize: 22,
              color: star <= (hover || rating) ? "#f5821f" : "#ddd",
              transition: "color 0.15s, transform 0.15s",
              transform: star <= (hover || rating) ? "scale(1.1)" : "scale(1)",
            }}
          >
            ★
          </span>
        ))}
        {rating > 0 && (
          <span style={{ fontSize: 11, color: C.textGray, marginLeft: 6, alignSelf: "center" }}>
            {["", "Très insatisfait", "Insatisfait", "Correct", "Satisfait", "Très satisfait"][rating]}
          </span>
        )}
      </div>
      <textarea
        value={comment}
        onChange={e => setComment(e.target.value)}
        placeholder="Un commentaire ? (optionnel)"
        rows={2}
        style={{
          width: "100%", border: `1px solid ${C.border}`,
          borderRadius: 8, padding: "8px 10px",
          fontSize: 12, fontFamily: "inherit",
          resize: "none", background: C.lightGray,
          marginBottom: 8,
        }}
      />
      <button
        onClick={handleSubmit}
        disabled={rating === 0}
        style={{
          width: "100%", padding: "8px",
          borderRadius: 8, border: "none",
          background: rating > 0 ? C.orange : C.midGray,
          color: "white", fontWeight: 600, fontSize: 12,
          cursor: rating > 0 ? "pointer" : "default",
          fontFamily: "inherit",
        }}
      >
        Envoyer mon avis
      </button>
    </div>
  );
}

function SuggestionChips({ buttons, onSelect }) {
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "0 0 10px 35px" }}>
      {buttons.map((btn, i) => (
        <button key={i} onClick={() => onSelect(btn)} style={{
          background: C.white, border: `1px solid ${C.border}`,
          borderRadius: 16, padding: "5px 12px",
          fontSize: 12, color: C.darkMid, cursor: "pointer",
          fontWeight: 500, fontFamily: "inherit", whiteSpace: "nowrap"
        }}
        onMouseOver={e => { e.currentTarget.style.background = C.orangeLight; e.currentTarget.style.borderColor = C.orange; }}
        onMouseOut={e => { e.currentTarget.style.background = C.white; e.currentTarget.style.borderColor = C.border; }}>
          {btn.label}
        </button>
      ))}
    </div>
  );
}

export default function MaroclearWidget({ zIndexOverride } = {}) {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [showProactive, setShowProactive] = useState(false);
  const [proactiveDismissed, setProactiveDismissed] = useState(false);
  const [messages, setMessages] = useState([]);
  const [contextButtons, setContextButtons] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [typing, setTyping] = useState(false);
  const [unread, setUnread] = useState(0);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const initialized = useRef(false);
  const hydrated = useRef(false);
  const messagesRef = useRef([]);

  const pushMessage = useCallback((msg) => {
    setMessages(prev => [...prev, { id: Date.now() + Math.random(), time: nowTime(), ...msg }]);
  }, []);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    // Portail public : pas de chargement de session serveur (sécurité)
    hydrated.current = true;
  }, []);

  // Portail public : pas de sauvegarde de session serveur
  useEffect(() => {}, [messages]);

  // ⚙️ CONFIG OPENROUTER — mets ta vraie clé et le modèle voulu
  
  // ✅ NOUVEAU sendToAPI
  const sendToAPI = useCallback(async (userText) => {
    setTyping(true);
    setContextButtons([]);

    if (isPrivateIssueDeclaration(userText)) {
      setTyping(false);
      pushMessage({
        from: "bot",
        text: PRIVATE_SPACE_REDIRECT_TEXT,
      });
      setContextButtons(PRIVATE_SPACE_BUTTONS);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText, context: "public" }),
      });

      if (!response.ok) {
        const errBody = await response.text();
        console.error("[ClearBot] HTTP " + response.status + ":", errBody);
        throw new Error("HTTP " + response.status);
      }

      const data = await response.json();
      const replyText = data.response || "Je n'ai pas pu traiter votre demande.";

      // Enrichir le message avec les métadonnées de l'orchestrateur
      const botMsg = {
        from: "bot",
        text: replyText,
        classification: data.classification || null,
        priorite: data.priorite || null,
        agent_used: data.agent_used || null,
        needs_glpi: data.needs_glpi || false,
        rag_sources: data.rag_sources || [],
        regl_sources: data.regl_sources || [],
        regl_sources_detailed: data.regl_sources_detailed || [],
      };

      setTyping(false);
      pushMessage(botMsg);

      // Suggestions contextuelles selon la classification
      const classif = data.classification || "";
      if (classif === "INCIDENT") 
        setContextButtons(CONTEXT_BUTTONS.after_incident);
      else if (classif === "DEMANDE" || replyText.toLowerCase().includes("mot de passe"))
        setContextButtons(CONTEXT_BUTTONS.connection_issue);

    } catch (err) {
      console.error("[ClearBot] Erreur:", err);
      setTyping(false);
      pushMessage({ from: "bot", text: "Erreur de connexion au serveur. Vérifiez que le backend est lancé." });
    }
  }, [pushMessage]);

  // handleSend simplifié (plus besoin de passer l'historique)
  const handleSend = useCallback(() => {
    const txt = inputValue.trim();
    if (!txt) return;
    setInputValue("");
    pushMessage({ from: "user", text: txt });
    sendToAPI(txt);
  }, [inputValue, pushMessage, sendToAPI]);

  const handleChipSelect = useCallback((btn) => {
    setContextButtons([]);

    if (btn.action === "login") {
      pushMessage({ from: "user", text: btn.text });
      // Sauvegarder la conversation dans localStorage avant redirection
      // Pour que MyMaroclear puisse la recuperer apres login
      const conversationToTransfer = messagesRef.current.filter(m => m.from === "user" || m.from === "bot");
      if (conversationToTransfer.length > 0) {
        localStorage.setItem("clearbot_public_conversation", JSON.stringify(conversationToTransfer));
      }
      openMyMaroclearLogin();
      return;
    }

    pushMessage({ from: "user", text: btn.text });
    sendToAPI(btn.text);
  }, [pushMessage, sendToAPI]);

  const handleReset = useCallback(() => {
    resetChatSession().catch(() => {});
    setMessages([]);
    messagesRef.current = [];
    setContextButtons([]);
    setInputValue("");
    setTyping(false);
    setUnread(0);
    setFeedbackSent(false);

    setTimeout(() => {
      pushMessage({
        from: "bot",
        text: "Bonjour, je suis ClearBot, l'assistant de Maroclear. Posez-moi votre question ou choisissez une option.",
      });
      setContextButtons(CONTEXT_BUTTONS.welcome_public);
    }, 100);
  }, [pushMessage]);

  const handleFeedback = async ({ rating, comment }) => {
    try {
      await fetch(`${API_BASE_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating, comment, ticket_id: "" }),
      });
      setFeedbackSent(true);
    } catch (err) {
      console.warn("[ClearBot] Feedback non envoyé:", err);
    }
  };

  // Init messages silencieusement (pas d'ouverture auto du chat)
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    // Affiche la bulle proactive après 1.5s
    setTimeout(() => {
      setShowProactive(true);
      setUnread(1);
    }, 1500);
  }, []);

  useEffect(() => {
    if (open) {
      setUnread(0);
      setShowProactive(false);
      // Afficher le greeting si pas encore de messages
      if (messagesRef.current.length === 0) {
        pushMessage({
          from: "bot",
          text: "Bonjour, je suis ClearBot, l'assistant de Maroclear. Posez-moi votre question ou choisissez une option.",
        });
        setContextButtons(CONTEXT_BUTTONS.welcome_public);
      }
      setTimeout(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
        inputRef.current?.focus();
      }, 80);
    }
  }, [open]);

  const handleOpenFromProactive = () => {
    setShowProactive(false);
    setProactiveDismissed(true);
    setOpen(true);
  };

  const z = zIndexOverride ?? 9998;

  return (
    <>
      <style>{`
        @keyframes mcBounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-5px)}}
        @keyframes mcFade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
        @keyframes mcPop{from{opacity:0;transform:scale(0.9) translateY(16px)}to{opacity:1;transform:scale(1) translateY(0)}}
        @keyframes mcSlideUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
        @keyframes mcPulse{0%,100%{box-shadow:0 0 0 0 rgba(245,130,31,0.4)}50%{box-shadow:0 0 0 10px rgba(245,130,31,0)}}
      `}</style>

      {/* Bouton invisible déclenché par la sidebar HTML */}
      <button id="clearbot-open" onClick={() => setOpen(v => !v)} style={{ display: "none" }} />

      {/* Bulle proactive style DataCamp */}
      {showProactive && !open && (
        <div style={{
          position: "fixed", bottom: 90, right: 24,
          zIndex: z + 1,
          animation: "mcSlideUp 0.4s cubic-bezier(0.34,1.56,0.64,1)",
          maxWidth: 300,
        }}>
          {/* Bouton fermer la bulle */}
          <button
            onClick={() => { setShowProactive(false); setProactiveDismissed(true); setUnread(0); }}
            style={{
              position: "absolute", top: -8, right: -8,
              width: 22, height: 22, borderRadius: "50%",
              background: C.dark, border: "2px solid white",
              color: "white", fontSize: 11, cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center",
              zIndex: 1, lineHeight: 1
            }}>✕</button>

          {/* Bulle de message */}
          <div
            onClick={handleOpenFromProactive}
            style={{
              background: C.orange,
              borderRadius: "18px 18px 4px 18px",
              padding: "14px 18px",
              cursor: "pointer",
              boxShadow: "0 8px 32px rgba(245,130,31,0.35)",
              color: "white",
              fontSize: 14,
              lineHeight: 1.5,
              fontFamily: "'Archivo', sans-serif",
            }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <div style={{
                width: 28, height: 28, borderRadius: "50%",
                background: "rgba(255,255,255,0.2)",
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0
              }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="8" r="3.5" stroke="white" strokeWidth="2"/>
                  <path d="M5 20c0-3.866 3.134-7 7-7s7 3.134 7 7" stroke="white" strokeWidth="2" strokeLinecap="round"/>
                  <circle cx="19" cy="6" r="2.5" fill={C.green}/>
                </svg>
              </div>
              <span style={{ fontWeight: 700, fontSize: 13 }}>ClearBot · Maroclear</span>
            </div>
            <p style={{ margin: 0, fontSize: 13 }}>
              Bonjour ! 👋 Je suis ClearBot, votre assistant Maroclear. Comment puis-je vous aider ?
            </p>
            <p style={{ margin: "8px 0 0", fontSize: 11, opacity: 0.8 }}>Cliquez pour démarrer →</p>
          </div>
        </div>
      )}

      {/* Bouton flottant rond */}
      {!open && (
        <button
          onClick={() => { setOpen(true); setShowProactive(false); }}
          style={{
            position: "fixed", bottom: 24, right: 24,
            width: 56, height: 56, borderRadius: "50%",
            background: `linear-gradient(135deg, ${C.orange}, ${C.orangeDark})`,
            border: "none", cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 20px rgba(245,130,31,0.45)",
            zIndex: z + 1,
            animation: unread > 0 ? "mcPulse 2s infinite" : "none",
            transition: "transform 0.2s",
          }}
          onMouseOver={e => e.currentTarget.style.transform = "scale(1.08)"}
          onMouseOut={e => e.currentTarget.style.transform = "scale(1)"}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <circle cx="8" cy="10" r="1" fill="white"/>
            <circle cx="12" cy="10" r="1" fill="white"/>
            <circle cx="16" cy="10" r="1" fill="white"/>
          </svg>
          {/* Badge unread */}
          {unread > 0 && (
            <div style={{
              position: "absolute", top: -2, right: -2,
              width: 18, height: 18, borderRadius: "50%",
              background: "#e74c3c", border: "2px solid white",
              fontSize: 10, color: "white", fontWeight: 700,
              display: "flex", alignItems: "center", justifyContent: "center"
            }}>{unread}</div>
          )}
        </button>
      )}

      {/* Fenêtre de chat */}
      {open && (
        <div style={{
          position: "fixed",
          bottom: expanded ? 0 : 18,
          right: expanded ? 0 : 24,
          width: expanded ? "min(700px, 100vw)" : "min(370px, calc(100vw - 16px))",
          height: expanded ? "min(90vh, 100vh)" : "min(565px, calc(100vh - 40px))",
          borderRadius: expanded ? 0 : 14,
          background: C.white,
          boxShadow: "0 8px 40px rgba(0,0,0,0.18)",
          display: "flex", flexDirection: "column",
          overflow: "hidden",
          animation: "mcPop 0.28s cubic-bezier(0.34,1.56,0.64,1)",
          zIndex: z,
          border: `1px solid ${C.border}`,
          transition: "width 0.25s ease, height 0.25s ease, bottom 0.25s ease, right 0.25s ease, border-radius 0.25s ease",
        }}>
          {/* Header */}
          <div style={{
            background: `linear-gradient(135deg, ${C.dark} 0%, #3a4152 100%)`,
            padding: "13px 14px",
            display: "flex", alignItems: "center", justifyContent: "space-between",
            flexShrink: 0
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 38, height: 38, borderRadius: "50%",
                background: "rgba(255,255,255,0.07)",
                border: `2px solid rgba(245,130,31,0.5)`,
                display: "flex", alignItems: "center", justifyContent: "center"
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="8" r="3.5" stroke="white" strokeWidth="1.8"/>
                  <path d="M5 20c0-3.866 3.134-7 7-7s7 3.134 7 7" stroke="white" strokeWidth="1.8" strokeLinecap="round"/>
                  <circle cx="19" cy="6" r="2.5" fill={C.green}/>
                </svg>
              </div>
              <div>
                <div style={{ color: C.white, fontWeight: 700, fontSize: 14 }}>ClearBot</div>
                <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 1 }}>
                  <div style={{ width: 5, height: 5, borderRadius: "50%", background: C.green }}/>
                  <span style={{ color: "rgba(255,255,255,0.5)", fontSize: 10.5 }}>Assistant Maroclear · En ligne</span>
                </div>
              </div>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <button
                onClick={handleReset}
                title="Nouvelle conversation"
                aria-label="Nouvelle conversation"
                style={{
                  background: "rgba(255,255,255,0.07)", border: "none",
                  borderRadius: 6, width: 28, height: 28, cursor: "pointer",
                  color: "rgba(255,255,255,0.7)", display: "flex",
                  alignItems: "center", justifyContent: "center"
                }}>
                <RefreshIcon size={13} color="rgba(255,255,255,0.75)" />
              </button>
              <button
                onClick={() => setExpanded(e => !e)}
                title={expanded ? "Réduire" : "Agrandir"}
                aria-label={expanded ? "Réduire" : "Agrandir"}
                style={{
                  background: "rgba(255,255,255,0.07)", border: "none",
                  borderRadius: 6, width: 28, height: 28, cursor: "pointer",
                  color: "rgba(255,255,255,0.7)", display: "flex",
                  alignItems: "center", justifyContent: "center"
                }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.75)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  {expanded ? (
                    <><path d="M4 14h6v6"/><path d="M20 10h-6V4"/><path d="M14 10l7-7"/><path d="M3 21l7-7"/></>
                  ) : (
                    <><path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/></>
                  )}
                </svg>
              </button>
              <button
                onClick={() => setOpen(false)}
                title="Fermer"
                aria-label="Fermer"
                style={{
                  background: "rgba(255,255,255,0.07)", border: "none",
                  borderRadius: 6, width: 28, height: 28, cursor: "pointer",
                  color: "rgba(255,255,255,0.7)", display: "flex",
                  alignItems: "center", justifyContent: "center"
                }}>
                <CloseIcon size={13} color="rgba(255,255,255,0.75)" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: "12px 12px 4px", background: C.lightGray }}>
            {messages.map(msg => <Message key={msg.id} msg={msg} />)}
            {typing && <TypingIndicator />}
            {!typing && contextButtons.length > 0 && (
              <SuggestionChips buttons={contextButtons} onSelect={handleChipSelect} />
            )}
            {!typing && messages.filter(m => m.from === "bot").length >= 2 && !feedbackSent && (
              <FeedbackPanel onSubmit={handleFeedback} />
            )}
            <div ref={bottomRef}/>
          </div>

          {/* Barre accent */}
          <div style={{ height: 2, background: `linear-gradient(90deg, ${C.orange}, ${C.green})`, flexShrink: 0 }}/>

          {/* Zone de saisie */}
          <div style={{
            padding: "10px 12px", background: C.white,
            display: "flex", alignItems: "flex-end", gap: 8,
            flexShrink: 0, borderTop: `1px solid ${C.midGray}`
          }}>
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder="Posez votre question..."
              rows={1}
              style={{
                flex: 1, border: `1.5px solid ${C.border}`,
                borderRadius: 10, padding: "9px 12px",
                fontSize: 13, lineHeight: 1.5,
                background: C.lightGray, color: C.textDark,
                fontFamily: "inherit", resize: "none",
                maxHeight: 90, overflowY: "auto"
              }}
              onFocus={e => e.target.style.borderColor = C.orange}
              onBlur={e => e.target.style.borderColor = C.border}
              onInput={e => {
                e.target.style.height = "auto";
                e.target.style.height = Math.min(e.target.scrollHeight, 90) + "px";
              }}
            />
            <button onClick={handleSend} disabled={!inputValue.trim() || typing} style={{
              width: 36, height: 36, borderRadius: 9, border: "none",
              background: inputValue.trim() && !typing ? `linear-gradient(135deg, ${C.orange}, ${C.orangeDark})` : C.midGray,
              cursor: inputValue.trim() && !typing ? "pointer" : "default",
              display: "flex", alignItems: "center", justifyContent: "center",
              flexShrink: 0
            }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <path d="M22 2L11 13" stroke="white" strokeWidth="2" strokeLinecap="round"/>
                <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>

          {/* Footer */}
          <div style={{ padding: "5px 14px 7px", background: C.white, textAlign: "center" }}>
            <span style={{ fontSize: 10, color: C.textGray }}>
              <strong style={{ color: C.orange }}>ClearBot</strong> · Maroclear — Dépositaire Central
            </span>
          </div>
        </div>
      )}
    </>
  );
}
