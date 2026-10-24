# Documentation Technique — ClearBot
## Systeme Multi-Agents Conversationnel Maroclear

**Version** : 1.0
**Date** : Mai 2026

---

## Table des matieres

1. [Presentation du projet](#1-presentation-du-projet)
2. [Architecture technique](#2-architecture-technique)
3. [Les agents](#3-les-agents)
4. [API Backend](#4-api-backend)
5. [Frontend](#5-frontend)
6. [Regles metier de classification](#6-regles-metier-de-classification)
7. [Matrice de priorite GLPI](#7-matrice-de-priorite-glpi)
8. [Configuration et deploiement](#8-configuration-et-deploiement)
9. [Guide de maintenance](#9-guide-de-maintenance)

---

## 1. Presentation du projet

### 1.1 Contexte

MyClear est un assistant conversationnel intelligent integre au portail MyMaroclear.
Il permet aux affilies (banques depositaires, societes de bourse, etablissements financiers)
de declarer des incidents, soumettre des demandes ou formuler des reclamations
via un widget de chat, sans avoir a remplir manuellement les formulaires.

### 1.2 Objectifs fonctionnels

- **Classifier automatiquement** les sollicitations (Incident / Demande / Reclamation)
- **Collecter les informations** necessaires via un dialogue guide
- **Pre-remplir les formulaires** MyMaroclear automatiquement
- **Calculer la priorite OLA** pour les incidents (P1 a P4)
- **Notifier le dispatcher** par email avec toutes les informations structurees
- **Repondre aux questions** institutionnelles et reglementaires via RAG

### 1.3 Stack technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.11, FastAPI |
| LLM | OpenRouter API (openai/gpt-oss-120b:free) |
| Embeddings | Ollama local (bge-m3) + FlagEmbedding (BGE-M3) |
| Vector Store | ChromaDB (persistant, local) |
| Frontend | React 18 (CRA), Docker |
| Email | Brevo (ex-SendinBlue) |
| Authentification | Session cookie (PBKDF2-SHA256) |

---

## 2. Architecture technique

### 2.1 Structure du projet

```
ClearBot/
  backend/
    agents/
      orchestrateur/              <- Route les requetes
      support_classification/     <- Classifie + collecte (machine a etats)
      informationnel_procedural/  <- RAG documentaire general
      conseiller_reglementaire/   <- RAG juridique (Loi 35-96, RG)
      auto_dispatcher/            <- Envoi email dispatcher
    shared/
      core/                       <- AgentMessage, AgentContext
      base/                       <- BaseAgent (classe abstraite)
      llm/                        <- Client OpenRouter
      rag/                        <- Pipeline RAG partage
      security/                   <- Filtre de confidentialite
    api/
      api.py                      <- Routes FastAPI
      builder.py                  <- Assemblage des composants
    config/
      config.yaml                 <- Configuration globale
      requirements.txt            <- Dependances Python
    .env                          <- Cles API (non versionne)
  frontend/
    mymaroclear/                  <- Application principale (port 3000)
    portail-public/               <- Portail public (port 5173)
  docker-compose.yml              <- Orchestration complete
```

### 2.2 Flux de donnees

```
Affilie (navigateur)
    |
    | HTTP (port 3000)
    v
Frontend React (mymaroclear)
    |
    | POST /chat, POST /dispatch
    | (port 8000)
    v
FastAPI (api.py)
    |
    v
Orchestrateur
    |--- Classification --> SupportClassificationAgent --> OpenRouter LLM
    |--- RAG general ----> RAGAgent --> Ollama + ChromaDB
    |--- Reglementaire --> ReglementaireAgent --> BGE-M3 + ChromaDB + BM25
    |--- Dispatch -------> AutoDispatcherAgent --> Brevo (email)
```

---

## 3. Les agents

### 3.1 Agent Orchestrateur

**Fichier** : `backend/agents/orchestrateur/agent.py`
**Classe** : `OrchestratorAgent`

**Responsabilite** : Recevoir chaque message de l'affilie et decider quel agent appeler.

**Logique de routage (par priorite)** :

| Priorite | Condition | Agent cible |
|----------|-----------|-------------|
| 1 | Mots-cles juridiques (loi, article, dahir, reglement) | Conseiller Reglementaire |
| 2 | Mots-cles support (probleme, erreur, demande, reclamation, pas recu...) | Support & Classification |
| 3 | Question documentaire generale (c'est quoi, comment, quel est le role) | Informationnel & Procedural |
| 4 | Aucun match | Reponse par defaut |

**Particularite** : Si une conversation de classification est en cours (etat != CLASSIFYING),
l'orchestrateur route automatiquement vers le ClassificationAgent meme sans mots-cles.

---

### 3.2 Agent Support & Classification

**Fichier** : `backend/agents/support_classification/agent.py`
**Classe** : `SupportClassificationAgent`

C'est l'agent principal du systeme. Il fonctionne comme une **machine a etats conversationnelle**
qui guide l'affilie etape par etape.

#### 3.2.1 Machine a etats

```
STATE_CLASSIFYING       Phase 1 : le LLM classifie le message
    |
    |-- Si confiance >= 0.88 et classe != AMBIGU --> Phase 2
    |-- Si confiance < 0.88 ou AMBIGU --> pose question de clarification
    |
STATE_COLLECT_SERVICE   Phase 2 : choix du service (boutons ou auto-detection)
    |
    |-- Si INCIDENT --> STATE_COLLECT_DESC (pas de date/frequence/solution)
    |-- Si DEMANDE/RECLAMATION --> STATE_COLLECT_DATE
    |
STATE_COLLECT_DATE      (DEMANDE/RECLAMATION uniquement)
STATE_COLLECT_FREQ      (DEMANDE/RECLAMATION uniquement)
STATE_COLLECT_DESC      Description du probleme
STATE_COLLECT_SOLUTION  (DEMANDE/RECLAMATION uniquement) Solution attendue
    |
STATE_SUMMARY           Phase 3 : form_data complet retourne au frontend
```

#### 3.2.2 Champs collectes par type

| Champ | INCIDENT | DEMANDE | RECLAMATION |
|-------|----------|---------|-------------|
| Service concerne | Oui (avec systeme) | Oui | Oui |
| Systeme impacte | Oui | Non | Non |
| Date d'occurrence | Non | Oui | Oui |
| Frequence | Non | Oui | Oui |
| Description | Oui (synthetisee par LLM) | Oui | Oui |
| Objet | Oui (titre court) | Non | Non |
| Solution attendue | Non | Oui | Oui |
| Documents joints | Oui (captures d'ecran) | Oui | Oui |
| Priorite GLPI | Oui (calculee, non affichee) | Non | Non |

#### 3.2.3 Questions de clarification

Definies dans `config/rules.yaml`. Chaque question a des **triggers** (mots-cles declencheurs)
et des **quick_replies** (boutons cliquables affiches dans le widget).

| Cle | Question | Declencheur |
|-----|----------|-------------|
| Q1_collectif | Nature du probleme ? | Message initial vague |
| Q2_contenu_type | Flux metier ou facture ? | "non recu", "errone", "manquant" |
| Q3_token_cause | Panne poste ou nouveau materiel ? | "token", "certificat" |
| Q4_action_ou_constat | Retransmission ou constat de manque ? | "transmettre", "retransmettre" |
| Q5_retransmission | Suite a non-reception ou demande generique ? | "retransmission" |
| Q6_suspens_actif | En cours ou prejudice subi ? | "suspens", "denouement" |
| Q7_screenshot | Message d'erreur visible ? Capture d'ecran ? | "erreur", "bug", "page blanche" |

#### 3.2.4 Cas AMBIGU

Quand le LLM retourne AMBIGU (ex: "on a pas recu les AOE"), l'agent force une question
de clarification au lieu de passer a la collecte :

- Si mots-cles facture → pose Q2_contenu_type (flux metier vs facture)
- Sinon → pose Q4_action_ou_constat (retransmission vs constat)

Apres la reponse de l'affilie, le LLM reclassifie avec le contexte enrichi.

#### 3.2.5 Detection automatique du service

Le service est detecte automatiquement par mots-cles dans le texte de l'affilie :
- "TCS BaNCS", "bourse", "AOE" → Post-marche-Bourse
- "OTC", "gre a gre" → Post-marche-OTC
- "token", "mot de passe" → Reinitialisation MDP TCS
- "facture", "montant", "TVA" → Facturation

Si non detecte → boutons affiches avec la liste des services du type concerne.

---

### 3.3 Agent Informationnel & Procedural

**Fichier** : `backend/agents/informationnel_procedural/agent.py`
**Classe** : `RAGAgent`

**Pipeline RAG** :
1. L'affilie pose une question ("C'est quoi Maroclear ?")
2. Embedding via Ollama local (modele bge-m3)
3. Recherche semantique dans ChromaDB (678 chunks, cosine, top_k=8)
4. Construction du contexte (glossaire en tete, puis extraits PDF)
5. Generation de reponse via OpenRouter avec prompt systeme strict

**Donnees indexees** :
- Regles de fonctionnement de Maroclear (PDF)
- Glossaire Maroclear (Excel → 1 terme = 1 chunk)

**Regle stricte** : L'agent repond UNIQUEMENT a partir du contexte fourni.
Si l'information n'est pas dans les documents, il dit "Je n'ai pas cette information".

---

### 3.4 Agent Conseiller Reglementaire

**Fichier** : `backend/agents/conseiller_reglementaire/agent.py`
**Classe** : `ReglementaireAgent`

**Specificites** :
- Retrieval **hybride** : vectoriel (BGE-M3) + BM25 (termes exacts juridiques)
- **Enrichissement par liens** : si un article reference un autre (links_to), le chunk lie est ajoute
- **Historique multi-tours** : memorise les 10 derniers echanges
- **Prompt juridique strict** : distinction Loi 35-96 vs Reglement General, citations canoniques

**Sources indexees** :
- Loi 35-96 (Dahir n 1-96-246) relative au depositaire central
- Reglement General du Depositaire Central Maroclear
- Recueil AMMC (en cours d'integration)

**Pipeline de chunking** : decoupe article par article avec metadonnees hierarchiques
(Titre > Chapitre > Section > Article) et detection des references croisees.

---

### 3.5 Agent Auto-Dispatcher

**Fichier** : `backend/agents/auto_dispatcher/agent.py`
**Classe** : `AutoDispatcherAgent`

**Declenchement** : route `POST /dispatch` appelee quand l'affilie confirme la SummaryCard.

**Actions** :
1. Recoit le ticket_data complet (form_data + profil utilisateur)
2. Genere un email HTML structure (template officiel Maroclear)
3. Inclut la priorite GLPI + justification argumentee (pour INCIDENT)
4. Envoie via Brevo au dispatcher
5. Retourne confirmation avec reference du ticket

**Le dispatcher recoit** :
- Informations de la demande (reference, type, objet, systeme, service, description)
- Priorite calculee avec justification (INCIDENT uniquement)
- Instruction de valider et creer le ticket GLPI

**Important** : L'agent n'a pas acces direct a GLPI. Le dispatcher est responsable
du transfert et du remplissage dans GLPI.

---

## 4. API Backend

### 4.1 Routes

| Methode | Route | Auth | Description |
|---------|-------|------|-------------|
| POST | `/auth/login` | Non | Authentification (username + password) |
| GET | `/auth/me` | Oui | Retourne le profil de l'utilisateur connecte |
| POST | `/auth/logout` | Oui | Deconnexion (supprime la session) |
| POST | `/chat` | Non* | Point d'entree principal — orchestre les agents |
| POST | `/chat-reglementaire` | Non | Acces direct a l'agent reglementaire |
| POST | `/dispatch` | Oui | Envoi email au dispatcher (apres confirmation) |
| GET | `/chat-session` | Non | Recupere la session de chat sauvegardee |
| POST | `/chat-session` | Non | Sauvegarde la session de chat |
| DELETE | `/chat-session` | Non | Reset la session de chat |

*La route `/chat` injecte le profil utilisateur si une session est active.

### 4.2 Format de requete `/chat`

```json
POST /chat
Content-Type: application/json

{"message": "j'ai un probleme sur TCS BaNCS"}
```

### 4.3 Format de reponse `/chat`

```json
{
  "response": "Texte affiche a l'affilie",
  "agent_used": "SupportClassificationAgent",
  "route": "classification",
  "classification": "INCIDENT",
  "priorite": "P2 Tres haute",
  "service": "Technique",
  "systeme": "TCS BaNCS",
  "needs_glpi": true,
  "quick_replies": ["Aujourd'hui", "Hier", "Avant-hier"],
  "form_data": {
    "type": "INCIDENT",
    "target_path": "/incidents",
    "serviceConcerne": "Technique",
    "systemeImpacte": "TCS BaNCS",
    "objet": "Plateforme TCS BaNCS inaccessible",
    "description": "L'affilie signale une impossibilite d'acceder...",
    "reporterName": "HIDRA Asmae",
    "reporterActivity": "Banque Depositaire",
    "institution": "ATTIJARIWAFA BANK",
    "priorite": "P2 Tres haute",
    "urgence": "Tres haute",
    "impact": "Moyen",
    "gravite": "indisponible"
  },
  "rag_sources": [],
  "regl_sources": []
}
```

### 4.4 Format de requete `/dispatch`

```json
POST /dispatch
Content-Type: application/json
Cookie: maroclear_session=...

{
  "ticket_data": {
    "ticket_id": "abc123",
    "type": "INCIDENT",
    "serviceConcerne": "Technique",
    "systemeImpacte": "TCS BaNCS",
    "description": "...",
    "priorite": "P2 Tres haute",
    "urgence": "Tres haute",
    "impact": "Moyen"
  }
}
```

### 4.5 Authentification

- Mecanisme : session cookie (`maroclear_session`) via Starlette SessionMiddleware
- Hashage : PBKDF2-SHA256, 120 000 iterations, sel aleatoire 16 octets
- Duree de session : 8 heures
- CORS : localhost:3000 et localhost:5173 autorises

---

## 5. Frontend

### 5.1 Application principale — mymaroclear (port 3000)

**Stack** : React 18, Create React App, Tailwind CSS, react-router-dom v6

**Pages** :
- `/` : Page de login (authentification via POST /auth/login)
- `/incidents` : Formulaire de declaration d'incident
- `/demandes/nouvelle` : Formulaire de demande
- `/reclamations/nouvelle` : Formulaire de reclamation

**Widget ClearBot** (`MaroclearWidget.jsx`) :
- Flottant en bas a droite de toutes les pages
- Appelle `POST /chat` pour chaque message utilisateur
- Affiche les `quick_replies` comme boutons cliquables sous les messages du bot
- Quand `form_data` est retourne → affiche une SummaryCard de confirmation
- SummaryCard : recapitulatif SANS priorite visible, boutons [Confirmer] [Corriger]
- [Confirmer] → appelle `POST /dispatch` → email envoye au dispatcher

**Comportement des boutons (quick_replies)** :
- Affiches sous le message du bot
- Au clic, le texte du bouton est envoye comme message utilisateur
- Les boutons disparaissent apres un clic

### 5.2 Portail public — portail-public (port 5173)

**Stack** : React 19, Vite, multi-page

- Simule le site public maroclear.com
- Widget ClearBot integre dans la page
- Page de login MyMaroclear separee (`/my-maroclear.html`)

---

## 6. Regles metier de classification

### 6.1 Arbre de decision

```
Message de l'affilie
    |
    |-- Dysfonctionnement technique / blocage / erreur systeme
    |   → INCIDENT
    |
    |-- Fichier metier (AOE, RSM, RCQ, REQ, CFT) vide / corrompu / errone
    |   → INCIDENT
    |
    |-- Facture incorrecte (montant, TVA, ICE, droit d'admission)
    |   → RECLAMATION
    |
    |-- Ecart de donnees (position != reel, solde incorrect)
    |   → RECLAMATION
    |
    |-- "Merci de...", "Veuillez...", "Priere de..." (demande active)
    |   → DEMANDE
    |
    |-- Token perdu (probleme cote affilie, pas cote depositaire)
    |   → DEMANDE
    |
    |-- "Nous n'avons pas recu..." (constat passif, cause inconnue)
    |   → AMBIGU → poser question Q4 ou Q2
    |       |-- "Je veux une retransmission" → DEMANDE
    |       |-- "C'est manquant/errone" + flux metier → INCIDENT
    |       |-- "C'est manquant/errone" + facture → RECLAMATION
```

### 6.2 Regles validees par le dispatcher

| Message | Classification | Justification |
|---------|---------------|---------------|
| "Merci de nous communiquer le solde au 31/12/2025" | DEMANDE | Demande d'information comptable |
| "Suite au changement de poste, nouveau Token" | DEMANDE | Nouveau materiel = premiere demande |
| "Merci de valider les AOE tardifs" | DEMANDE | Traitement exceptionnel |
| "Mon poste a subi une deterioration, token perdu" | DEMANDE | Probleme cote affilie |
| "Merci de mettre a disposition l'avis d'opere ref X" | DEMANDE | Sollicitation active |
| "La facture comporte une erreur sur la quantite" | RECLAMATION | Facture erronee |
| "Ecart : position devrait etre X mais MCL affiche Y" | RECLAMATION | Ecart de donnees |
| "Nous n'avons pas recu le fichier RSM (118)" | AMBIGU | Cause inconnue → diagnostic |
| "Nous n'arrivons pas a acceder a TCS BANKS" | INCIDENT | Plateforme inaccessible |
| "Les fichiers CFT sont vides" | INCIDENT | Fichiers metier corrompus |
| "Impossible de saisir les operations OTC. Batch en cours" | INCIDENT | Blocage systeme |
| "Pending for Fund Transfer alors que cash disponible" | INCIDENT | Statut errone systeme |

### 6.3 Regles imperatives

- Ne JAMAIS demander a l'affilie si le probleme impacte d'autres affilies (il ne sait pas)
- Si bug/erreur visuelle → demander une capture d'ecran
- Ignorer les mots forts ("urgent", "panne") → analyser ce qui est reellement decrit
- Token perdu apres panne materielle cote affilie → DEMANDE (pas incident cote depositaire)
- "Veuillez transmettre/retransmettre" → DEMANDE (demande active)
- Fichier metier non recu/errone → INCIDENT (probleme systeme)
- Facture non recue/erronee → RECLAMATION (probleme donnees)

---

## 7. Matrice de priorite GLPI

### 7.1 Principes

La priorite est calculee **uniquement pour les INCIDENTS** par la fonction `compute_glpi()`.
Elle n'est **jamais affichee a l'affilie** — elle est transmise dans le mail au dispatcher.

**Algorithme** :
1. Detecter la **gravite** par mots-cles dans la description
2. Croiser **(service x gravite)** dans la matrice
3. Obtenir **(urgence, impact, priorite)**

### 7.2 Services et systemes (INCIDENT)

| Service | Systeme | Description |
|---------|---------|-------------|
| Post-marche-Bourse | TCS BaNCS | Contrats bourse, AOE, denouement |
| Post-marche-OTC | TCS BaNCS | Operations gre a gre |
| Post-marche-Repo's | TCS BaNCS | Pensions livrees |
| Post-marche-Transfert | TCS BaNCS | Transferts Franco |
| Referentiel-Titres | MyMaroclear | Codification, admission |
| Referentiel-Affilies | MyMaroclear | Affiliation, mandats |
| OST | MyMaroclear | Operations sur titres |
| Reporting | TCS BaNCS | Documents comptables (RCQ, REQ, RMQ, RSM) |
| Technique | MyMaroclear / TCS | Incidents techniques interfaces/fichiers |

### 7.3 Matrice de priorite

**Post-marche (Bourse, OTC, Repo's)** :

| Gravite | Urgence | Impact | Priorite |
|---------|---------|--------|----------|
| Blocage general du marche / denouement bloque | Tres haute | Tres haut | **P1 Majeur** |
| Blocage d'un affilie (operations impossibles) | Tres haute | Moyen | **P2 Tres haute** |
| Dysfonctionnement partiel contournable | Moyenne | Moyen | **P3 Moyenne** |
| Bug affichage | Basse | Bas | **P4 Basse** |

**OST / Referentiel** :

| Gravite | Urgence | Impact | Priorite |
|---------|---------|--------|----------|
| Impossibilite de prise en charge | Tres haute | Moyen | **P2 Tres haute** |
| Dysfonctionnement partiel | Moyenne | Moyen | **P3 Moyenne** |

**Reporting** :

| Gravite | Urgence | Impact | Priorite |
|---------|---------|--------|----------|
| Erreur ou non-generation des documents comptables | Tres haute | Tres haut | **P1 Majeur** |
| Erreur sur un document comptable | Tres haute | Moyen | **P2 Tres haute** |

**Technique** :

| Gravite | Urgence | Impact | Priorite |
|---------|---------|--------|----------|
| Plateforme indisponible / lenteurs extremes / arret complet | Tres haute | Tres haut | **P1 Majeur** |
| Arret des echanges avec un affilie | Tres haute | Moyen | **P2 Tres haute** |
| Non transmission des documents a temps | Moyenne | Moyen | **P3 Moyenne** |
| Message d'erreur impertinent | Basse | Bas | **P4 Basse** |
| Fichiers recus vides / corrompus | Tres haute | Tres haut | **P1 Majeur** |
| Statut errone (Pending for Fund Transfer) | Tres haute | Moyen | **P2 Tres haute** |
| Batch en cours bloquant la saisie | Tres haute | Moyen | **P2 Tres haute** |

### 7.4 Delais OLA

| Priorite | Prise en charge | Resolution |
|----------|-----------------|------------|
| P1 Majeur | 15 minutes | 2 heures |
| P2 Tres haute | 30 minutes | 4 heures |
| P3 Moyenne | 4 heures | J+1 |
| P4 Basse | 8 heures | J+2 |

---

## 8. Configuration et deploiement

### 8.1 Prerequis

- Python 3.11+
- Docker Desktop (pour le frontend)
- Ollama (pour les embeddings locaux) avec modele `bge-m3`
- Cle API OpenRouter (gratuite : https://openrouter.ai/keys)
- Cle API Brevo (pour l'envoi d'emails)

### 8.2 Variables d'environnement

**`backend/.env`** (non versionne, copier depuis `.env.example`) :
```
OPENROUTER_API_KEY=sk-or-v1-...
BREVO_API_KEY=...
SESSION_SECRET_KEY=changez-moi-en-production
```

### 8.3 Lancement

**Mode Docker (recommande)** :

```bash
# Depuis la racine du projet
cp backend/.env.example backend/.env
# Editer backend/.env et renseigner les cles
docker-compose up --build
```

**Mode local** :

```bash
# Terminal 1 — Backend
cd backend
pip install -r config/requirements.txt
uvicorn api.api:app --reload --port 8000

# Terminal 2 — Frontend prive (port 3000)
cd frontend/mymaroclear
npm install
npm start

# Terminal 3 — Portail public (port 5173)
cd frontend/portail-public
npm install
npm run dev
```

### 8.4 Comptes de test

| Utilisateur | Mot de passe | Role |
|-------------|-------------|------|
| asmae.hidra | maroclear123 | Responsable support affilie |
| adil.elbouzgui | maroclear123 | Responsable |

---

## 9. Guide de maintenance

### 9.1 Modifier les regles de classification

Editer `backend/agents/support_classification/config/rules.yaml` :
- Section `services` : ajouter/modifier les services par type
- Section `glpi.matrix` : modifier la matrice de priorite
- Section `glpi.gravite_keywords` : ajouter des mots-cles de detection
- Section `questions` : modifier les questions de clarification

**Aucune modification de code necessaire** — tout est dans le YAML.

### 9.2 Ajouter un document au RAG general

```bash
# Copier le PDF dans le dossier documents
cp nouveau_doc.pdf backend/agents/informationnel_procedural/data/documents/

# Relancer l'indexation
cd backend/api
python -c "from builder import load_config, index_documents; index_documents(load_config())"
```

### 9.3 Ajouter un document au RAG reglementaire

```bash
cd backend/agents/conseiller_reglementaire/rag
python ingest_new_doc.py chemin/vers/document.pdf
```

### 9.4 Modifier le template email dispatcher

Editer `backend/agents/auto_dispatcher/agent.py` :
- Methode `_build_body_html()` : template HTML
- Methode `_build_body_text()` : version texte brut
- Methode `_build_justification()` : logique de justification de la priorite

### 9.5 Ajouter un nouvel agent

1. Creer un dossier dans `backend/agents/nouveau_agent/`
2. Creer `agent.py` heritant de `BaseAgent` (implementer `can_handle`, `process`, `get_capabilities`)
3. Ajouter l'agent dans `builder.py` (instanciation)
4. Ajouter l'agent dans `OrchestratorAgent.__init__()` et `_decide_route()`
5. Ajouter les mots-cles de routage

### 9.6 Problemes connus

| Probleme | Cause | Solution |
|----------|-------|----------|
| "OPENROUTER_API_KEY non definie" | .env manquant ou mal place | Verifier backend/.env et support_classification/.env |
| "Modele bge-m3 introuvable" | Ollama non demarre ou modele non telecharge | `ollama pull bge-m3` |
| "ChromaDB : 0 documents" | Base vectorielle vide | Relancer l'indexation (voir 9.2) |
| Cookie session trop gros | Conversation trop longue | Reset la session (DELETE /chat-session) |
| Frontend ne se connecte pas | Backend non demarre ou CORS | Verifier port 8000 et config CORS dans api.py |

---
