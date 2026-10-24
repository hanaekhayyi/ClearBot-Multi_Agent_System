# Frontend — ClearBot Maroclear

## Structure

```
frontend/
├── mymaroclear/      ← React 18 — Espace privé affilié MyMaroclear (port 3000)
└── portail-public/   ← Vite + React 19 — Portail public (port 5173)
```

## mymaroclear/ — Espace privé affilié

Application React 18 avec :
- Authentification (login / logout)
- Simulateur interface MyMaroclear
- Widget ClearBot intégré
- Formulaires Incident / Demande / Réclamation avec pré-remplissage automatique

**Via Docker (recommandé) :**
```bash
# Depuis la racine du projet
docker-compose up --build
```

**En local :**
```bash
cd frontend/mymaroclear
npm install
npm start
# → http://localhost:3000
```

## portail-public/ — Portail public

Application Vite + React 19 avec :
- Simulation du site public Maroclear
- Widget ClearBot pour visiteurs non authentifiés
- Redirection vers MyMaroclear pour les affiliés

**Via Docker (recommandé) :**
```bash
# Depuis la racine du projet
docker-compose up --build
```

**En local :**
```bash
cd frontend/portail-public
npm install
npm run dev
# → http://localhost:5173
```

## Comptes de test (MyMaroclear)

| Username | Password | Rôle |
|---|---|---|
| `asmae.hidra` | `maroclear123` | Responsable support affilié |
| `adil.elbouzgui` | `maroclear123` | Responsable |
