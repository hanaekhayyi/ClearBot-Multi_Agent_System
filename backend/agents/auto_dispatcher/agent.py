"""
auto_dispatcher/agent.py
=========================
AutoDispatcherAgent — Envoi email de notification au dispatcher Maroclear.

Rôle :
  - Reçoit un ticket déjà classifié et qualifié (form_data depuis ClassificationAgent)
  - Formate l'email de notification selon le template officiel
  - Envoie via Brevo (sib-api-v3-sdk)
  - Retourne confirmation avec ticket_id

Ce que cet agent NE fait PAS :
  - Pas de classification
  - Pas de calcul de priorité (déjà fait par ClassificationAgent)
  - Pas d'accès direct à GLPI (le dispatcher s'en charge)

Déclenchement : après confirmation de l'utilisateur ("Soumettre")
via la route POST /dispatch de api.py
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Charger le .env local
load_dotenv(Path(__file__).parent / ".env")

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.base.base_agent import BaseAgent
from shared.core.message import AgentMessage
from shared.core.agent_context import AgentContext

logger = logging.getLogger(__name__)


# ── Priorité → libellés lisibles ─────────────────────────────────────────────

_PRIORITY_LABELS = {
    "P1 Majeur":      ("Critique",  "Immédiate"),
    "P2 Très haute":  ("Élevé",     "Haute"),
    "P3 Moyenne":     ("Moyen",     "Normale"),
    "P4 Basse":       ("Faible",    "Basse"),
    "Qualifiée par dispatcher": ("À qualifier", "À qualifier"),
}

_TYPE_LABELS = {
    "INCIDENT":    "déclaration d'incident",
    "DEMANDE":     "demande",
    "RÉCLAMATION": "réclamation",
    "RECLAMATION": "réclamation",
    "AMBIGU":      "déclaration",
}


class AutoDispatcherAgent(BaseAgent):
    """
    Agent de dispatch — notifie le dispatcher Maroclear par email.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(agent_name="AutoDispatcherAgent", config=config)

        dispatch_cfg = config.get("auto_dispatcher", {})
        self._dispatcher_email = dispatch_cfg.get(
            "dispatcher_email",
            os.getenv("DISPATCHER_EMAIL", "dispatcher@maroclear.com"),
        )
        self._sender_email = dispatch_cfg.get(
            "sender_email",
            os.getenv("SENDER_EMAIL", "myclear@maroclear.com"),
        )
        self._sender_name = dispatch_cfg.get("sender_name", "MyClear — Agent IA Maroclear")
        self._api_key     = os.getenv("BREVO_API_KEY", "")

        if not self._api_key:
            self.log("BREVO_API_KEY non définie — emails désactivés", level="WARNING")

        self.log(f"AutoDispatcherAgent prêt — dispatcher: {self._dispatcher_email}")

    # ── Interface BaseAgent ───────────────────────────────────────────────────

    def can_handle(self, message: AgentMessage, context: AgentContext) -> bool:
        """
        L'AutoDispatcher ne se déclenche pas sur des messages texte.
        Il est appelé directement via process() depuis la route /dispatch.
        """
        return False

    def process(self, message: AgentMessage, context: AgentContext) -> AgentMessage:
        """
        Traite une demande de dispatch.
        message.metadata doit contenir le form_data complet.
        """
        ticket_data = message.metadata.get("ticket_data", {})
        return self.dispatch(ticket_data)

    # ── Méthode principale ────────────────────────────────────────────────────

    def dispatch(self, ticket_data: dict) -> AgentMessage:
        """
        Point d'entrée principal depuis la route /dispatch.

        Args:
            ticket_data: dict contenant tous les champs du ticket
                         (issu de ClassificationAgent.form_data + profil utilisateur)
        """
        ticket_id = ticket_data.get("ticket_id", "N/A")
        classe    = ticket_data.get("type", "INCIDENT").upper()

        self.log(f"Dispatch ticket [{ticket_id}] — {classe}")

        # Construire et envoyer l'email
        subject  = self._build_subject(ticket_data)
        body_txt = self._build_body_text(ticket_data)
        body_html = self._build_body_html(ticket_data)

        email_sent = False
        error_msg  = ""

        if self._api_key:
            email_sent, error_msg = self._send_brevo(subject, body_txt, body_html)
        else:
            error_msg = "BREVO_API_KEY non configurée"
            self.log(error_msg, level="WARNING")

        # Réponse
        if email_sent:
            content = (
                f"✅ Votre {_TYPE_LABELS.get(classe, 'demande')} a été transmise au dispatcher.\n\n"
                f"**Référence :** {ticket_id}\n"
                f"**Email envoyé à :** {self._dispatcher_email}\n\n"
                "Le dispatcher va valider la priorité et créer le ticket GLPI."
            )
        else:
            content = (
                f"⚠️ La notification email n'a pas pu être envoyée ({error_msg}).\n\n"
                f"**Référence :** {ticket_id}\n"
                "Veuillez contacter le dispatcher directement."
            )

        return AgentMessage.create_response(
            sender=self.agent_name,
            content=content,
            metadata={
                "ticket_id":        ticket_id,
                "email_sent":       email_sent,
                "dispatcher_email": self._dispatcher_email,
                "error":            error_msg,
            },
        )

    # ── Construction email ────────────────────────────────────────────────────

    def _build_subject(self, data: dict) -> str:
        classe   = data.get("type", "INCIDENT")
        if classe == "INCIDENT":
            priorite = data.get("priorite", "")
            px = priorite.split()[0] if priorite else "Px"
            return f"[ClearBot] Nouvelle {_TYPE_LABELS.get(classe, 'demande')} — {px}"
        else:
            return f"[ClearBot] Nouvelle {_TYPE_LABELS.get(classe, 'demande')}"

    def _build_body_text(self, data: dict) -> str:
        """Corps email en texte brut (fallback)."""
        classe    = data.get("type", "INCIDENT")
        type_label = _TYPE_LABELS.get(classe, "demande")
        priorite  = data.get("priorite", "N/A")
        impact_lbl, urgence_lbl = _PRIORITY_LABELS.get(priorite, ("N/A", "N/A"))

        reporter   = data.get("reporterName", "N/A")
        institution = data.get("institution", "N/A")
        ticket_id  = data.get("ticket_id", "N/A")
        objet      = data.get("objet", data.get("description", "N/A"))
        systeme    = data.get("systemeImpacte", data.get("systeme", "N/A"))
        service    = data.get("serviceConcerne", data.get("service", "N/A"))
        description = data.get("description", "N/A")
        justification = self._build_justification(data)

        body = f"""Bonjour,

Une nouvelle {type_label} a été créée via MyMaroclear par l'affilié {reporter} / {institution}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFORMATIONS DE LA DEMANDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Référence   : {ticket_id}
Type        : {classe}
Objet       : {objet}
Service     : {service}
Description : {description}
"""
        # Système uniquement pour INCIDENT
        if classe == "INCIDENT":
            body += f"Système     : {systeme}\n"

        # Priorité uniquement pour INCIDENT
        if classe == "INCIDENT":
            body += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRIORITÉ CALCULÉE : {priorite}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Impact  : {impact_lbl}
