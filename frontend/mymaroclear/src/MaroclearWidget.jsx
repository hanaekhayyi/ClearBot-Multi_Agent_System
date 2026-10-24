import { useState, useRef, useEffect, useCallback } from "react";
import { getChatSession, resetChatSession, saveChatSession } from "./authApi";

// ─── Palette ──────────────────────────────────────────────────────────────────
const C = {
  orange:      "#f5821f",
  orangeDark:  "#c46819",
  orangeLight: "#fde6d2",
  green:       "#8cc63f",
  dark:        "#282e3c",
  white:       "#FFFFFF",
  lightGray:   "#f7f7f8",
  midGray:     "#e9ecef",
  border:      "#dee2e6",
  textGray:    "#6c757d",
  textDark:    "#282e3c",
  red:         "#e74c3c",
};

// ─── Icônes SVG (sans emoji) ──────────────────────────────────────────────────
function Ic({ d, size = 14, color = "currentColor", sw = 1.8, fill = "none" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill}
      stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round"
      style={{ flexShrink: 0 }}>
      {Array.isArray(d)
        ? d.map((path, i) => <path key={i} d={path} />)
        : <path d={d} />}
    </svg>
  );
}

const PATH = {
  user:       "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  briefcase:  ["M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z","M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"],
  mail:       ["M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z","M22 6l-10 7L2 6"],
  phone:      "M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 8.82 19.79 19.79 0 0 1 1.62 2.15 2 2 0 0 1 3.62 0h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 7.91a16 16 0 0 0 6.29 6.29l1.28-1.28a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z",
  layers:     ["M12 2L2 7l10 5 10-5-10-5z","M2 17l10 5 10-5","M2 12l10 5 10-5"],
  monitor:    ["M2 3h20a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z","M8 21h8","M12 17v4"],
  edit:       ["M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7","M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"],
  file:       ["M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z","M14 2v6h6","M16 13H8","M16 17H8","M10 9H8"],
  clip:       "M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48",
  check:      "M20 6L9 17l-5-5",
  warn:       ["M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z","M12 9v4","M12 17h.01"],
  refresh:    "M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15",
  x:          "M18 6L6 18M6 6l12 12",
  send:       ["M22 2L11 13","M22 2L15 22 11 13 2 9 22 2"],
  chat:       "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  image:      ["M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z","M8.5 10a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z","M21 15l-5-5L5 21"],
  dot:        "M12 12m-2 0a2 2 0 1 0 4 0 2 2 0 1 0-4 0",
  pencil:     ["M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"],
  dispatch:   ["M22 11.08V12a10 10 0 1 1-5.93-9.14","M22 4L12 14.01l-3-3"],
};

// ─── Prompt système — flux direct JSON, priorité interne uniquement ───────────
function buildSystemPrompt(profile) {
  const profileBlock = profile
    ? `PROFIL AFFILIÉ CONNECTÉ (déjà enregistré — ne jamais redemander) :
- Nom        : ${profile.reporterName}
- Activité   : ${profile.reporterActivity}
- Institution: ${profile.institution || ""}
- Email      : ${profile.reporterEmail}
- Téléphone  : ${profile.reporterPhone}`
    : `PROFIL AFFILIÉ : Non disponible. Demande le nom et l'email avant de continuer.`;

  return `Tu es ClearBot, assistant IA de Maroclear. Tu aides les affiliés à qualifier et préparer une demande, un incident ou une réclamation.

${profileBlock}

═══════════════════════════════════
TYPE DE DOSSIER — INFÉRENCE AUTOMATIQUE OBLIGATOIRE
Tu dois déterminer requestType parmi exactement : "incident", "demande", "reclamation".
- incident : dysfonctionnement, anomalie, blocage, indisponibilité, erreur technique, service interrompu.
- demande : besoin d'information, assistance, action attendue, création/modification, réinitialisation, aide sans insatisfaction.
- reclamation : plainte, insatisfaction, contestation, qualité de service jugée insuffisante, retard ou traitement non conforme.
Si le type est ambigu, pose une question courte pour trancher avant de générer le JSON.
Le champ system est demandé uniquement pour un incident. Pour une demande ou une réclamation, ne demande jamais le système et laisse system vide.

CHAMPS À COLLECTER SELON LE TYPE
- incident : service, system, subject, description. Les pièces jointes sont optionnelles.
- demande : service, dateOccurrence, frequenceOccurrence, description, solution. Ne demande jamais system.
- reclamation : service, dateOccurrence, frequenceOccurrence, description, solution. Ne demande jamais system.
Ne demande pas de champ qui n'existe pas dans le formulaire cible.

═══════════════════════════════════
CATALOGUE DES SERVICES — INFÉRENCE AUTOMATIQUE OBLIGATOIRE
Ne JAMAIS demander le service s'il peut être déduit du message. Ne demander le système que pour un incident.
═══════════════════════════════════
Applique ces règles de déduction dès le premier message de l'affilié uniquement si le dossier est un incident :

1. L'affilié mentionne "TCS BaNCS", "TCS", "BaNCS", "bancs", "tcs bancs" (insensible à la casse)
   → système = "TCS BaNCS"
   → Si bourse, contrats, dénouement, avis d'opéré              → service = "Post-marché-Bourse"
   → Si OTC, gré à gré                                          → service = "Post-marché-OTC"
   → Si pension livrée, repo                                    → service = "Post-marché-Repo's"
   → Si transfert, franco                                       → service = "Post-marché-Transfert"
   → Si reporting, RCQ, REQ, RMQ, RSM, document comptable       → service = "Reporting"
   → Si accès impossible, connexion, écran, interface bloquée,
     message d'erreur, indisponible, inaccessible, arrêt,
     ne s'ouvre pas, ne fonctionne pas, ne répond pas           → service = "Technique"
   → Si aucun sous-contexte clair                               → service = "Technique"

2. L'affilié mentionne "MyMaroclear", "My Maroclear", "mymaroclear" (insensible à la casse)
   → système = "My Maroclear"
   → Si OST, opération sur titre                                → service = "OST"
   → Si codification, admission, instrument, valeur, titre      → service = "Référentiel-Titres"
   → Si affiliation, mandat, affilié                            → service = "Référentiel-Affiliés"
   → Sinon                                                      → service = "Technique"

3. L'affilié mentionne "OST" sans préciser le système
   → système = "My Maroclear", service = "OST"

4. Si le dossier est un incident et que l'affilié ne mentionne aucun système reconnaissable
   → Pose UNE seule question courte pour identifier le service.
   → Ne demande JAMAIS service ET système dans le même message.

RÈGLE ABSOLUE : Dès que le système ou le service est déductible du texte (même partiellement),
ne le demande JAMAIS — remplis-le directement dans le JSON.
Pour une demande ou une réclamation, déduis seulement le service et garde system vide.

═══════════════════════════════════
MATRICE DE QUALIFICATION — INTERNE
Ne jamais mentionner les mots "priorité", "urgence" ou "impact" à l'affilié.
Ne jamais afficher ces valeurs dans le chat.
═══════════════════════════════════
POST-MARCHÉ (Bourse/OTC/Repos/Transfert) sur TCS BaNCS :
  • Blocage général / dénouement bloqué     → urgency:Très haute  impact:Très haut  priority:P1 Majeure
  • Blocage d'un affilié                    → urgency:Très haute  impact:Moyen      priority:P2 Très haute
  • Dysfonctionnement contournable          → urgency:Moyenne     impact:Moyen      priority:P3 Moyenne
OST / RÉFÉRENTIEL sur My Maroclear :
  • Impossibilité totale de traitement      → urgency:Très haute  impact:Moyen      priority:P2 Très haute
  • Dysfonctionnement partiel               → urgency:Moyenne     impact:Moyen      priority:P3 Moyenne
TECHNIQUE :
  • Système indisponible / arrêt complet    → urgency:Très haute  impact:Très haut  priority:P1 Majeure
  • Message d'erreur / bug affichage        → urgency:Basse       impact:Bas        priority:P4 Basse

═══════════════════════════════════
DIAGNOSTIC OBLIGATOIRE POUR INCIDENT (AVANT JSON)
═══════════════════════════════════
Avant de générer le JSON d'un incident, tu dois t'assurer que les éléments suivants sont clairs :

- Nature du problème (erreur, blocage, page blanche, lenteur…)
- Présence d'un message d'erreur
- Étendue de l'impact (utilisateur seul ou global)
- Contexte d'apparition (depuis quand, quelle action déclenchait le problème)

Si ces éléments ne sont pas mentionnés pour un incident, pose des questions.
Pour une demande ou une réclamation, ne pose pas ces questions techniques si elles ne sont pas pertinentes : collecte seulement le service concerné, la date d'occurrence, la fréquence d'occurrence, la description, et la solution attendue ou le motif d'insatisfaction.
Ne génère PAS le JSON tant que les informations utiles au type de dossier ne sont pas suffisamment claires.

═══════════════════════════════════
PROCÉDURE STRICTE
═══════════════════════════════════
1. Accueille l'affilié sobrement et demande-lui de décrire son besoin ou problème.
2. Déduis automatiquement le type et le service dès que possible. Déduis le système uniquement si le type est incident.
3. Pose les questions nécessaires pour qualifier correctement le dossier.
   Pour un incident, priorité aux questions suivantes si elles ne sont pas mentionnées :
   - Y a-t-il un message d'erreur affiché ? Si oui, lequel ?
   - S'agit-il d'une page blanche, d'un blocage ou d'un comportement anormal ?
   - Le problème impacte-t-il uniquement vous ou plusieurs utilisateurs ?
   - Depuis quand le problème se produit-il ?
   - Demande une capture d'écran si pertinent.
   Pose ces questions de manière naturelle et progressive.
4. Pour un incident, demande une capture d'écran dans les cas suivants :
   - message d'erreur
   - page blanche
   - affichage anormal
   - blocage visuel
   Ne pas hésiter à la demander si cela peut aider au diagnostic d'un incident.
5. Génère le JSON uniquement lorsque :
   - le dossier est clairement compris
   - le contexte est suffisant pour le traitement
   - les éléments requis pour le type de dossier sont renseignés
   Sinon, continue à poser des questions.
6. Un formulaire de confirmation s'affichera automatiquement côté client. Tu n'as PAS à demander de confirmation par texte.
7. N'utilise JAMAIS d'emojis dans tes réponses.
8. Sois concis, professionnel et bienveillant. Réponds en français.

═══════════════════════════════════
FORMAT JSON — générer dès que les infos sont réunies
═══════════════════════════════════
{"EXTRACTED":{"requestType":"incident|demande|reclamation","reporterName":"...","reporterActivity":"...","reporterEmail":"...","reporterPhone":"...","service":"...","system":"...","businessCase":"...","urgency":"...","impact":"...","priority":"...","subject":"...","description":"...","dateOccurrence":"...","frequenceOccurrence":"...","solution":"..."}}

Le JSON doit être sur une seule ligne, inclure tous les champs, et être la dernière chose générée dans le message.
Pour requestType "demande" ou "reclamation", system doit être une chaîne vide.`;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
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
      continue; // skip separator row
    } else {
      if (inTable) { tableHtml += "</table>"; processed.push(tableHtml); tableHtml = ""; inTable = false; }
      processed.push(line);
    }
  }
  if (inTable) { tableHtml += "</table>"; processed.push(tableHtml); }

  return processed.join("\n")
    // Headers
    .replace(/^### (.+)$/gm, '<div style="font-size:13px;font-weight:700;margin:12px 0 4px;color:#1a1a1a;">$1</div>')
    .replace(/^## (.+)$/gm, '<div style="font-size:14px;font-weight:700;margin:14px 0 6px;color:#1a1a1a;">$1</div>')
    .replace(/^---$/gm, '<hr style="border:none;border-top:1px solid #e5e5e5;margin:10px 0;"/>')
    // Blockquotes
    .replace(/^> \*(.+?)\*$/gm, '<div style="border-left:3px solid #f5821f;padding:4px 10px;margin:6px 0;font-style:italic;font-size:12px;color:#555;background:#fef9f4;">$1</div>')
    .replace(/^> (.+)$/gm, '<div style="border-left:3px solid #ddd;padding:4px 10px;margin:6px 0;font-size:12px;color:#555;">$1</div>')
    // Lists
    .replace(/^\d+\.\s+(.+)$/gm, '<div style="padding-left:16px;margin:2px 0;">• $1</div>')
    .replace(/^[-*]\s+(.+)$/gm, '<div style="padding-left:16px;margin:2px 0;">• $1</div>')
    // Inline formatting
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/`(.*?)`/g, `<code style="background:#f0f0f0;padding:1px 5px;border-radius:4px;font-size:12px;font-family:monospace">$1</code>`)
    .replace(/\n/g, "<br/>");
}