Urgence : {urgence_lbl}

Justification de la priorité :
{justification}
"""

        body += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Veuillez consulter la demande dans MyMaroclear, valider
puis procéder au remplissage de GLPI.

Cordialement,
ClearBot — Agent IA Maroclear"""

        return body

    def _build_body_html(self, data: dict) -> str:
        """Corps email en HTML."""
        classe     = data.get("type", "INCIDENT")
        type_label = _TYPE_LABELS.get(classe, "demande")
        priorite   = data.get("priorite", "N/A")
        impact_lbl, urgence_lbl = _PRIORITY_LABELS.get(priorite, ("N/A", "N/A"))
        px         = priorite.split()[0] if priorite else "Px"

        reporter    = data.get("reporterName", "N/A")
        institution = data.get("institution", "N/A")
        ticket_id   = data.get("ticket_id", "N/A")
        objet       = data.get("objet", data.get("description", "N/A"))
        systeme     = data.get("systemeImpacte", data.get("systeme", "N/A"))
        service     = data.get("serviceConcerne", data.get("service", "N/A"))
        description = data.get("description", "N/A")
        justification = self._build_justification(data)

        # Couleur selon priorité
        priority_colors = {
            "P1": "#c0392b", "P2": "#e67e22",
            "P3": "#f39c12", "P4": "#27ae60",
        }
        color = priority_colors.get(px, "#7f8c8d")

        # Section système (uniquement pour INCIDENT)
        systeme_row = ""
        if classe == "INCIDENT":
            systeme_row = f'<div class="field"><span class="label">Système</span><span class="value">{systeme}</span></div>'

        # Section priorité (uniquement pour INCIDENT)
        priority_section = ""
        if classe == "INCIDENT":
            priority_section = f"""
    <div class="section" style="border-left-color: {color};">
      <h3>Priorité calculée</h3>
      <div class="priority-badge">{priorite}</div>
      <div class="field"><span class="label">Impact</span><span class="value">{impact_lbl}</span></div>
      <div class="field"><span class="label">Urgence</span><span class="value">{urgence_lbl}</span></div>
      <div class="justification">
        <strong>Justification :</strong><br>{justification}
      </div>
    </div>"""

        return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><style>
  body {{ font-family: Arial, sans-serif; color: #2c3e50; max-width: 700px; margin: 0 auto; }}
  .header {{ background: #0d1b2a; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
  .header h2 {{ margin: 0; font-size: 18px; }}
  .header p {{ margin: 5px 0 0; color: #8090b0; font-size: 13px; }}
  .section {{ background: #f8f9fa; border-left: 4px solid #e8722a; padding: 15px 20px; margin: 15px 0; border-radius: 0 6px 6px 0; }}
  .section h3 {{ margin: 0 0 12px; color: #0d1b2a; font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .field {{ display: flex; margin: 6px 0; font-size: 14px; }}
  .label {{ color: #6b7a94; min-width: 120px; font-weight: bold; }}
  .value {{ color: #2c3e50; }}
  .priority-badge {{ background: {color}; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold; font-size: 16px; display: inline-block; margin: 10px 0; }}
  .justification {{ background: white; border: 1px solid #dde3ec; border-radius: 6px; padding: 12px; font-size: 13px; color: #4a5568; line-height: 1.6; margin-top: 10px; }}
  .footer {{ background: #f2f4f7; padding: 15px 20px; border-radius: 0 0 8px 8px; font-size: 12px; color: #6b7a94; border-top: 1px solid #dde3ec; }}
  .divider {{ border: none; border-top: 1px solid #dde3ec; margin: 15px 0; }}
</style></head>
<body>
  <div class="header">
    <h2>Nouvelle {type_label} — MyMaroclear</h2>
    <p>Affilié : <strong>{reporter}</strong> — {institution}</p>
  </div>

  <div style="padding: 0 5px;">
    <div class="section">
      <h3>Informations de la demande</h3>
      <div class="field"><span class="label">Référence</span><span class="value">{ticket_id}</span></div>
      <div class="field"><span class="label">Type</span><span class="value">{classe}</span></div>
      <div class="field"><span class="label">Objet</span><span class="value">{objet}</span></div>
      {systeme_row}
      <div class="field"><span class="label">Service</span><span class="value">{service}</span></div>
      <hr class="divider">
      <div class="field" style="flex-direction: column;">
        <span class="label" style="margin-bottom: 6px;">Description</span>
        <span class="value" style="line-height: 1.6;">{description}</span>
      </div>
    </div>

    {priority_section}

    <div style="background: #fff8e1; border: 1px solid #f39c12; border-radius: 6px; padding: 12px 16px; margin: 15px 0; font-size: 13px;">
      Veuillez consulter la demande dans MyMaroclear puis procéder au remplissage de GLPI.
    </div>
  </div>

  <div class="footer">
    Cordialement,<br>
    <strong>ClearBot — Agent IA Maroclear</strong><br>
    <em>Cet email a été généré automatiquement. Ne pas répondre directement.</em>
  </div>
</body>
</html>"""

    def _build_justification(self, data: dict) -> str:
        """Génère une justification argumentée de la priorité."""
        classe   = data.get("type", "INCIDENT")
        priorite = data.get("priorite", "N/A")
        service  = data.get("serviceConcerne", data.get("service", ""))
        gravite  = data.get("gravite", "")
        px       = priorite.split()[0] if priorite else "Px"

        impact_lbl, urgence_lbl = _PRIORITY_LABELS.get(priorite, ("N/A", "N/A"))

        if classe == "INCIDENT":
            gravite_desc = {
                "blocage_general":  "un blocage général affectant l'ensemble du marché",
                "blocage_affilie":  "un blocage affectant les opérations de l'affilié",
                "partiel":          "un dysfonctionnement partiel contournable",
                "bug_affichage":    "un bug d'affichage sans impact opérationnel",
                "impossible":       "une impossibilité de prise en charge",
                "indisponible":     "une indisponibilité de la plateforme",
                "lenteur":          "des lenteurs extrêmes bloquantes",
                "erreur_nongen":    "une erreur ou non-génération de documents comptables",
                "erreur_doc":       "une erreur sur un document comptable",
            }.get(gravite, "un dysfonctionnement signalé")

            return (
                f"La priorité {priorite} a été attribuée car l'affilié signale {gravite_desc} "
                f"sur le service {service}. "
                f"L'impact est {impact_lbl.lower()} et l'urgence est {urgence_lbl.lower()}. "
                f"Le dispatcher est invité à valider cette qualification avant création du ticket GLPI."
            )

        if classe in ("DEMANDE", "RÉCLAMATION", "RECLAMATION"):
            return (
                f"Il s'agit d'une {_TYPE_LABELS.get(classe, 'demande')} sur le service {service}. "
                "La priorité sera qualifiée par le dispatcher selon le contexte opérationnel."
            )

        return "Priorité à qualifier par le dispatcher."

    # ── Envoi Brevo ───────────────────────────────────────────────────────────

    def _send_brevo(self, subject: str, body_txt: str, body_html: str) -> tuple[bool, str]:
        """Envoie l'email via Brevo (sib-api-v3-sdk)."""
        try:
            import sib_api_v3_sdk
            from sib_api_v3_sdk.rest import ApiException

            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key["api-key"] = self._api_key

            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )

            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                sender={"name": self._sender_name, "email": self._sender_email},
                to=[{"email": self._dispatcher_email}],
                subject=subject,
                text_content=body_txt,
                html_content=body_html,
            )

            api_instance.send_transac_email(send_smtp_email)
            self.log(f"Email envoyé à {self._dispatcher_email}")
            return True, ""

        except ImportError:
            msg = "sib-api-v3-sdk non installé. Lancez : pip install sib-api-v3-sdk"
            self.log(msg, level="ERROR")
            return False, msg
        except Exception as exc:
            msg = str(exc)
            self.log(f"Erreur Brevo : {msg}", level="ERROR")
            return False, msg

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "agent_name":  self.agent_name,
            "description": "Envoie la notification email au dispatcher Maroclear",
            "handles": [
                "Formatage email de notification (HTML + texte)",
                "Envoi via Brevo (sib-api-v3-sdk)",
                "Justification argumentée de la priorité",
            ],
            "email_configured": bool(self._api_key),
            "dispatcher_email": self._dispatcher_email,
        }