// ─── Composants visuels ───────────────────────────────────────────────────────
function Avatar({ isUser }) {
  if (isUser) return (
    <div style={{
      width: 28, height: 28, borderRadius: "50%",
      background: C.dark, display: "flex", alignItems: "center",
      justifyContent: "center", flexShrink: 0,
      fontSize: 11, color: "white", fontWeight: 700,
    }}>A</div>
  );
  return (
    <div style={{
      width: 28, height: 28, borderRadius: "50%",
      background: `linear-gradient(135deg, ${C.orange}, ${C.orangeDark})`,
      display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
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
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: 5, height: 5, borderRadius: "50%",
            background: C.orange, opacity: 0.7,
            animation: `mcBounce 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}/>
        ))}
      </div>
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.from === "user";

  if (msg.type === "system") return (
    <div style={{ textAlign: "center", margin: "10px 0" }}>
      <span style={{
        fontSize: 11, color: C.textGray,
        background: C.midGray, borderRadius: 20, padding: "3px 12px",
      }}>{msg.text}</span>
    </div>
  );

  return (
    <div style={{
      display: "flex", gap: 7,
      flexDirection: isUser ? "row-reverse" : "row",
      alignItems: "flex-end", marginBottom: 8,
      animation: "mcFade 0.25s ease",
    }}>
      <Avatar isUser={isUser} />
      <div style={{ maxWidth: "80%", display: "flex", flexDirection: "column", alignItems: isUser ? "flex-end" : "flex-start" }}>
        {/* Pièces jointes inline (message utilisateur) */}
        {msg.attachmentNames && msg.attachmentNames.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 4, justifyContent: isUser ? "flex-end" : "flex-start" }}>
            {msg.attachmentNames.map((name, i) => (
              <div key={i} style={{
                background: C.orangeLight, border: `1px solid ${C.orange}30`,
                borderRadius: 6, padding: "3px 8px",
                fontSize: 11, color: C.orangeDark,
                display: "flex", alignItems: "center", gap: 4,
              }}>
                <Ic d={PATH.image} size={10} color={C.orangeDark} sw={2}/>
                {name.length > 16 ? name.slice(0, 16) + "…" : name}
              </div>
            ))}
          </div>
        )}
        <div style={{
          background: isUser ? `linear-gradient(135deg, ${C.orange}, ${C.orangeDark})` : C.white,
          color: isUser ? "white" : C.textDark,
          border: isUser ? "none" : `1px solid ${C.border}`,
          borderRadius: isUser ? "12px 0 12px 12px" : "0 12px 12px 12px",
          padding: "9px 13px", fontSize: 13, lineHeight: 1.65,
          boxShadow: isUser ? `0 2px 10px rgba(245,130,31,0.25)` : "0 1px 4px rgba(0,0,0,0.05)",
        }} dangerouslySetInnerHTML={{ __html: formatText(msg.text) }}/>
        {/* Bouton "Voir la source" pour les reponses RAG */}
        {!isUser && msg.rag_sources && msg.rag_sources.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
            {msg.rag_sources.map((source, i) => (
              <a key={i}
                href={`http://localhost:8000/documents/${encodeURIComponent(source)}`}
                target="_blank" rel="noopener noreferrer"
                style={{
                  display: "inline-flex", alignItems: "center", gap: 4,
                  background: "#f0f7ff", border: "1px solid #cce0ff",
                  borderRadius: 6, padding: "3px 8px",
                  fontSize: 11, color: "#2c5ab5", textDecoration: "none",
                  fontWeight: 500, cursor: "pointer",
                }}
              >
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <path d="M14 2v6h6"/>
                </svg>
                {source.length > 25 ? source.slice(0, 25) + "..." : source}
              </a>
            ))}
          </div>
        )}
        {/* Sources légales (RAG réglementaire) */}
        {!isUser && (msg.regl_sources_detailed?.length > 0 || msg.regl_sources?.length > 0) && (
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
            <div style={{ display: "none", marginTop: 6, maxHeight: 250, overflowY: "auto", border: "1px solid #ede5ff", borderRadius: 6, padding: 8 }}>
              {msg.regl_sources_detailed?.length > 0 ? (
                msg.regl_sources_detailed.map((src, i) => (
                  <div key={i} style={{
                    background: "#faf8ff",
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
                      <div style={{ color: "#7c6b9e", marginTop: 3, fontSize: 10, paddingLeft: 22, wordBreak: "break-word", lineHeight: 1.6 }}>
                        {src.hierarchy.split(" > ").map((part, j) => (
                          <span key={j}>
                            {j > 0 && <span style={{ margin: "0 3px", color: "#bbb" }}>›</span>}
                            <span>{part.length > 60 ? part.slice(0, 60) + "…" : part}</span>
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
              // Construire dynamiquement les liens PDF à partir des sources
              const pdfSources = new Set();
              if (msg.regl_sources_detailed?.length > 0) {
                msg.regl_sources_detailed.forEach(src => {
                  const corpus = src.corpus || "";
                  if (corpus === "actualite_historique") {
                    pdfSources.add(JSON.stringify({ name: "Actualités Historique Maroclear", file: "ACTUALIT%C3%89S%20HISTORIQUE.pdf" }));
                  } else if (corpus === "ammc_recueil_docling") {
                    pdfSources.add(JSON.stringify({ name: "Recueil AMMC (Mars 2026)", file: "Recueil_AMMC_VF_%20Mars%202026.pdf" }));
                  } else {
                    // Fallback par nom de document
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

// ─── Carte de résumé — SANS priorité/urgence/impact ──────────────────────────
function SummaryCard({ data, attachments, onConfirm, onCancel }) {
  const requestType = (data.requestType || "")
    .toString()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

  const rows = [
    { icon: PATH.dispatch,  label: "Type",        val: data.requestType },
    { icon: PATH.user,      label: "Rapporteur",  val: data.reporterName },
    { icon: PATH.briefcase, label: "Activité",    val: data.reporterActivity },
    { icon: PATH.mail,      label: "Email",       val: data.reporterEmail },
    { icon: PATH.phone,     label: "Téléphone",   val: data.reporterPhone },
    { icon: PATH.layers,    label: "Service",     val: data.service },
    requestType === "incident" ? { icon: PATH.monitor, label: "Système", val: data.system } : null,
    requestType === "incident" ? { icon: PATH.edit, label: "Objet", val: data.subject } : null,
    requestType !== "incident" ? { icon: PATH.edit, label: "Date", val: data.dateOccurrence } : null,
    requestType !== "incident" ? { icon: PATH.refresh, label: "Fréquence", val: data.frequenceOccurrence } : null,
    { icon: PATH.file,      label: "Description", val: data.description
        ? (data.description.length > 80 ? data.description.slice(0, 80) + "…" : data.description)
        : "—" },
    requestType !== "incident" ? { icon: PATH.check, label: "Solution", val: data.solution } : null,
  ].filter(Boolean);

  return (
    <div style={{
      background: C.white, border: `1.5px solid ${C.orange}`,
      borderRadius: 10, padding: "12px 14px", marginBottom: 8,
      boxShadow: "0 2px 12px rgba(245,130,31,0.12)",
      animation: "mcFade 0.3s ease",
    }}>
      {/* En-tête carte */}
      <div style={{
        display: "flex", alignItems: "center", gap: 7,
        fontWeight: 700, color: C.orange, marginBottom: 10, fontSize: 13,
      }}>
        <Ic d={PATH.file} size={14} color={C.orange} sw={2}/>
        Récapitulatif du dossier
      </div>

      {/* Lignes de données */}
      {rows.map(r => (
        <div key={r.label} style={{ display: "flex", gap: 8, marginBottom: 5, fontSize: 12, alignItems: "flex-start" }}>
          <span style={{ paddingTop: 1 }}>
            <Ic d={r.icon} size={12} color={C.textGray} sw={1.8}/>
          </span>
          <span style={{ color: C.textGray, minWidth: 82, flexShrink: 0 }}>{r.label}</span>
          <span style={{ color: C.textDark, fontWeight: 500, lineHeight: 1.4 }}>{r.val || "—"}</span>
        </div>
      ))}

      {/* Pièces jointes */}
      {attachments && attachments.length > 0 && (
        <div style={{ display: "flex", gap: 8, marginBottom: 5, fontSize: 12, alignItems: "center" }}>
          <Ic d={PATH.clip} size={12} color={C.textGray} sw={1.8}/>
          <span style={{ color: C.textGray, minWidth: 82 }}>Captures</span>
          <span style={{ color: C.green, fontWeight: 600 }}>
            {attachments.length} fichier{attachments.length > 1 ? "s" : ""} joint{attachments.length > 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* Boutons */}
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <button onClick={onConfirm} style={{
          flex: 1, padding: "8px", borderRadius: 8, border: "none",
          background: `linear-gradient(135deg, ${C.green}, #27ae60)`,
          color: "white", fontWeight: 700, fontSize: 12, cursor: "pointer",
          fontFamily: "inherit", display: "flex", alignItems: "center",
          justifyContent: "center", gap: 6,
        }}>
          <Ic d={PATH.check} size={12} color="white" sw={2.5}/>
          Confirmer
        </button>
        {onCancel && (
          <button onClick={onCancel} style={{
            flex: 1, padding: "8px", borderRadius: 8,
            border: `1.5px solid ${C.border}`, background: C.white,
            color: C.textDark, fontWeight: 600, fontSize: 12, cursor: "pointer",
            fontFamily: "inherit", display: "flex", alignItems: "center",
            justifyContent: "center", gap: 6,
          }}>
            <Ic d={PATH.pencil} size={12} color={C.textDark} sw={1.8}/>
            Corriger
          </button>
        )}
      </div>
    </div>
  );
}

function SuccessBanner() {
  return (
    <div style={{
      background: `linear-gradient(135deg, #eafde8, #d4f7d0)`,
      border: `1.5px solid ${C.green}`,
      borderRadius: 10, padding: "12px 14px",
      display: "flex", alignItems: "center", gap: 10,
      animation: "mcFade 0.3s ease", marginBottom: 8,
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: "50%",
        background: C.green, display: "flex",
        alignItems: "center", justifyContent: "center", flexShrink: 0,
      }}>
        <Ic d={PATH.check} size={16} color="white" sw={2.5}/>
      </div>
      <div>
        <div style={{ fontWeight: 700, color: "#27ae60", fontSize: 13 }}>
          Formulaire rempli automatiquement
        </div>
        <div style={{ fontSize: 11, color: C.textGray, marginTop: 2 }}>
          Vérifiez les champs et soumettez le dossier.
        </div>
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
        Comment évaluez-vous cette interaction ?
      </div>
      {/* Étoiles */}
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
      {/* Commentaire optionnel */}
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
          transition: "background 0.2s",
        }}
      >
        Envoyer mon avis
      </button>
    </div>
  );
}

const STORAGE_KEY = "maroclear-clearbot-session";

function loadStoredSession() {
  if (typeof window === "undefined") {
    return { messages: [], stage: "idle", pendingData: null, open: false };
  }

  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return { messages: [], stage: "idle", pendingData: null, open: false };
    const parsed = JSON.parse(raw);
    return {
      messages: Array.isArray(parsed.messages) ? parsed.messages : [],
      stage: parsed.stage || "idle",
      pendingData: parsed.pendingData || null,
      open: Boolean(parsed.open),
    };
  } catch (_) {
    return { messages: [], stage: "idle", pendingData: null, open: false };
  }
}

function toHistory(messages) {
  return messages
    .filter(msg => msg.from === "user" || msg.from === "bot")
    .map(msg => ({
      role: msg.from === "user" ? "user" : "assistant",
      content: msg.text,
    }));
}

// ─── Composant principal ──────────────────────────────────────────────────────
export default function MaroclearWidget({ onDataExtracted, onDispatch, userProfile = null }) {
  const storedSession = useRef(loadStoredSession());
  const [open, setOpen]           = useState(storedSession.current.open);
  const [expanded, setExpanded]   = useState(false);
  const [messages, setMessages]   = useState(storedSession.current.messages);
  const [typing, setTyping]       = useState(false);
  const [inputValue, setInput]    = useState("");
  const [stage, setStage]         = useState(storedSession.current.stage);
  const [pendingData, setPending] = useState(storedSession.current.pendingData);
  const [unread, setUnread]       = useState(0);
  const [showProactive, setShowProactive]     = useState(false);
  const [proactiveDismissed, setProactiveDismissed] = useState(false);
  const [attachments, setAttachments]         = useState([]);
  const [hydrated, setHydrated]               = useState(false);

  const bottomRef   = useRef(null);
  const inputRef    = useRef(null);
  const fileInputRef = useRef(null);
  const historyRef  = useRef(toHistory(storedSession.current.messages));
  const hydratedRef = useRef(false);

  const OPENROUTER_API_KEY = process.env.REACT_APP_OPENROUTER_KEY;
  const z = 9998;

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing, pendingData]);

  useEffect(() => {
    let cancelled = false;
    getChatSession()
      .then((session) => {
        if (cancelled || !Array.isArray(session.messages) || session.messages.length === 0) return;
        setMessages(session.messages);
        historyRef.current = toHistory(session.messages);
        setStage(session.stage || "chatting");
        setPending(session.pendingData || null);
      })
      .catch(() => {})
      .finally(() => {
        hydratedRef.current = true;
        setHydrated(true);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Persiste la conversation pendant la navigation et les remontages React.
  useEffect(() => {
    window.sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ messages, stage, pendingData, open })
    );
    if (hydrated) {
      saveChatSession({ messages, stage, pendingData })
        .catch((err) => console.warn("[ClearBot] Session non sauvegardee:", err));
    }
  }, [messages, stage, pendingData, open, hydrated]);

  // Bulle proactive après 2s
  useEffect(() => {
    const t = setTimeout(() => {
      if (!open && !proactiveDismissed) {
        setShowProactive(true);
        setUnread(1);
      }
    }, 2000);
    return () => clearTimeout(t);
  }, [open, proactiveDismissed]);

  // Focus à l'ouverture
  useEffect(() => {
    if (open) {
      setUnread(0);
      setShowProactive(false);
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [open, messages.length, userProfile]);

  // Message de bienvenue (une seule fois)
  const greetingSentRef = useRef(false);

  useEffect(() => {
    if (!hydrated) return;
    if (greetingSentRef.current) return;
    if (open && messages.length === 0) {
      greetingSentRef.current = true;

      // Verifier si une conversation a ete commencee dans le portail public
      const publicConversation = localStorage.getItem("clearbot_public_conversation");
      if (publicConversation) {
        try {
          const publicMsgs = JSON.parse(publicConversation);
          const restored = publicMsgs.map(m => ({
            id: Date.now() + Math.random(),
            from: m.from,
            time: m.time || nowTime(),
            text: m.text,
          }));
          setMessages(restored);
          restored.forEach(m => {
            historyRef.current.push({ role: m.from === "user" ? "user" : "assistant", content: m.text });
          });
          localStorage.removeItem("clearbot_public_conversation");
          const transition = userProfile
            ? `Bonjour **${userProfile.reporterName}**, je reprends notre conversation. Vous etes maintenant connecte a votre espace prive. Je peux finaliser votre declaration.`
            : `Vous etes maintenant connecte. Je reprends notre conversation.`;
          pushBot(transition);
          setStage("chatting");
        } catch (e) {
          localStorage.removeItem("clearbot_public_conversation");
        }
        return;
      }

      const greeting = userProfile
        ? `Bonjour, **${userProfile.reporterName}**.\n\nJe suis ClearBot, l'assistant de Maroclear. Vos coordonnees sont deja enregistrees.\n\nDecrivez-moi votre demande, incident ou reclamation en quelques mots, je preparerai la bonne fiche.`
        : `Bonjour.\n\nJe suis ClearBot, l'assistant IA de Maroclear. Decrivez-moi votre demande, incident ou reclamation en quelques mots.`;
      pushBot(greeting);
      setStage("chatting");
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, hydrated]);

  const pushBot = (text, extra = {}) => {
    const msg = { id: Date.now() + Math.random(), from: "bot", time: nowTime(), text, ...extra };
    setMessages(prev => [...prev, msg]);
    historyRef.current.push({ role: "assistant", content: text });
  };

  const pushUser = (text, extra = {}) => {
    const msg = { id: Date.now() + Math.random(), from: "user", time: nowTime(), text, ...extra };
    setMessages(prev => [...prev, msg]);
    historyRef.current.push({ role: "user", content: text });
  };

  // Gestion des pièces jointes
  const handleFileChange = (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    const newFiles = [...attachments, ...files];
    setAttachments(newFiles);

    // Message utilisateur avec noms des fichiers
    const names = files.map(f => f.name);
    pushUser(
      `${files.length} capture${files.length > 1 ? "s" : ""} jointe${files.length > 1 ? "s" : ""}`,
      { attachmentNames: names }
    );

    // Informer le backend que des pièces jointes ont été ajoutées
    // Seulement si on n'a pas encore de pendingData (pas en mode correction)
    if (stage === "chatting" && !pendingData) {
      callAI(`[Pièce(s) jointe(s) : ${names.join(", ")}. L'utilisateur a joint une capture d'écran.]`);
    }

    e.target.value = "";
  };

  const removeAttachment = (idx) => {
    setAttachments(prev => prev.filter((_, i) => i !== idx));
  };

  // ─── Appel Backend /chat ─────────────────────────────────────────────────────
  const callAI = useCallback(async (userText) => {
    setTyping(true);
    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ message: userText, context: "private" }),
      });

      if (!response.ok) {
        const err = await response.text();
        throw new Error(`HTTP ${response.status}: ${err}`);
      }

      const data = await response.json();
      const botText = data.response || "Je n'ai pas pu traiter votre demande.";

      setTyping(false);

      // DEBUG — voir ce que le backend retourne
      console.log("[ClearBot] Backend response:", JSON.stringify(data, null, 2));

      // ── Si form_data est retourné → afficher la SummaryCard ──
      const formData = data.form_data;
      if (formData && data.classification && data.classification !== "AMBIGU") {
        // Texte visible pour l'utilisateur
        pushBot(botText);

        // Construire les données pour la carte de confirmation
        const extracted = {
          requestType:         (formData.type || data.classification || "").toLowerCase(),
          reporterName:        formData.reporterName || "",
          reporterActivity:    formData.reporterActivity || "",
          reporterEmail:       formData.reporterEmail || "",
          reporterPhone:       formData.reporterPhone || "",
          service:             formData.serviceConcerne || "",
          system:              formData.systemeImpacte || "",
          subject:             formData.objet || "",
          description:         formData.description || "",
          dateOccurrence:      formData.dateOccurrence || "",
          frequenceOccurrence: formData.frequenceOccurrence || "",
          solution:            formData.solution || "",
          businessCase:        formData.objet || formData.description || "",
          urgency:             formData.urgence || "",
          impact:              formData.impact || "",
          priority:            formData.priorite || "",
          // Garder le form_data brut pour le dispatch
          _rawFormData:        formData,
        };

        setPending(extracted);
        setStage("awaiting_confirm");
        return;
      }

      // ── Sinon, afficher la réponse texte (question de clarification ou autre) ──
      pushBot(botText, {
        classification: data.classification || "",
        priorite: data.priorite || "",
        agent_used: data.agent_used || "",
        needs_glpi: data.needs_glpi || false,
        rag_sources: data.rag_sources || [],
        regl_sources: data.regl_sources || [],
        regl_sources_detailed: data.regl_sources_detailed || [],
      });

    } catch (error) {
      setTyping(false);
      console.error("[ClearBot] Erreur:", error);
      pushBot(`Erreur de connexion au serveur. ${error.message || "Vérifiez que le backend est lancé sur le port 8000."}`);
    }
  }, [userProfile]);

  const handleSend = useCallback(() => {
    const txt = inputValue.trim();
    if (!txt || typing || stage === "done" || stage === "awaiting_confirm") return;
    setInput("");
    pushUser(txt);

    // Si en mode correction (pendingData existe et stage === "correcting")
    if (pendingData && stage === "correcting") {
      const lower = txt.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      const updated = { ...pendingData };
      let fieldCorrected = "";

      if (lower.startsWith("description") || lower.startsWith("desc")) {
        const val = txt.replace(/^(?:description|desc)\s*[:=]?\s*/i, "").trim();
        if (val) { updated.description = val; fieldCorrected = "description"; }
      } else if (lower.startsWith("service")) {
        const val = txt.replace(/^service\s*[:=]?\s*/i, "").trim();
        if (val) { updated.service = val; fieldCorrected = "service"; }
      } else if (lower.startsWith("objet") || lower.startsWith("sujet")) {
        const val = txt.replace(/^(?:objet|sujet)\s*[:=]?\s*/i, "").trim();
        if (val) { updated.subject = val; fieldCorrected = "objet"; }
      } else if (lower.startsWith("systeme") || lower.startsWith("système") || lower.startsWith("system")) {
        const val = txt.replace(/^(?:syst[eè]me|system)\s*[:=]?\s*/i, "").trim();
        if (val) { updated.system = val; fieldCorrected = "système"; }
      } else if (lower.startsWith("date")) {
        const val = txt.replace(/^date\s*[:=]?\s*/i, "").trim();
        if (val) { updated.dateOccurrence = val; fieldCorrected = "date"; }
      } else if (lower.startsWith("frequence") || lower.startsWith("fréquence")) {
        const val = txt.replace(/^(?:fr[eé]quence)\s*[:=]?\s*/i, "").trim();
        if (val) { updated.frequenceOccurrence = val; fieldCorrected = "fréquence"; }
      } else if (lower.startsWith("solution")) {
        const val = txt.replace(/^solution\s*[:=]?\s*/i, "").trim();
        if (val) { updated.solution = val; fieldCorrected = "solution"; }
      } else {
        // Pas de champ détecté → demander de préciser
        pushBot("Je n'ai pas compris quel champ corriger. Précisez le nom du champ suivi de la valeur, par exemple :\n- **service** : Reporting\n- **description** : Nous souhaitons...");
        return;
      }

      setPending(updated);
      setStage("awaiting_confirm");
      pushBot(`Le champ **${fieldCorrected}** a été mis à jour. Vérifiez le récapitulatif ci-dessous.`);
      return;
    }

    callAI(txt);
  }, [inputValue, typing, stage, callAI, pendingData]);

  // ── Confirmation : envoie les données au formulaire + dispatch priorité ──
  const handleConfirm = () => {
    if (!pendingData) return;
    const requestType = (pendingData.requestType || "incident")
      .toString()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();

    // Données publiques (pour le formulaire affilié) — sans priorité
    const publicData = {
      requestType:      requestType,
      service:          pendingData.service     || "",
      system:           requestType === "incident" ? (pendingData.system || "") : "",
      subject:          pendingData.subject     || "",
      description:      pendingData.description || "",
      businessCase:     pendingData.businessCase || "",
      dateOccurrence:   pendingData.dateOccurrence || "",
      frequenceOccurrence: pendingData.frequenceOccurrence || "",
      solution:         pendingData.solution || "",
      attachments:      attachments,
      // Profil session — source de vérité
      ...(userProfile && {
        reporterName:     userProfile.reporterName,
        reporterActivity: userProfile.reporterActivity,
        reporterEmail:    userProfile.reporterEmail,
        reporterPhone:    userProfile.reporterPhone,
        institution:      userProfile.institution || pendingData.institution,
      }),
    };

    // Données de dispatch — envoyer le form_data brut du backend (déjà avec les bons noms de champs)
    const dispatchData = pendingData._rawFormData || {
      ticket_id:        "TKT-" + Math.random().toString(36).substr(2, 8).toUpperCase(),
      type:             (pendingData.requestType || "incident").toUpperCase(),
      serviceConcerne:  pendingData.service || "",
      systemeImpacte:   pendingData.system || "",
      objet:            pendingData.subject || pendingData.description || "",
      description:      pendingData.description || "",
      priorite:         pendingData.priority || "",
      urgence:          pendingData.urgency || "",
      impact:           pendingData.impact || "",
      gravite:          pendingData.gravite || "",
      reporterName:     userProfile?.reporterName || "",
      reporterActivity: userProfile?.reporterActivity || "",
      institution:      userProfile?.institution || "",
      reporterEmail:    userProfile?.reporterEmail || "",
      reporterPhone:    userProfile?.reporterPhone || "",
    };

    // Stocker les fichiers dans un store global (les objets File ne survivent pas à navigate)
    if (attachments.length > 0) {
      window.__clearbot_attachments = attachments;
    }

    onDataExtracted?.(publicData);
    onDispatch?.(dispatchData); // hook optionnel pour envoyer au dispatcher

    setStage("done");
    pushBot(
      attachments.length > 0
        ? `Votre dossier a été enregistré avec ${attachments.length} capture${attachments.length > 1 ? "s" : ""} jointe${attachments.length > 1 ? "s" : ""}. Le formulaire a été pré-rempli. Vous pouvez le vérifier et le soumettre.`
        : "Votre dossier a été enregistré. Le formulaire a été pré-rempli. Vous pouvez le vérifier et le soumettre."
    );
  };

  const handleCancel = () => {
    if (stage === "correcting") return; // Déjà en mode correction
    setStage("correcting");
    pushBot(
      "Quel champ souhaitez-vous corriger ?\n\n" +
      "Indiquez le champ suivi de la nouvelle valeur, par exemple :\n" +
      "- **service** : Post-marché-Bourse\n" +
      "- **description** : Nous n'avons pas reçu...\n" +
      "- **objet** : Retransmission fichier AOE\n" +
      "- **système** : TCS BaNCS\n" +
      "- **date** : 25/05/2026\n\n" +
      "Ou décrivez simplement la correction à apporter."
    );
  };

  const handleReset = () => {
    window.sessionStorage.removeItem(STORAGE_KEY);
    resetChatSession().catch(() => {});
    setMessages([]);
    historyRef.current = [];
    setStage("idle");
    setPending(null);
    setInput("");
    setAttachments([]);
    setTimeout(() => {
      const greeting = userProfile
        ? `Bonjour, **${userProfile.reporterName}**.\n\nDécrivez-moi votre demande, incident ou réclamation.`
        : "Bonjour. Décrivez-moi votre demande, incident ou réclamation.";
      pushBot(greeting);
      setStage("chatting");
    }, 100);
  };

  const handleFeedback = async ({ rating, comment }) => {
    try {
      await fetch("http://localhost:8000/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ rating, comment, ticket_id: pendingData?.ticket_id || "" }),
      });
    } catch (err) {
      console.warn("[ClearBot] Feedback non envoyé:", err);
    }
  };

  const canSend    = inputValue.trim() && !typing && (stage === "chatting" || stage === "correcting");
  const canAttach  = (stage === "chatting" || stage === "correcting" || stage === "done") && !typing;

  return (
    <>
      <style>{`
        @keyframes mcBounce  { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-5px)} }
        @keyframes mcFade    { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
        @keyframes mcPop     { from{opacity:0;transform:scale(0.9) translateY(16px)} to{opacity:1;transform:scale(1) translateY(0)} }
        @keyframes mcSlideUp { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        @keyframes mcPulse   { 0%,100%{box-shadow:0 4px 20px rgba(245,130,31,0.45)} 50%{box-shadow:0 4px 30px rgba(245,130,31,0.8)} }
        .cb-input:focus  { outline:none; border-color:${C.orange} !important; }
        .cb-attach:hover { background:${C.orangeLight} !important; border-color:${C.orange} !important; }
        .cb-btn-icon:hover { opacity:0.85; }
      `}</style>

      {/* Input fichier caché */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,.png,.jpg,.jpeg,.gif,.webp,.pdf"
        multiple
        style={{ display: "none" }}
        onChange={handleFileChange}
      />

      {/* ── Bulle proactive ── */}
      {showProactive && !open && (
        <div style={{
          position: "fixed", bottom: 90, right: 24,
          zIndex: z + 1,
          animation: "mcSlideUp 0.4s cubic-bezier(0.34,1.56,0.64,1)",
          maxWidth: 300,
        }}>
          {/* Fermer bulle */}
          <button
            onClick={() => { setShowProactive(false); setProactiveDismissed(true); setUnread(0); }}
            style={{
              position: "absolute", top: -8, right: -8,
              width: 22, height: 22, borderRadius: "50%",
              background: C.dark, border: "2px solid white",
              color: "white", fontSize: 11, cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center",
              zIndex: 1,
            }}>
            <Ic d={PATH.x} size={9} color="white" sw={2.5}/>
          </button>

          {/* Corps bulle */}
          <div
            onClick={() => { setOpen(true); setShowProactive(false); }}
            style={{
              background: C.orange,
              borderRadius: "18px 18px 4px 18px",
              padding: "14px 18px",
              cursor: "pointer",
              boxShadow: "0 8px 32px rgba(245,130,31,0.35)",
              color: "white",
              fontSize: 14,
              lineHeight: 1.5,
              fontFamily: "inherit",
            }}>
            {/* Avatar + nom */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <div style={{
                width: 28, height: 28, borderRadius: "50%",
                background: "rgba(255,255,255,0.2)",
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
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
              Bonjour — je suis ClearBot, votre assistant Maroclear. Une demande, un incident ou une réclamation à préparer ?
            </p>
            <p style={{ margin: "8px 0 0", fontSize: 11, opacity: 0.8 }}>
              Cliquez pour démarrer →
            </p>
          </div>
        </div>
      )}

      {/* ── Bouton flottant ── */}
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
          onMouseOut={e  => e.currentTarget.style.transform = "scale(1)"}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z"
              stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <circle cx="8"  cy="10" r="1" fill="white"/>
            <circle cx="12" cy="10" r="1" fill="white"/>
            <circle cx="16" cy="10" r="1" fill="white"/>
          </svg>

          {/* Badge non-lus */}
          {unread > 0 && (
            <div style={{
              position: "absolute", top: -2, right: -2,
              width: 18, height: 18, borderRadius: "50%",
              background: C.red, border: "2px solid white",
              fontSize: 10, color: "white", fontWeight: 700,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>{unread}</div>
          )}
        </button>
      )}

      {/* ── Fenêtre de chat ── */}
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
            flexShrink: 0,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 38, height: 38, borderRadius: "50%",
                background: "rgba(255,255,255,0.07)",
                border: `2px solid rgba(245,130,31,0.5)`,
                display: "flex", alignItems: "center", justifyContent: "center",
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
                  <span style={{ color: "rgba(255,255,255,0.5)", fontSize: 10.5 }}>
                    Assistant Maroclear · En ligne
                  </span>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: 6 }}>
              {/* Bouton reset */}
              <button
                onClick={handleReset}
                title="Nouvelle conversation"
                className="cb-btn-icon"
                style={{
                  background: "rgba(255,255,255,0.07)", border: "none",
                  borderRadius: 6, width: 28, height: 28, cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  color: "rgba(255,255,255,0.6)",
                }}>
                <Ic d={PATH.refresh} size={13} color="rgba(255,255,255,0.7)" sw={2}/>
              </button>
              {/* Bouton agrandir/réduire */}
              <button
                onClick={() => setExpanded(e => !e)}
                title={expanded ? "Réduire" : "Agrandir"}
                className="cb-btn-icon"
                style={{
                  background: "rgba(255,255,255,0.07)", border: "none",
                  borderRadius: 6, width: 28, height: 28, cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.7)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  {expanded ? (
                    <>
                      <path d="M4 14h6v6"/><path d="M20 10h-6V4"/><path d="M14 10l7-7"/><path d="M3 21l7-7"/>
                    </>
                  ) : (
                    <>
                      <path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/>
                    </>
                  )}
                </svg>
              </button>
              {/* Bouton fermer */}
              <button
                onClick={() => setOpen(false)}
                className="cb-btn-icon"
                style={{
                  background: "rgba(255,255,255,0.07)", border: "none",
                  borderRadius: 6, width: 28, height: 28, cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                <Ic d={PATH.x} size={13} color="rgba(255,255,255,0.7)" sw={2}/>
              </button>
            </div>
          </div>

          {/* Zone des messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: "12px 12px 4px", background: C.lightGray }}>
            {messages.map(msg => <Message key={msg.id} msg={msg} />)}
            {typing && <TypingIndicator />}

            {/* SummaryCard — visible en attente de confirmation */}
            {!typing && stage === "awaiting_confirm" && pendingData && (
              <SummaryCard
                data={pendingData}
                attachments={attachments}
                onConfirm={handleConfirm}
                onCancel={handleCancel}
              />
            )}

            {stage === "done" && <SuccessBanner />}
            {stage === "done" && <FeedbackPanel onSubmit={handleFeedback} />}
            <div ref={bottomRef}/>
          </div>

          {/* Barre accent */}
          <div style={{ height: 2, background: `linear-gradient(90deg, ${C.orange}, ${C.green})`, flexShrink: 0 }}/>

          {/* Aperçu des pièces jointes */}
          {attachments.length > 0 && (
            <div style={{
              padding: "6px 12px", background: C.white,
              borderTop: `1px solid ${C.midGray}`,
              display: "flex", gap: 6, flexWrap: "wrap",
            }}>
              {attachments.map((f, i) => (
                <div key={i} style={{
                  background: C.orangeLight, borderRadius: 6,
                  padding: "3px 8px", fontSize: 11, color: C.orangeDark,
                  display: "flex", alignItems: "center", gap: 5,
                  border: `1px solid ${C.orange}30`,
                }}>
                  <Ic d={PATH.image} size={10} color={C.orangeDark} sw={2}/>
                  {f.name.length > 14 ? f.name.slice(0, 14) + "…" : f.name}
                  <span
                    onClick={() => removeAttachment(i)}
                    style={{ cursor: "pointer", fontWeight: 700, opacity: 0.7, fontSize: 10, display: "flex" }}
                    title="Retirer">
                    <Ic d={PATH.x} size={9} color={C.orangeDark} sw={2.5}/>
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Zone de saisie */}
          <div style={{
            padding: "10px 12px", background: C.white,
            display: "flex", alignItems: "flex-end", gap: 8,
            flexShrink: 0, borderTop: `1px solid ${C.midGray}`,
          }}>
            {/* Bouton pièce jointe */}
            <button
              className="cb-attach"
              onClick={() => canAttach && fileInputRef.current?.click()}
              disabled={!canAttach}
              title="Joindre une capture d'écran"
              style={{
                width: 36, height: 36, borderRadius: 9,
                border: `1.5px solid ${attachments.length > 0 ? C.orange : C.border}`,
                background: attachments.length > 0 ? C.orangeLight : C.white,
                cursor: canAttach ? "pointer" : "default",
                display: "flex", alignItems: "center", justifyContent: "center",
                flexShrink: 0, transition: "all 0.2s",
                position: "relative",
                opacity: canAttach ? 1 : 0.35,
              }}>
              <Ic d={PATH.clip} size={16} color={attachments.length > 0 ? C.orange : C.textGray} sw={2}/>
              {attachments.length > 0 && (
                <div style={{
                  position: "absolute", top: -5, right: -5,
                  width: 15, height: 15, borderRadius: "50%",
                  background: C.orange, fontSize: 9, color: "white",
                  fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center",
                  border: "1.5px solid white",
                }}>{attachments.length}</div>
              )}
            </button>

            {/* Champ texte */}
            <textarea
              ref={inputRef}
              className="cb-input"
              value={inputValue}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder={
                stage === "done"            ? "Dossier transmis au formulaire" :
                stage === "awaiting_confirm"? "Confirmez ou corrigez via la fiche ci-dessus..." :
                stage === "correcting"      ? "Ex: service : Reporting" :
                "Décrivez votre demande, incident ou réclamation..."
              }
              rows={1}
              disabled={stage === "done" || stage === "awaiting_confirm"}
              style={{
                flex: 1, border: `1.5px solid ${C.border}`,
                borderRadius: 10, padding: "9px 12px",
                fontSize: 13, lineHeight: 1.5,
                background: (stage === "done" || stage === "awaiting_confirm") ? C.midGray : C.lightGray,
                color: C.textDark, fontFamily: "inherit",
                resize: "none", maxHeight: 90, overflowY: "auto",
                opacity: (stage === "done" || stage === "awaiting_confirm") ? 0.5 : 1,
                transition: "border-color 0.2s",
              }}
              onInput={e => {
                e.target.style.height = "auto";
                e.target.style.height = Math.min(e.target.scrollHeight, 90) + "px";
              }}
            />

            {/* Bouton envoyer */}
            <button
              onClick={handleSend}
              disabled={!canSend}
              style={{
                width: 36, height: 36, borderRadius: 9, border: "none",
                background: canSend
                  ? `linear-gradient(135deg, ${C.orange}, ${C.orangeDark})`
                  : C.midGray,
                cursor: canSend ? "pointer" : "default",
                display: "flex", alignItems: "center", justifyContent: "center",
                flexShrink: 0, transition: "background 0.2s",
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
